"""VerificationGate: nothing ships on an agent's say-so.

Two layers, in order:

1. Deterministic checks — commands with exit codes (tests, lint, type-check,
   schema validation). Cheap, non-negotiable, run first. Output is saved as a
   proof artifact whether it passes or fails.

2. Verifier agent — a model in the "verifier" role judging the ARTIFACTS
   against ACCEPTANCE CRITERIA. It never sees the worker's chain of reasoning
   or chat transcript, only the task, the criteria, and the produced files/
   reports. Independence is what makes the check adversarial rather than
   sycophantic.

Retry ladder on failure (bounded by max_attempts):
   attempt 2: same route, task REFORMULATED with concrete failure evidence
   attempt 3+: route escalated (effort up, then tier up) via Router.escalate
   ladder exhausted / attempts exhausted: gate returns needs_human
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .blast_radius import BlastRadiusExceeded, PhaseBlastRadius
from .events import EventLog
from .loop import LoopResult
from .memory import ProofStore
from .routing import Route


@dataclass
class Check:
    name: str
    command: str            # run under harness control, NOT model control
    timeout: int = 600


@dataclass
class CheckResult:
    name: str
    passed: bool
    output: str
    terminal: bool = False


# Version of the verifier-verdict parsing contract (parse_verdict: last JSON
# verdict object wins; fail closed otherwise). Part of a proven
# brain's bundle identity: bump on ANY behavior change to the parser, because
# a scorecard earned under one parsing contract says nothing about another.
PARSER_VERSION = "2"


CLAIM_STATUSES = frozenset({"reproduced", "refuted", "not_verifiable"})


@dataclass(frozen=True)
class ClaimVerdict:
    """One independently adjudicated acceptance claim.

    Required claims determine the overall verdict. Optional claims remain in
    the result as useful findings but cannot block the gate.
    """

    claim_id: str
    status: str
    required: bool = True
    reason: str = ""
    evidence: tuple[str, ...] = ()


@dataclass
class Verdict:
    passed: bool
    reasons: str
    source: str             # "checks" | "verifier" | "gate" | "consent"
    overall_status: str = ""  # "verified" | "failed" | "cannot_verify"
    claims: tuple[ClaimVerdict, ...] = ()

    def __post_init__(self) -> None:
        # Preserve the long-standing three-positional-argument constructor for
        # checks, gates, consent, and legacy verifier JSON.
        if not self.overall_status:
            self.overall_status = "verified" if self.passed else "failed"


def run_checks(checks: list[Check], workspace: Path, proofs: ProofStore,
               events: EventLog, attempt: int,
               allow_network: bool = False,
               blast_radius: PhaseBlastRadius | None = None,
               readonly_paths: tuple[Path, ...] = ()) -> list[CheckResult]:
    from .sandbox import SandboxUnavailable, wrap as sandbox_wrap
    from .tools.builtin import scrubbed_env
    results = []
    for check in checks:
        try:
            # Checks run agent-produced code (pytest imports the workspace), so
            # they are sandboxed exactly like run_shell and fail closed with it.
            argv = shlex.split(check.command)
            sandboxed = (sandbox_wrap(
                argv, workspace, allow_network=allow_network,
                readonly_paths=readonly_paths)
                if readonly_paths else
                sandbox_wrap(argv, workspace, allow_network=allow_network))
            def apply_check():
                return subprocess.run(
                    sandboxed, cwd=workspace, capture_output=True, text=True,
                    timeout=check.timeout, env=scrubbed_env())
            proc = (blast_radius.apply(f"check:{check.name}", apply_check)
                    if blast_radius is not None else apply_check())
            output = (proc.stdout + proc.stderr)[:50_000]
            if proc.returncode == 71 and "sandbox_apply" in output:
                passed = False
                output = f"sandbox unavailable, check blocked (fail-closed): {output.strip()}"
            else:
                passed = proc.returncode == 0
        except SandboxUnavailable as e:
            passed, output = False, f"sandbox unavailable, check blocked (fail-closed): {e}"
            terminal = False
        except BlastRadiusExceeded as e:
            passed, output = False, e.detail
            terminal = True
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
            passed, output = False, f"check failed to run: {e}"
            terminal = False
        else:
            terminal = False
        proofs.save(f"check-{check.name}-attempt{attempt}.txt",
                    f"$ {check.command}\npassed={passed}\n\n{output}")
        events.emit("check", name=check.name, passed=passed, attempt=attempt)
        results.append(CheckResult(check.name, passed, output, terminal=terminal))
        if terminal:
            break
    return results


def _json_objects(report: str):
    """Yield every parseable JSON object embedded in the text, left to right."""
    dec = json.JSONDecoder()
    idx = 0
    while True:
        start = report.find("{", idx)
        if start == -1:
            return
        try:
            obj, consumed = dec.raw_decode(report[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue
        if isinstance(obj, dict):
            yield obj
        idx = start + max(consumed, 1)


def _failed_parse(reason: str) -> Verdict:
    return Verdict(
        passed=False,
        reasons=reason,
        source="verifier",
        overall_status="cannot_verify",
    )


def _parse_claims(obj: dict) -> Verdict:
    raw_claims = obj.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        return _failed_parse(
            "invalid structured verdict (failing closed): claims must be a "
            "non-empty array")

    claims: list[ClaimVerdict] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_claims):
        if not isinstance(raw, dict):
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim {index} "
                "must be an object")

        claim_id = raw.get("id", raw.get("claim_id"))
        if not isinstance(claim_id, str) or not claim_id.strip():
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim {index} "
                "requires a non-empty id")
        claim_id = claim_id.strip()
        if claim_id in seen_ids:
            return _failed_parse(
                "invalid structured verdict (failing closed): duplicate claim "
                f"id {claim_id!r}")
        seen_ids.add(claim_id)

        status = raw.get("status")
        if status not in CLAIM_STATUSES:
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim "
                f"{claim_id!r} has unknown status {status!r}")

        required = raw.get("required", True)
        if not isinstance(required, bool):
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim "
                f"{claim_id!r} required must be boolean")

        reason = raw.get("reason", "")
        if not isinstance(reason, str):
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim "
                f"{claim_id!r} reason must be a string")

        raw_evidence = raw.get("evidence", [])
        if isinstance(raw_evidence, str):
            evidence = (raw_evidence,)
        elif (isinstance(raw_evidence, list)
              and all(isinstance(item, str) for item in raw_evidence)):
            evidence = tuple(raw_evidence)
        else:
            return _failed_parse(
                f"invalid structured verdict (failing closed): claim "
                f"{claim_id!r} evidence must be a string or array of strings")

        claims.append(ClaimVerdict(
            claim_id=claim_id,
            status=status,
            required=required,
            reason=reason[:2000],
            evidence=evidence,
        ))

    required_claims = [claim for claim in claims if claim.required]
    if not required_claims:
        return _failed_parse(
            "invalid structured verdict (failing closed): at least one claim "
            "must be required")

    if any(claim.status == "refuted" for claim in required_claims):
        overall_status = "failed"
    elif any(claim.status == "not_verifiable" for claim in required_claims):
        overall_status = "cannot_verify"
    else:
        overall_status = "verified"

    supplied_reasons = obj.get("reasons", "")
    if not isinstance(supplied_reasons, str):
        return _failed_parse(
            "invalid structured verdict (failing closed): reasons must be a "
            "string")
    if supplied_reasons:
        reasons = supplied_reasons[:2000]
    else:
        findings = [
            f"{claim.claim_id}: {claim.status}"
            + (f" ({claim.reason})" if claim.reason else "")
            for claim in required_claims
            if claim.status != "reproduced"
        ]
        reasons = "; ".join(findings)[:2000]
        if not reasons:
            reasons = "all required claims reproduced"

    return Verdict(
        passed=overall_status == "verified",
        reasons=reasons,
        source="verifier",
        overall_status=overall_status,
        claims=tuple(claims),
    )


def parse_verdict(report: str) -> Verdict:
    """The verifier contract says the report ENDS with exactly one JSON verdict
    object. Weaker models wrap it in prose or quote example objects earlier, so
    take the LAST parseable object carrying either the legacy ``passed`` key or
    structured ``claims``: the contract's final-position object always wins
    over anything quoted before it.

    passed must be boolean true (string "true" tolerated for weak models).
    Any other shape, and reports with no verdict object at all, fail closed:
    at a gate, a false FAIL costs one retry; a false PASS ships a defect."""
    verdict_obj = None
    for obj in _json_objects(report):
        if "passed" in obj or "claims" in obj:
            verdict_obj = obj
    if verdict_obj is None:
        return _failed_parse(
            "no JSON verdict object found (failing closed): " + report[:500])
    if "claims" in verdict_obj:
        return _parse_claims(verdict_obj)
    passed = verdict_obj["passed"]
    ok = passed is True or (isinstance(passed, str) and passed.strip().lower() == "true")
    return Verdict(passed=ok,
                   reasons=str(verdict_obj.get("reasons", ""))[:2000],
                   source="verifier",
                   overall_status="verified" if ok else "failed")


@dataclass
class GateResult:
    status: str             # "passed" | "needs_human"
    attempts: int
    final_report: str
    verdicts: list[Verdict] = field(default_factory=list)


@dataclass
class VerificationGate:
    workspace: Path
    proofs: ProofStore
    events: EventLog
    max_attempts: int = 3

    def run(
        self,
        task: str,
        attempt_fn: Callable[[str, Route], LoopResult],   # runs the worker
        verify_fn: Callable[[str], LoopResult] | None,     # runs the verifier agent
        checks: list[Check],
        route: Route,
        allow_network: bool = False,
        # Deterministic checks the HARNESS computes in-process (no shell, no
        # sandbox): callables (attempt:int) -> CheckResult. e.g. memory_lint.
        harness_checks: list[Callable[[int], CheckResult]] | None = None,
        # Cascade opt-in (0.7): replaces the default Route.escalate() walk
        # with a policy-driven decision. Receives (current_route, failing
        # verdict); returns the next route, the same route to hold, or None
        # when the ladder is exhausted. Phases that do not opt in get the
        # default — byte-identical to the pre-cascade ladder.
        escalate_fn: Callable[[Route, "Verdict"], Route | None] | None = None,
        blast_radius: PhaseBlastRadius | None = None,
        readonly_paths: tuple[Path, ...] = (),
    ) -> GateResult:
        verdicts: list[Verdict] = []
        current_task, current_route = task, route
        counter_used = False

        for attempt in range(1, self.max_attempts + 1):
            work = attempt_fn(current_task, current_route)
            if work.stop == "declined":
                # Consent withheld — a disagreement, not a capability failure.
                # One re-offer on a counter-proposal (Turnfile's bounded
                # rebuttal), then the operator. The route is NEVER escalated
                # on a decline: punishing refusal with a bigger model teaches
                # the system to steamroll objections.
                reason = str(work.detail.get("reason", work.report))
                counter = str(work.detail.get("counter_proposal", ""))
                verdicts.append(Verdict(False, f"consent declined: {reason}",
                                        "consent"))
                self.events.emit("gate_verdict", attempt=attempt, passed=False,
                                 source="consent", route={"tier": current_route.tier,
                                    "effort": current_route.effort})
                if counter and not counter_used:
                    counter_used = True
                    current_task = (
                        f"{task}\n\n## Re-offer after decline\n"
                        f"The previously assigned agent declined this task: {reason}\n"
                        f"Its counter-proposal:\n{counter}\n\n"
                        "The task is re-offered incorporating that counter-proposal. "
                        "Accept it only if you judge it achievable as specified; "
                        "declining again hands the decision to the operator.")
                    continue
                return GateResult("needs_human", len(verdicts),
                                  f"task declined by agent: {reason}", verdicts)
            if work.stop == "blast_radius":
                verdict = Verdict(
                    False, f"blast radius exceeded: {work.report}", "gate")
                verdicts.append(verdict)
                self.events.emit(
                    "gate_verdict", attempt=attempt, passed=False,
                    source="gate", terminal=True,
                    route={"tier": current_route.tier,
                           "effort": current_route.effort})
                return GateResult(
                    "needs_human", attempt, work.report, verdicts)
            if not work.ok:
                verdict = Verdict(False, f"worker loop stopped: {work.stop}: "
                                         f"{work.report[:500]}", "gate")
            else:
                check_results = run_checks(checks, self.workspace, self.proofs,
                                           self.events, attempt,
                                           allow_network=allow_network,
                                           blast_radius=blast_radius,
                                           readonly_paths=readonly_paths)
                terminal = next(
                    (result for result in check_results if result.terminal), None)
                if terminal is not None:
                    verdict = Verdict(
                        False, f"blast radius exceeded: {terminal.output}",
                        "checks")
                    verdicts.append(verdict)
                    self.events.emit(
                        "gate_verdict", attempt=attempt, passed=False,
                        source="checks", terminal=True,
                        route={"tier": current_route.tier,
                               "effort": current_route.effort})
                    return GateResult(
                        "needs_human", attempt, terminal.output, verdicts)
                for hc in (harness_checks or []):
                    result = hc(attempt)
                    self.proofs.save(f"check-{result.name}-attempt{attempt}.txt",
                                     f"(harness check)\npassed={result.passed}\n\n"
                                     f"{result.output}")
                    self.events.emit("check", name=result.name,
                                     passed=result.passed, attempt=attempt)
                    check_results.append(result)
                failed = [c for c in check_results if not c.passed]
                if failed:
                    detail = "\n".join(f"[{c.name}] {c.output[:800]}" for c in failed)
                    verdict = Verdict(False, f"deterministic checks failed:\n{detail}",
                                      "checks")
                elif verify_fn is not None:
                    vres = verify_fn(work.report)
                    verdict = (parse_verdict(vres.report) if vres.ok else
                               Verdict(False, f"verifier loop stopped: {vres.stop}",
                                       "gate"))
                else:
                    verdict = Verdict(True, "checks passed; no verifier configured",
                                      "checks")

            verdicts.append(verdict)
            self.events.emit("gate_verdict", attempt=attempt, passed=verdict.passed,
                             source=verdict.source, route={"tier": current_route.tier,
                                    "effort": current_route.effort})
            if verdict.passed:
                return GateResult("passed", attempt, work.report, verdicts)

            # Reformulate with evidence — retrying the identical prompt against
            # the same model mostly reproduces the identical failure.
            current_task = (
                f"{task}\n\n## Previous attempt {attempt} FAILED\n"
                f"{verdict.reasons[:3000]}\n\n"
                "Do not repeat the failed approach. Address every failure above, "
                "then re-run the relevant checks yourself before calling task_complete.")
            if attempt >= 2:
                if escalate_fn is not None:
                    nxt = escalate_fn(current_route, verdict)
                else:
                    nxt = current_route.escalate()
                if nxt is None:
                    break
                current_route = nxt

        last = verdicts[-1].reasons[:800] if verdicts else "(no verdicts)"
        return GateResult("needs_human", len(verdicts),
                          "verification failed after escalation ladder; "
                          f"operator review required. Last verdict: {last}",
                          verdicts)
