"""Standalone verification surface: `harnessie verify` (decisions/AIDR-0006).

Point the VerificationGate's two layers at an arbitrary workspace and a claims
file, with no project scaffold, no orchestrator, and no run manifest:

    harnessie verify --workspace <dir> --criteria <claims.md> \
        [--check "<cmd>" ...] [--report-dir <dir>] [--models <models.yaml>]

Exit contract (fail closed, scriptable as a Ringer check or CI step):
    0  verified      every deterministic check passed AND the verifier agent
                     judged the criteria met
    1  failed        a check failed, or the verifier judged the criteria unmet
    2  cannot verify infrastructure could not produce a verdict: missing
                     config, sandbox unavailable, provider/model error, step
                     ceiling. Never reported as pass OR fail, because neither
                     was earned.

What is deliberately NOT here (scope guards from AIDR-0006):
- No retry/escalation ladder. The gate reformulates a WORKER's task on
  failure; a standalone verify judges someone else's finished artifact, so a
  failure is the answer, not a prompt to try again.
- No hash-chained EventLog requirement beyond what EventLog already writes to
  the report directory; the tamper-evident audit earns its keep inside
  governed runs.
- No containment routing. The verifier judges whatever workspace it is given
  on whatever model the operator configured. Verification of untrusted diffs
  belongs on models you control; the report header states the model used so
  the reader can judge that call.

Deterministic checks reuse run_checks and therefore inherit its sandbox
fail-closed behavior. The verifier agent is read-only plus allowlisted test
execution (registry-enforced), single pass, network-denied.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .events import EventLog
from .loop import AgentLoop
from .memory import ProofStore
from .models import build_model
from .roles import RoleDef
from .routing import Budget, Route, Router
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import Check, CheckResult, parse_verdict, run_checks
from .verify_evidence import (
    EvidenceBundle,
    EvidenceValidationError,
    load_evidence_bundle,
    register_evidence_reader,
)

EXIT_VERIFIED = 0
EXIT_FAILED = 1
EXIT_CANNOT_VERIFY = 2

# Marker run_checks prefixes onto a check blocked by a missing sandbox (see
# verify.run_checks). Standalone, that is "cannot verify", not "failed":
# nothing was observed about the artifact.
_SANDBOX_BLOCKED = "sandbox unavailable, check blocked"

# Built-in verifier prompt, so no agents/ scaffold is required. A project may
# override it with --verifier-prompt. Boundaries are appended by RoleDef and
# cannot be removed by the override.
DEFAULT_VERIFIER_PROMPT = """\
# Verifier

You independently verify finished work against stated acceptance criteria.
The criteria arrive as CLAIMS made by whoever produced the work; your job is
to test each claim against the artifacts actually present in the workspace,
using your read tools and allowlisted shell commands.

For verifier `run_shell`, the complete command allowlist is `ls`, `cat`,
`grep`, and `pytest`. Do not call `git`, Python interpreters, or any other
command. Inspect a staged diff with `read_file` instead of `git diff`.

Work claim by claim. For each claim, state what evidence you inspected and
whether the evidence supports it: reproduced, refuted, or not verifiable in
this environment (say exactly why). A claim you could not check is NOT a
passing claim.

Then call task_complete. Your report must contain the claim-by-claim findings
and END with one JSON object in this exact structural form:
{"claims":[{"id":"C1","status":"reproduced|refuted|not_verifiable",
"required":true,"reason":"concise basis","evidence":["path or command"]}],
"reasons":"overall summary"}

