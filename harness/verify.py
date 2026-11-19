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

import errno
import json
import os
import selectors
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .blast_radius import BlastRadiusExceeded, PhaseBlastRadius
from .events import EventLog
from .loop import LoopResult
from .memory import ProofStore
from .quarantine import redact_secrets
from .routing import Route


def _redacted(text: str, limit: int) -> str:
    """Redact credential-shaped strings, then cut: cutting first could leave
    a partial secret the patterns no longer match."""
    return redact_secrets(text)[0][:limit]


@dataclass
class Check:
    name: str
    command: str            # run under harness control, NOT model control
    timeout: int = 600


# Structured check outcomes. Only CHECK_FAILED means the check executed and
# reported a failure about the artifact; every other non-pass outcome means
# nothing was observed (standalone verify maps those to cannot-verify).
CHECK_PASSED = "passed"
CHECK_FAILED = "failed"
CHECK_BLOCKED = "blocked"      # sandbox, missing/denied executable, malformed command
CHECK_TIMEOUT = "timeout"
CHECK_RESOURCE = "resource"    # blast radius, or a descendant escaped cleanup
# Only a check that never launched is cannot-verify. A launched check that
# hangs, escapes cleanup or exceeds its blast radius is an observed failure;
# otherwise a failing artifact could make itself unscorable.
CHECK_NOT_EXECUTED = frozenset({CHECK_BLOCKED})
CHECK_FAILED_OUTCOMES = frozenset({CHECK_FAILED, CHECK_TIMEOUT, CHECK_RESOURCE})

# Per-stream byte ceiling for check output. Bytes past it are drained and
# discarded so the child never blocks on a full pipe and memory stays bounded.
CHECK_OUTPUT_LIMIT_BYTES = 50_000
# After the direct child exits its process group is killed, and the pipes get
# this long to reach EOF before a holder is treated as an escaped descendant.
_PIPE_DRAIN_GRACE_SECONDS = 1.0


@dataclass
class CheckResult:
    name: str
    passed: bool
    output: str
    terminal: bool = False
    outcome: str = ""
    truncated: bool = False

    def __post_init__(self) -> None:
        if not self.outcome:
            self.outcome = CHECK_PASSED if self.passed else CHECK_FAILED
        if self.passed is not (self.outcome == CHECK_PASSED):
            raise ValueError(
                f"check {self.name!r}: passed={self.passed!r} contradicts "
                f"outcome {self.outcome!r}")


@dataclass
class _BoundedRun:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    stdout_over: bool
    stderr_over: bool
    timed_out: bool
    escaped: bool

    @property
    def truncated(self) -> bool:
        return self.stdout_over or self.stderr_over


class _CheckBlocked(Exception):
    pass


def _resolve_executable(argv: list[str], workspace: Path,
                        env: dict[str, str], launcher: list[str]) -> None:
    """Refuse, before any wrapper runs, a check whose program cannot be
    executed. A launcher's own exit status is indistinguishable from the
    program's, so this must be decided before launch, not inferred after.

    Checks launch with no shell (VAR=value prefixes are not assignments),
    cwd=workspace and exactly ``env``; the wrapper execvp's argv[0]. So a
    relative program path and relative or empty PATH entries resolve from
    the workspace, never from the harness's own cwd. A docker launcher
    resolves inside its image, which the host cannot see: there only a
    workspace-relative program is checked, and anything else launches and
    is classified by its observed result."""
    program = argv[0]
    in_image = launcher[:1] == ["docker"]
    if "/" in program:
        candidate = Path(program)
        if not candidate.is_absolute():
            candidate = workspace / candidate
        elif in_image:
            return
        if not candidate.is_file():
            raise _CheckBlocked(f"executable not found: {program}")
        if not os.access(candidate, os.X_OK):
            raise _CheckBlocked(f"permission denied: {program}")
        return
    if in_image:
        return
    denied = False
    for entry in env.get("PATH", os.defpath).split(os.pathsep):
        directory = Path(entry or ".")
        if not directory.is_absolute():
            directory = workspace / directory
        candidate = directory / program
        if candidate.is_file():
            if os.access(candidate, os.X_OK):
                return
            denied = True
    if denied:
        raise _CheckBlocked(f"permission denied on PATH: {program}")
    raise _CheckBlocked(f"executable not found on PATH: {program}")


