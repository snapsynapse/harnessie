"""Opt-in live provider scorecards.

The deterministic eval suite stays network-free. This module is the 0.4 live
layer: it discovers operator-configured provider targets, skips visibly when
the opt-in flag or credentials are absent, and runs a small comparable smoke
scorecard when the operator explicitly enables live calls.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

from .events import EventLog
from .loop import AgentLoop
from .models import build_model
from .models.base import Message, ModelSpec
from .runner import load_models_config
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import parse_verdict


LIVE_FLAG = "HARNESSIE_LIVE"


@dataclass
class LiveTarget:
    id: str
    provider: str
    spec: ModelSpec | None
    status: str
    notes: str = ""


@dataclass
class LiveCaseResult:
    id: str
    provider: str
    status: str
    passed: bool
    expected: str
    observed: str
    notes: str = ""
    tokens: int = 0
    cost_usd: float = 0.0


def discover_live_targets(
    root: Path,
    env: Mapping[str, str] | None = None,
) -> list[LiveTarget]:
    """Return live provider targets, marking unavailable ones as skipped.

    Discovery never opens the network. Local OpenAI-compatible endpoints are
    only considered configured when the operator sets a base URL override or
    explicitly opts into the checked-in local tier.
    """

    env = env or os.environ
    tiers, _, _ = load_models_config(root / "config" / "models.yaml")
    enabled = env.get(LIVE_FLAG) == "1"
    if not enabled:
        return [
            LiveTarget("anthropic", "anthropic", None, "skipped",
                       "set HARNESSIE_LIVE=1 and ANTHROPIC_API_KEY"),
            LiveTarget("openai_compat", "openai-compat", None, "skipped",
                       "set HARNESSIE_LIVE=1 and HARNESSIE_OPENAI_COMPAT_BASE_URL"),
        ]

    return [
        _anthropic_target(tiers, env),
        _openai_compat_target(tiers, env),
    ]


def run_live_scorecard(root: Path, env: Mapping[str, str] | None = None) -> dict:
    results: list[LiveTarget | LiveCaseResult] = []
    for target in discover_live_targets(root, env=env):
        if target.status == "skipped":
            results.append(target)
            continue
        assert target.spec is not None
        results.extend(_run_target_scorecard(target))
    total = sum(1 for r in results if r.status != "skipped")
    passed = sum(1 for r in results if r.status != "skipped" and getattr(r, "passed", False))
    return {"passed": passed, "total": total, "results": results}


def format_live_scorecard(scorecard: dict) -> str:
    lines = [
        f"live scorecard: {scorecard['passed']}/{scorecard['total']} passed"
    ]
    for result in scorecard["results"]:
        if result.status == "skipped":
            lines.append(f"SKIP {result.id}: {result.notes}")
            continue
        mark = "PASS" if result.passed else "FAIL"
        lines.append(
            f"{mark} {result.provider}:{result.id}: expected={result.expected} "
            f"observed={result.observed}"
        )
        if result.tokens or result.cost_usd:
            lines[-1] += f" tokens={result.tokens} cost=${result.cost_usd:.6f}"
        if result.notes and not result.passed:
            lines.append(f"  {result.notes[:500]}")
    return "\n".join(lines)


def _anthropic_target(tiers: dict[str, ModelSpec], env: Mapping[str, str]) -> LiveTarget:
    tier = env.get("HARNESSIE_LIVE_ANTHROPIC_TIER", "mid")
    spec = tiers.get(tier) or _first_provider(tiers, "anthropic")
    if spec is None:
        return LiveTarget("anthropic", "anthropic", None, "skipped",
                          "config/models.yaml has no anthropic tier")
    key_env = spec.api_key_env or "ANTHROPIC_API_KEY"
    if not env.get(key_env):
        return LiveTarget("anthropic", "anthropic", None, "skipped",
                          f"missing {key_env}")
    model_id = env.get("HARNESSIE_ANTHROPIC_MODEL")
    if model_id:
        spec = replace(spec, model_id=model_id)
    return LiveTarget("anthropic", "anthropic", spec, "ready")


def _openai_compat_target(
    tiers: dict[str, ModelSpec],
    env: Mapping[str, str],
) -> LiveTarget:
    spec = tiers.get("local") or _first_provider(tiers, "openai-compat")
    if spec is None:
        return LiveTarget("openai_compat", "openai-compat", None, "skipped",
                          "config/models.yaml has no openai-compat tier")
    base_url = env.get("HARNESSIE_OPENAI_COMPAT_BASE_URL")
    use_config_local = env.get("HARNESSIE_LIVE_OPENAI_COMPAT") == "1"
    if not base_url and not use_config_local:
        return LiveTarget(
            "openai_compat", "openai-compat", None, "skipped",
            "set HARNESSIE_OPENAI_COMPAT_BASE_URL or HARNESSIE_LIVE_OPENAI_COMPAT=1",
        )
    model_id = env.get("HARNESSIE_OPENAI_COMPAT_MODEL")
    spec = replace(
        spec,
        base_url=base_url or spec.base_url,
        model_id=model_id or spec.model_id,
    )
    if spec.api_key_env and not env.get(spec.api_key_env):
        return LiveTarget("openai_compat", "openai-compat", None, "skipped",
                          f"missing {spec.api_key_env}")
    return LiveTarget("openai_compat", "openai-compat", spec, "ready")


def _first_provider(tiers: dict[str, ModelSpec], provider: str) -> ModelSpec | None:
    for spec in tiers.values():
        if spec.provider == provider:
            return spec
    return None


def _run_target_scorecard(target: LiveTarget) -> list[LiveCaseResult]:
    assert target.spec is not None
    return [
        _direct_smoke(target),
        _verdict_smoke(target),
        _loop_smoke(target, consent=False),
        _loop_smoke(target, consent=True),
        _consent_lock_smoke(target),
    ]


def _direct_smoke(target: LiveTarget) -> LiveCaseResult:
    model = build_model(target.spec)  # type: ignore[arg-type]
    turn = model.complete([
        Message(role="user", content="Reply with a short sentence containing Harnessie live OK.")
    ], tools=None, effort="low")
    passed = turn.stop_reason not in {"error", "refusal"} and bool(turn.content.strip())
    return LiveCaseResult(
        id="direct_completion",
        provider=target.provider,
        status="passed" if passed else "failed",
        passed=passed,
        expected="non-empty completion",
        observed=f"{turn.stop_reason}: {turn.content[:120]}",
        tokens=turn.input_tokens + turn.output_tokens,
        cost_usd=_cost(target.spec, turn.input_tokens, turn.output_tokens),
    )


def _verdict_smoke(target: LiveTarget) -> LiveCaseResult:
    model = build_model(target.spec)  # type: ignore[arg-type]
    turn = model.complete([
        Message(role="user", content=(
            "Return only JSON for a verifier verdict: "
            "{\"passed\": true, \"reasons\": \"live smoke\"}"
        ))
    ], tools=None, effort="low")
    verdict = parse_verdict(turn.content)
    passed = turn.stop_reason not in {"error", "refusal"} and verdict.passed
    return LiveCaseResult(
        id="verdict_json",
        provider=target.provider,
        status="passed" if passed else "failed",
        passed=passed,
        expected='parseable {"passed": true}',
        observed=f"{turn.stop_reason}: {turn.content[:120]}",
        notes=verdict.reasons,
        tokens=turn.input_tokens + turn.output_tokens,
        cost_usd=_cost(target.spec, turn.input_tokens, turn.output_tokens),
    )


def _loop_smoke(target: LiveTarget, consent: bool) -> LiveCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-live-") as d:
        root = Path(d)
        reg = ToolRegistry()
        workspace = root / "workspace"
        workspace.mkdir()
        run_dir = root / "run"
        register_builtin(reg, workspace=workspace)
        loop = AgentLoop(
            role="worker",
            model=build_model(target.spec),  # type: ignore[arg-type]
            registry=reg,
            events=EventLog(run_dir, echo=False),
            max_steps=4,
            agent_name="implementer",
            consent_required=consent,
        )
        if consent:
            task = (
                "First call accept_task with note 'live smoke'. Then call "
                "task_complete with report 'live loop ok'. Do not write files."
            )
        else:
            task = "Call task_complete with report 'live loop ok'. Do not write files."
        result = loop.run("You are a Harnessie live-smoke worker.", task, effort="low")
        consent_event = _event_kinds(run_dir).count("consent_granted")
    passed = result.stop == "complete" and (not consent or consent_event == 1)
    case_id = "consent_loop" if consent else "tool_loop"
    return LiveCaseResult(
        id=case_id,
        provider=target.provider,
        status="passed" if passed else "failed",
        passed=passed,
        expected="complete" if not consent else "accept_task then complete",
        observed=f"{result.stop}: {result.report[:120]}",
        notes=f"steps={result.steps}",
    )


def _consent_lock_smoke(target: LiveTarget) -> LiveCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-live-") as d:
        root = Path(d)
        reg = ToolRegistry()
        workspace = root / "workspace"
        workspace.mkdir()
        run_dir = root / "run"
        register_builtin(reg, workspace=workspace)
        loop = AgentLoop(
            role="worker",
            model=build_model(target.spec),  # type: ignore[arg-type]
            registry=reg,
            events=EventLog(run_dir, echo=False),
            max_steps=4,
            agent_name="implementer",
            consent_required=True,
        )
        result = loop.run(
            "You are a Harnessie live-smoke worker.",
            "Do not call accept_task. Try to write blocked.txt with write_file, "
            "then report what happened with task_complete.",
            effort="low",
        )
        artifact_absent = not (workspace / "blocked.txt").exists()
        refusal_seen = "refusal" in _event_kinds(run_dir)
    passed = artifact_absent and result.stop not in {"model_error", "refusal"}
    return LiveCaseResult(
        id="consent_lock",
        provider=target.provider,
        status="passed" if passed else "failed",
        passed=passed,
        expected="blocked.txt absent under locked side effects",
        observed=f"stop={result.stop}; refusal_seen={refusal_seen}",
        notes=result.report[:300],
    )


def _event_kinds(run_dir: Path) -> list[str]:
    events = run_dir / "events.jsonl"
    if not events.exists():
        return []
    kinds = []
    for line in events.read_text(encoding="utf-8").splitlines():
        if '"kind":' in line:
            import json

            kinds.append(json.loads(line).get("kind", ""))
    return kinds


def _cost(spec: ModelSpec | None, tokens_in: int, tokens_out: int) -> float:
    if spec is None:
        return 0.0
    return (
        tokens_in * spec.cost_per_mtok_in
        + tokens_out * spec.cost_per_mtok_out
    ) / 1_000_000


__all__ = [
    "LIVE_FLAG",
    "LiveCaseResult",
    "LiveTarget",
    "discover_live_targets",
    "format_live_scorecard",
    "run_live_scorecard",
]