Use the criterion's own stable identifier when it has one; otherwise assign
`C1`, `C2`, and so on in source order. Include every acceptance claim exactly
once. Do not emit the legacy boolean-only verdict unless an operator-supplied
prompt explicitly requires that compatibility format.
"""


@dataclass
class VerifyRequest:
    workspace: Path
    criteria_path: Path | None
    checks: list[Check] = field(default_factory=list)
    report_dir: Path | None = None
    models_path: Path | None = None       # default: <cwd>/config/models.yaml
    task_class: str = "verify"
    tier: str = ""                        # explicit tier overrides task_class
    verifier_prompt_path: Path | None = None
    no_verifier: bool = False             # deterministic checks only
    # Checks run network-denied by default; artifacts whose own tests bind
    # sockets (dev servers, port scans) need the opt-in. The verifier AGENT
    # stays network-denied regardless.
    allow_network: bool = False
    max_steps: int = 20
    echo: bool = True
    evidence_bundle_path: Path | None = None
    evidence_root: Path | None = None


@dataclass
class VerifyOutcome:
    exit_code: int
    report_path: Path | None
    summary: str


def _workspace_git_state(workspace: Path) -> tuple[str, bool] | None:
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace,
                             capture_output=True, text=True, timeout=10)
        if rev.returncode != 0:
            return None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=workspace,
                               capture_output=True, text=True, timeout=10)
        if dirty.returncode != 0:
            return None
        return rev.stdout.strip(), bool(dirty.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return None


def _input_fingerprint(workspace: Path, criteria_text: str) -> dict[str, str]:
    """Identify what was verified: criteria hash plus the workspace's git
    revision when available (a full workspace content hash is not attempted;
    the git line is honest about dirtiness instead)."""
    fp = {"criteria_sha256": hashlib.sha256(criteria_text.encode()).hexdigest()}
    state = _workspace_git_state(workspace)
    if state is not None:
        revision, dirty = state
        fp["git_rev"] = revision + (" (dirty)" if dirty else "")
    return fp


def _bundle_criteria(bundle: EvidenceBundle) -> str:
    lines = ["# Acceptance claims from evidence bundle", ""]
    for claim in bundle.data["claims"]:
        required = claim.get("required", True)
        lines.append(
            f"- [{claim['id']}] {claim['statement']} "
            f"({'required' if required else 'optional'})")
        bindings = []
        if claim.get("diff"):
            bindings.append("diff")
        bindings.extend(claim.get("evidence", []))
        bindings.extend(f"check:{item}" for item in claim.get("checks", []))
        lines.append(f"  Evidence bindings: {', '.join(bindings)}")
    lines.extend(["", "## Recorded deterministic checks", ""])
    checks = bundle.data.get("checks", [])
    if not checks:
        lines.append("(none recorded)")
    for check in checks:
        platform = f"; platform={check['platform']}" if check.get("platform") else ""
        lines.append(
            f"- [{check['id']}] exit={check['exit_code']}{platform}; "
            f"command={check['command']}")
    return "\n".join(lines) + "\n"


def _render_report(*, workspace: Path, criteria_path: Path,
                   fingerprint: dict[str, str], model_line: str,
                   check_results: list[CheckResult], verifier_section: str,
                   exit_code: int, generated: str,
                   allow_network: bool = False) -> str:
    verdict_word = {EXIT_VERIFIED: "VERIFIED", EXIT_FAILED: "FAILED",
                    EXIT_CANNOT_VERIFY: "CANNOT VERIFY"}[exit_code]
    lines = [
        f"# Verification report: {verdict_word}",
        "",
        f"- generated: {generated}",
        f"- workspace: {workspace}",
        f"- criteria: {criteria_path}",
    ]
    lines += [f"- {k}: {v}" for k, v in fingerprint.items()]
    lines += [f"- verifier model: {model_line}",
              "- checks network: "
              + ("allowed (--allow-network)" if allow_network else "denied"),
              f"- exit code: {exit_code} "
              "(0 verified / 1 failed / 2 cannot verify, fail closed)",
              "", "## Deterministic checks", ""]
    if check_results:
        for c in check_results:
            status = "PASS" if c.passed else "FAIL"
            lines.append(f"### [{status}] {c.name}")
            lines.append("")
            lines.append("```")
            lines.append(c.output.strip()[:4000] or "(no output)")
            lines.append("```")
            lines.append("")
    else:
        lines += ["(none supplied)", ""]
    lines += ["## Verifier judgment", "", verifier_section.strip(), ""]
    return "\n".join(lines)


def run_standalone_verify(req: VerifyRequest) -> VerifyOutcome:
    workspace = req.workspace.resolve()
    if not workspace.is_dir():
        return VerifyOutcome(EXIT_CANNOT_VERIFY, None,
                             f"workspace is not a directory: {workspace}")
    if bool(req.criteria_path) == bool(req.evidence_bundle_path):
        return VerifyOutcome(
            EXIT_CANNOT_VERIFY, None,
            "provide exactly one of criteria_path or evidence_bundle_path")

    evidence_bundle = None
    if req.evidence_bundle_path is not None:
        if req.evidence_root is None:
            return VerifyOutcome(EXIT_CANNOT_VERIFY, None,
                                 "evidence_root is required with an evidence bundle")
        git_state = _workspace_git_state(workspace)
        if git_state is None:
            return VerifyOutcome(
                EXIT_CANNOT_VERIFY, None,
                "evidence bundle requires an observable Git workspace revision")
        try:
            evidence_bundle = load_evidence_bundle(
                req.evidence_bundle_path,
                evidence_root=req.evidence_root,
                current_revision=git_state[0],
                current_dirty=git_state[1],
            )
        except EvidenceValidationError as exc:
            return VerifyOutcome(EXIT_CANNOT_VERIFY, None,
                                 f"evidence bundle preflight failed: {exc}")
        criteria = _bundle_criteria(evidence_bundle)
        criteria_path = evidence_bundle.source
    else:
        assert req.criteria_path is not None
        if not req.criteria_path.is_file():
            return VerifyOutcome(EXIT_CANNOT_VERIFY, None,
                                 f"criteria file not found: {req.criteria_path}")
        criteria = req.criteria_path.read_text(encoding="utf-8")
        criteria_path = req.criteria_path

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_dir = (req.report_dir or
                  Path.cwd() / "verify-reports" /
                  datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")).resolve()
    if report_dir == workspace:
        return VerifyOutcome(EXIT_CANNOT_VERIFY, None,
                             "report dir must not be the workspace itself")
    report_dir.mkdir(parents=True, exist_ok=True)
    events = EventLog(report_dir, echo=False)
    proofs = ProofStore(report_dir)

    # -- model resolution (before any check runs: refuse early, bill nothing)
    model = None
    model_line = "(none — deterministic checks only)"
    route = Route(tier="mid", effort="medium")
    budget = Budget()
    if not req.no_verifier:
        models_path = req.models_path or Path.cwd() / "config" / "models.yaml"
        if not models_path.is_file():
            return VerifyOutcome(
                EXIT_CANNOT_VERIFY, None,
                f"no models config at {models_path}; pass --models or run "
                "with --no-verifier for deterministic checks only")
        from .runner import load_models_config  # deferred: import cost
        tiers, routing_table, budget_cfg, fallbacks = \
            load_models_config(models_path)
        router = Router(tiers=tiers, table=routing_table, fallbacks=fallbacks)
        route = (Route(tier=req.tier, effort="medium") if req.tier
                 else router.route(req.task_class))
        try:
            spec = router.spec_for(route)
            model = build_model(spec)
        except ValueError as e:
            return VerifyOutcome(EXIT_CANNOT_VERIFY, None, str(e))
        budget = Budget(**budget_cfg)
        model_line = f"{spec.model_id} ({spec.provider}, tier {spec.name})"

    # -- layer 1: deterministic checks (sandboxed, fail closed)
    check_results = run_checks(req.checks, workspace, proofs, events,
                               attempt=1, allow_network=req.allow_network)
    blocked = [c for c in check_results
               if not c.passed and c.output.startswith(_SANDBOX_BLOCKED)]
    failed = [c for c in check_results
              if not c.passed and not c.output.startswith(_SANDBOX_BLOCKED)]

    def finish(exit_code: int, verifier_section: str) -> VerifyOutcome:
        fingerprint = _input_fingerprint(workspace, criteria)
        if evidence_bundle is not None:
            fingerprint["evidence_bundle_sha256"] = hashlib.sha256(
                evidence_bundle.source.read_bytes()).hexdigest()
        report = _render_report(
            workspace=workspace, criteria_path=criteria_path,
            fingerprint=fingerprint,
            model_line=model_line, check_results=check_results,
            verifier_section=verifier_section, exit_code=exit_code,
            generated=generated, allow_network=req.allow_network)
        path = report_dir / "report.md"
        path.write_text(report, encoding="utf-8")
        events.emit("verify_done", exit_code=exit_code,
                    workspace=str(workspace))
        from .trace_eval import analyze_trace, load_events
        expected_claims = (
            [claim["id"] for claim in evidence_bundle.data["claims"]]
            if evidence_bundle is not None else [])
        metrics = analyze_trace(load_events(report_dir / "events.jsonl"),
                                claim_ids=expected_claims)
        proofs.save("trace-metrics.json",
                    json.dumps(metrics, indent=2, sort_keys=True) + "\n")
        word = {0: "VERIFIED", 1: "FAILED", 2: "CANNOT VERIFY"}[exit_code]
        return VerifyOutcome(exit_code, path, f"{word}: {path}")

    if blocked:
        names = ", ".join(c.name for c in blocked)
        return finish(EXIT_CANNOT_VERIFY,
                      f"(not consulted: sandbox unavailable for checks: {names}; "
                      "nothing was observed, so no verdict is earned)")
    if failed:
        names = ", ".join(c.name for c in failed)
        return finish(EXIT_FAILED,
                      f"(not consulted: deterministic checks already failed: {names})")
    if req.no_verifier:
        return finish(EXIT_VERIFIED if check_results else EXIT_CANNOT_VERIFY,
                      "(skipped by --no-verifier; verdict rests on the checks above)"
                      if check_results else
                      "(--no-verifier with no checks supplied: nothing was "
                      "verified, failing closed)")

    # -- layer 2: verifier agent, single pass, read-only + test execution
    prompt = (req.verifier_prompt_path.read_text(encoding="utf-8")
              if req.verifier_prompt_path else DEFAULT_VERIFIER_PROMPT)
    role = RoleDef(name="verifier", kind="verifier", prompt=prompt)
    registry = ToolRegistry()
    register_builtin(registry, workspace=workspace, events=events)
    if evidence_bundle is not None and evidence_bundle.files:
        register_evidence_reader(registry, evidence_bundle)
    loop = AgentLoop(role="verifier", model=model, registry=registry,
                     events=events, budget=budget, max_steps=req.max_steps,
                     agent_name="verifier")
    evidence_hint = ""
    if evidence_bundle is not None:
        if evidence_bundle.files:
            evidence_hint += (
                "Use read_evidence for the content-addressed proof files bound "
                "above. ")
        evidence_hint += (
            "Recorded check results are evidence, not a substitute for your "
            "independent judgment. ")
    task = (
        "Verify this workspace against acceptance criteria.\n\n"
        f"## Acceptance criteria (claims, unverified)\n{criteria}\n\n"
        "Inspect the actual artifacts in the workspace with your tools. "
        + evidence_hint
        +
        "Treat every claim as a claim to test, not a fact. Then call "
        "task_complete with your claim-by-claim findings, ending with your "
        "JSON verdict.")
    result = loop.run(role.system_prompt(), task, effort=route.effort)
    proofs.save("verifier-report.txt", result.report)

    if not result.ok:
        return finish(EXIT_CANNOT_VERIFY,
                      f"(verifier loop stopped without a verdict: {result.stop}: "
                      f"{result.report[:800]})")
    verdict = parse_verdict(result.report)
    for claim in verdict.claims:
        events.emit("claim_verdict", claim_id=claim.claim_id,
                    status=claim.status, required=claim.required,
                    evidence=list(claim.evidence))
    if evidence_bundle is not None:
        if not verdict.claims:
            section = (
                "Verdict: CANNOT VERIFY (source: verifier)\n\n"
                "Evidence-bundle verification requires a structured claim "
                f"verdict; the verifier returned none.\n\n{result.report}")
            return finish(EXIT_CANNOT_VERIFY, section)
        expected_ids = {claim["id"] for claim in evidence_bundle.data["claims"]}
        observed_ids = {claim.claim_id for claim in verdict.claims}
        if observed_ids != expected_ids:
            missing = sorted(expected_ids - observed_ids)
            unknown = sorted(observed_ids - expected_ids)
            section = (
                "Verdict: CANNOT VERIFY (source: verifier)\n\n"
                "Structured verdict claim coverage did not match the evidence "
                f"bundle: missing={missing}, unknown={unknown}.\n\n{result.report}")
            return finish(EXIT_CANNOT_VERIFY, section)
        expected_required = {
            claim["id"]: claim.get("required", True)
            for claim in evidence_bundle.data["claims"]}
        mismatched_required = sorted(
            claim.claim_id for claim in verdict.claims
            if claim.required is not expected_required[claim.claim_id])
        if mismatched_required:
            section = (
                "Verdict: CANNOT VERIFY (source: verifier)\n\n"
                "Structured verdict changed bundle-owned required/optional "
                f"classification for claims: {mismatched_required}.\n\n"
                f"{result.report}")
            return finish(EXIT_CANNOT_VERIFY, section)
    exit_code = {
        "verified": EXIT_VERIFIED,
        "failed": EXIT_FAILED,
        "cannot_verify": EXIT_CANNOT_VERIFY,
    }.get(verdict.overall_status, EXIT_CANNOT_VERIFY)
    label = {
        EXIT_VERIFIED: "PASS",
        EXIT_FAILED: "FAIL",
        EXIT_CANNOT_VERIFY: "CANNOT VERIFY",
    }[exit_code]
    section = (f"Verdict: {label} (source: {verdict.source})\n\n"
               f"{result.report}")
    return finish(exit_code, section)