def _exited_unreaped(proc: subprocess.Popen) -> bool:
    # CPython exposes os.waitid on macOS only from 3.13; earlier supported
    # versions fall back to poll(), which reaps (the group id may then be
    # reused before the final kill).
    if not (hasattr(os, "waitid") and hasattr(os, "WNOWAIT")):
        return proc.poll() is not None
    try:
        return os.waitid(os.P_PID, proc.pid,
                         os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    except ChildProcessError:
        return True


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _run_bounded(argv: list[str], *, cwd: Path, env: dict[str, str],
                 timeout: float, limit: int) -> _BoundedRun:
    """Run argv in its own process group under a whole-call deadline,
    streaming stdout and stderr into per-stream byte ceilings.

    The group is killed on timeout and again once the direct child exits, so
    no descendant outlives the check. A pipe still held open after that (a
    descendant that left the group) is reported as escaped. Residual: a
    descendant that left the group and closed its pipes is not observable
    here, so it is neither reported nor killed."""
    deadline = time.monotonic() + timeout
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    pgid = proc.pid
    streams = (proc.stdout, proc.stderr)
    buffers = (bytearray(), bytearray())
    over = [False, False]
    timed_out = escaped = False
    drain_deadline: float | None = None
    selector = selectors.DefaultSelector()
    try:
        for index, stream in enumerate(streams):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream.fileno(), selectors.EVENT_READ, index)
        while selector.get_map():
            now = time.monotonic()
            if drain_deadline is None:
                if _exited_unreaped(proc):
                    _kill_group(pgid)
                    drain_deadline = now + _PIPE_DRAIN_GRACE_SECONDS
                elif now >= deadline:
                    timed_out = True
                    _kill_group(pgid)
                    drain_deadline = now + _PIPE_DRAIN_GRACE_SECONDS
            elif now >= drain_deadline:
                escaped = not timed_out
                break
            wait_until = drain_deadline if drain_deadline is not None else deadline
            for key, _ in selector.select(min(0.1, max(0.0, wait_until - now))):
                try:
                    chunk = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fd)
                    continue
                buffer = buffers[key.data]
                room = limit - len(buffer)
                if len(chunk) > room:
                    over[key.data] = True
                if room > 0:
                    buffer.extend(chunk[:room])
        # Both pipes closed while the child may still run: honor the deadline.
        while drain_deadline is None and not _exited_unreaped(proc):
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(0.02)
    finally:
        selector.close()
        # The leader is not reaped before this point, so its pgid cannot have
        # been reused by an unrelated process group.
        _kill_group(pgid)
        for stream in streams:
            stream.close()
        proc.wait()
    return _BoundedRun(proc.returncode, bytes(buffers[0]), bytes(buffers[1]),
                       over[0], over[1], timed_out, escaped)


def _decode_stream(data: bytes, over_limit: bool, limit: int) -> str:
    text = data.decode("utf-8", errors="replace")
    if over_limit:
        text += f"\n[output truncated at {limit} bytes]\n"
    return text


# Version of the verifier-verdict parsing contract (parse_verdict: last JSON
# verdict object wins; fail closed otherwise). Part of a proven
# brain's bundle identity: bump on ANY behavior change to the parser, because
# a scorecard earned under one parsing contract says nothing about another.
PARSER_VERSION = "3"


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
    # Resolve every check before any check runs: artifact code executed by an
    # earlier check must not be able to turn a later check into a pre-launch
    # block (cannot-verify) and so make a failing artifact unscorable.
    prepared: list[tuple[list[str], list[str], dict] | str] = []
    for check in checks:
        try:
            # Checks run agent-produced code (pytest imports the workspace), so
            # they are sandboxed exactly like run_shell and fail closed with it.
            try:
                argv = shlex.split(check.command)
            except ValueError as e:
                raise _CheckBlocked(f"malformed command: {e}") from None
            if not argv:
                raise _CheckBlocked("malformed command: empty")
            sandboxed = (sandbox_wrap(
                argv, workspace, allow_network=allow_network,
                readonly_paths=readonly_paths)
                if readonly_paths else
                sandbox_wrap(argv, workspace, allow_network=allow_network))
            env = scrubbed_env()
            _resolve_executable(argv, workspace, env, sandboxed)
            prepared.append((argv, sandboxed, env))
        except SandboxUnavailable as e:
            prepared.append(f"sandbox unavailable, check blocked (fail-closed): {e}")
        except _CheckBlocked as e:
            prepared.append(f"check could not execute: {e}")
        except OSError as e:
            prepared.append(f"check could not execute: {type(e).__name__}: {e}")

    results = []
    for check, prep in zip(checks, prepared):
        terminal = truncated = False
        if isinstance(prep, str):
            outcome, output = CHECK_BLOCKED, prep
        else:
            argv, sandboxed, env = prep
            outcome, output, truncated, terminal = _launch_check(
                check, argv, sandboxed, env, workspace, blast_radius)
        passed = outcome == CHECK_PASSED
        proofs.save(f"check-{check.name}-attempt{attempt}.txt",
                    f"$ {check.command}\npassed={passed}\noutcome={outcome}\n\n"
                    f"{output}")
        events.emit("check", name=check.name, passed=passed, attempt=attempt,
                    outcome=outcome)
        results.append(CheckResult(check.name, passed, output,
                                   terminal=terminal, outcome=outcome,
                                   truncated=truncated))
        if terminal:
            break
    return results


