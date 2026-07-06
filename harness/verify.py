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


@dataclass
class Verdict:
    passed: bool
    reasons: str
    source: str             # "checks" | "verifier" | "gate" | "consent"


def run_checks(checks: list[Check], workspace: Path, proofs: ProofStore,
               events: EventLog, attempt: int,
               allow_network: bool = False) -> list[CheckResult]:
    from .sandbox import SandboxUnavailable, wrap as sandbox_wrap
    from .tools.builtin import scrubbed_env
    results = []
    for check in checks:
        try:
            # Checks run agent-produced code (pytest imports the workspace), so
            # they are sandboxed exactly like run_shell and fail closed with it.
            sandboxed = sandbox_wrap(shlex.split(check.command), workspace,
                                     allow_network=allow_network)
            proc = subprocess.run(sandboxed, cwd=workspace,
                                  capture_output=True, text=True,
                                  timeout=check.timeout, env=scrubbed_env())
            output = (proc.stdout + proc.stderr)[:50_000]
            if proc.returncode == 71 and "sandbox_apply" in output:
                passed = False
                output = f"sandbox unavailable, check blocked (fail-closed): {output.strip()}"
            else:
                passed = proc.returncode == 0
        except SandboxUnavailable as e:
            passed, output = False, f"sandbox unavailable, check blocked (fail-closed): {e}"
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
            passed, output = False, f"check failed to run: {e}"
        proofs.save(f"check-{check.name}-attempt{attempt}.txt",
                    f"$ {check.command}\npassed={passed}\n\n{output}")
        events.emit("check", name=check.name, passed=passed, attempt=attempt)
        results.append(CheckResult(check.name, passed, output))
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


def parse_verdict(report: str) -> Verdict:
    """The verifier contract says the report ENDS with exactly one JSON verdict
    object. Weaker models wrap it in prose or quote example objects earlier, so
    take the LAST parseable object carrying a "passed" key: the contract's
    final-position object always wins over anything quoted before it.

    passed must be boolean true (string "true" tolerated for weak models).
    Any other shape, and reports with no verdict object at all, fail closed:
    at a gate, a false FAIL costs one retry; a false PASS ships a defect."""
    verdict_obj = None
    for obj in _json_objects(report):
        if "passed" in obj:
            verdict_obj = obj
    if verdict_obj is None:
        return Verdict(passed=False,
                       reasons="no JSON verdict object found (failing closed): "
                               + report[:500],
                       source="verifier")
    passed = verdict_obj["passed"]
    ok = passed is True or (isinstance(passed, str) and passed.strip().lower() == "true")
    return Verdict(passed=ok,
                   reasons=str(verdict_obj.get("reasons", ""))[:2000],
                   source="verifier")


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
                                 source="consent", route=vars(current_route))
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
            if not work.ok:
                verdict = Verdict(False, f"worker loop stopped: {work.stop}: "
                                         f"{work.report[:500]}", "gate")
            else:
                check_results = run_checks(checks, self.workspace, self.proofs,
                                           self.events, attempt,
                                           allow_network=allow_network)
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
                             source=verdict.source, route=vars(current_route))
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
                nxt = current_route.escalate()
                if nxt is None:
                    break
                current_route = nxt

        last = verdicts[-1].reasons[:800] if verdicts else "(no verdicts)"
        return GateResult("needs_human", len(verdicts),
                          "verification failed after escalation ladder; "
                          f"operator review required. Last verdict: {last}",
                          verdicts)
