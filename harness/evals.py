"""Deterministic eval runner for Harnessie.

The baseline suite uses a scripted mock brain, not live endpoints. That keeps
it network-free and makes it suitable for CI. Live brain scorecards are a later
layer built on the same scenario shape.
"""

from __future__ import annotations

import json
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .events import EventLog
from .loop import AgentLoop
from .models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from .runner import WorkflowRunner
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import parse_verdict


@dataclass
class EvalCaseResult:
    id: str
    passed: bool
    expected: Any
    observed: Any
    notes: str = ""


def load_eval_files(root: Path, suite_path: Path | None = None) -> list[Path]:
    if suite_path is not None:
        return [suite_path]
    eval_dir = root / "evals"
    return sorted(eval_dir.glob("*.yaml")) if eval_dir.exists() else []


def run_eval_suite(root: Path, suite_path: Path | None = None) -> dict[str, Any]:
    files = load_eval_files(root, suite_path)
    results: list[EvalCaseResult] = []
    for path in files:
        suite = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for scenario in suite.get("scenarios", []):
            results.append(run_scenario(scenario))
    passed = sum(1 for r in results if r.passed)
    return {
        "passed": passed,
        "total": len(results),
        "results": [r.__dict__ for r in results],
    }


def run_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    kind = scenario.get("kind")
    if kind == "verdict":
        verdict = parse_verdict(scenario.get("report", ""))
        expected = bool(scenario["expect_passed"])
        observed = verdict.passed
        return EvalCaseResult(
            id=scenario["id"],
            passed=observed == expected,
            expected=expected,
            observed=observed,
            notes=verdict.reasons,
        )
    if kind == "loop":
        return _run_loop_scenario(scenario)
    if kind == "workflow":
        return _run_workflow_scenario(scenario)
    if kind == "resume":
        return _run_resume_scenario(scenario)
    return EvalCaseResult(
        id=scenario.get("id", "(missing-id)"),
        passed=False,
        expected="known scenario kind",
        observed=kind,
        notes="unknown scenario kind",
    )


def _run_loop_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        reg = ToolRegistry()
        workspace = root / "workspace"
        workspace.mkdir()
        register_builtin(reg, workspace=workspace)
        model = MockModel(
            ModelSpec(name="mid", provider="mock", model_id="mock"),
            script=[_turn(t, i) for i, t in enumerate(scenario.get("script", []), 1)],
        )
        loop = AgentLoop(
            role=scenario.get("role", "worker"),
            model=model,
            registry=reg,
            events=EventLog(root / "run", echo=False),
            max_steps=int(scenario.get("max_steps", 4)),
        )
        result = loop.run("system", scenario.get("task", "task"))
    expected = scenario["expect_stop"]
    return EvalCaseResult(
        id=scenario["id"],
        passed=result.stop == expected,
        expected=expected,
        observed=result.stop,
        notes=result.report[:500],
    )


def _run_workflow_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=int(scenario.get("max_attempts", 2)))
        statuses = _run_scripted_workflow(root, "evalrun", scenario.get("script", []),
                                          scenario.get("goal", "eval goal"))
    expected = scenario["expect_statuses"]
    return EvalCaseResult(
        id=scenario["id"],
        passed=statuses == expected,
        expected=expected,
        observed=statuses,
    )


def _run_resume_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=int(scenario.get("max_attempts", 2)))
        first = _run_scripted_workflow(root, "evalrun", scenario.get("first_script", []),
                                       scenario.get("goal", "eval goal"))
        second = _run_scripted_workflow(root, "evalrun", scenario.get("second_script", []),
                                        scenario.get("goal", "eval goal"))
    expected = {
        "first": scenario["expect_first_statuses"],
        "second": scenario["expect_second_statuses"],
    }
    observed = {"first": first, "second": second}
    return EvalCaseResult(
        id=scenario["id"],
        passed=observed == expected,
        expected=expected,
        observed=observed,
    )


def _run_scripted_workflow(root: Path, run_id: str, script: list[dict[str, Any]],
                           goal: str) -> list[str]:
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=[_turn(t, i) for i, t in enumerate(script, 1)],
    )
    outcomes = runner.run_workflow(root / "workflows" / "eval.yaml", goal=goal)
    return [o.status for o in outcomes]


def _turn(spec: dict[str, Any], idx: int) -> AssistantTurn:
    if "tool" in spec:
        return AssistantTurn(
            content=spec.get("content", ""),
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(
                    id=spec.get("id", f"call_{idx}"),
                    name=spec["tool"],
                    arguments=spec.get("args", {}),
                )
            ],
        )
    return AssistantTurn(
        content=spec.get("content", ""),
        stop_reason=spec.get("stop_reason", "end_turn"),
        input_tokens=int(spec.get("input_tokens", 0)),
        output_tokens=int(spec.get("output_tokens", 0)),
    )


def _scaffold_eval_project(root: Path, max_attempts: int) -> None:
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan and integrate.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo the task.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge it.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock
        routing:
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    (root / "workflows" / "eval.yaml").write_text(textwrap.dedent(f"""
        name: eval
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {{goal}}"
          - name: implement
            agent: implementer
            task: "Do this plan: {{plan}}"
            verify:
              max_attempts: {max_attempts}
              verifier: code-verifier
              criteria: artifact satisfies the plan
          - name: integrate
            agent: orchestrator
            task: "Summarize: {{implement}}"
    """))


def format_scorecard(scorecard: dict[str, Any]) -> str:
    lines = [f"eval scorecard: {scorecard['passed']}/{scorecard['total']} passed"]
    for result in scorecard["results"]:
        mark = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"{mark} {result['id']}: expected={json.dumps(result['expected'])} "
            f"observed={json.dumps(result['observed'])}")
        if result.get("notes") and not result["passed"]:
            lines.append(f"  {result['notes'][:500]}")
    return "\n".join(lines)