def _launch_check(check: Check, argv: list[str], sandboxed: list[str],
                  env: dict, workspace: Path,
                  blast_radius: PhaseBlastRadius | None
                  ) -> tuple[str, str, bool, bool]:
    from .sandbox import SandboxUnavailable
    truncated = terminal = False
    limit = CHECK_OUTPUT_LIMIT_BYTES
    try:
        def apply_check():
            return _run_bounded(sandboxed, cwd=workspace, env=env,
                                timeout=check.timeout, limit=limit)
        proc = (blast_radius.apply(f"check:{check.name}", apply_check)
                if blast_radius is not None else apply_check())
        truncated = proc.truncated
        output = (_decode_stream(proc.stdout, proc.stdout_over, limit)
                  + _decode_stream(proc.stderr, proc.stderr_over, limit))
        if proc.timed_out:
            outcome = CHECK_TIMEOUT
            output = (f"check timed out after {check.timeout}s; process "
                      f"group killed: {output}")
        elif proc.escaped:
            outcome = CHECK_RESOURCE
            output = ("check left a descendant outside its process group "
                      f"holding its output open (fail-closed): {output}")
        elif (proc.returncode == 71 and Path(sandboxed[0]).name == "sandbox-exec"
              and "sandbox_apply" in output
              and _sandbox_apply_fails(sandboxed, argv, workspace, env)):
            outcome = CHECK_BLOCKED
            output = ("sandbox unavailable, check blocked (fail-closed): "
                      f"{output.strip()}")
        else:
            outcome = CHECK_PASSED if proc.returncode == 0 else CHECK_FAILED
    except SandboxUnavailable as e:
        outcome = CHECK_BLOCKED
        output = f"sandbox unavailable, check blocked (fail-closed): {e}"
    except BlastRadiusExceeded as e:
        outcome, output = CHECK_RESOURCE, e.detail
        terminal = True
    except OSError as e:
        # The program resolved before any check ran; if it is now missing or
        # not executable, workspace code changed it, which is an observed
        # failure. Other launcher errors (EMFILE, ENOMEM) are infrastructure.
        if e.errno in (errno.ENOENT, errno.EACCES, errno.ENOEXEC,
                       errno.EISDIR, errno.ENOTDIR):
            outcome = CHECK_FAILED
            output = ("check program changed after pre-launch resolution: "
                      f"{type(e).__name__}: {e}")
        else:
            outcome = CHECK_BLOCKED
            output = f"check could not execute: {type(e).__name__}: {e}"
    return outcome, output, truncated, terminal


def _sandbox_apply_fails(sandboxed: list[str], argv: list[str],
                         workspace: Path, env: dict) -> bool:
    """Re-probe Seatbelt with the same wrapper and a trivial program. The
    checked program controls its own stderr and exit status, so a 71 with a
    sandbox_apply message is infrastructure only if the probe fails too."""
    n = len(argv)
    if n == 0 or sandboxed[-n:] != argv:
        return True
    try:
        probe = subprocess.run(sandboxed[:-n] + ["/usr/bin/true"],
                               cwd=workspace, env=env, capture_output=True,
                               timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return True
    return probe.returncode != 0


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
        if not isinstance(status, str) or status not in CLAIM_STATUSES:
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
                                     passed=result.passed, attempt=attempt,
                                     outcome=result.outcome)
                    check_results.append(result)
                failed = [c for c in check_results if not c.passed]
                if failed:
                    # Check output becomes model-visible through the retry
                    # task, so it is redacted in both boundary modes. The raw
                    # proofs/check-*.txt files stay as operator artifacts.
                    detail = "\n".join(f"[{c.name}] {_redacted(c.output, 800)}"
                                       for c in failed)
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
                f"{_redacted(verdict.reasons, 3000)}\n\n"
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

        last = _redacted(verdicts[-1].reasons, 800) if verdicts else "(no verdicts)"
        return GateResult("needs_human", len(verdicts),
                          "verification failed after escalation ladder; "
                          f"operator review required. Last verdict: {last}",
                          verdicts)
