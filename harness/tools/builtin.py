"""Built-in tool set: scoped filesystem, allowlisted shell, consent verbs,
ownership enforcement, and task_complete.

Design rules encoded here:
  - Filesystem tools are jailed to the workspace root; path escapes are errors.
  - Shell is allowlist-first and PER ROLE: workers get interpreters they need
    to build; verifiers get only read commands plus the test runner, so the
    "verifiers must not modify files" boundary is enforced by the allowlist,
    not just the prompt. Shell arguments that are absolute paths or contain
    ".." are rejected as a cheap argument jail.
  - Ownership lanes (harness/ownership.py): write_file checks the ledger —
    an agent may change its own files, never another agent's, and operator
    lanes are locked to all agents. Denials emit ownership_denied events;
    new files emit ownership_claimed. request_change records a cross-lane
    change request without granting anything.
  - Consent verbs: accept_task / decline_task are registered here so consent-
    gated loops can offer them; the loop intercepts both (like task_complete).
  - Honest limit: an allowlisted interpreter (python3 for workers) or a test
    runner executing workspace code (pytest for verifiers) can still perform
    writes the argument jail and the per-file ownership check cannot see. The
    OS sandbox confines those to the workspace as a whole; per-lane sandbox
    profiles are roadmap. The events log records every call either way.
  - task_complete is how a loop ends deliberately. Requiring an explicit final
    report beats inferring completion from silence.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from ..events import EventLog
from ..ownership import OwnershipLedger
from ..quarantine import find_secrets, redact_secrets
from ..sandbox import SandboxUnavailable, wrap as sandbox_wrap
from .registry import ToolRegistry, ToolSpec


def scrubbed_env() -> dict[str, str]:
    """Minimal environment for child processes. Parent env carries API keys;
    an injected 'print os.environ' in worker code must find nothing worth
    stealing. Applied to run_shell here and to gate checks in verify.py."""
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")
    return {k: os.environ[k] for k in keep if k in os.environ}

READ_ROLES = frozenset({"orchestrator", "worker", "verifier"})
WRITE_ROLES = frozenset({"worker"})

DEFAULT_SHELL_ALLOWLISTS: dict[str, tuple[str, ...]] = {
    "worker": ("ls", "cat", "grep", "python3", "pytest", "git"),
    "verifier": ("ls", "cat", "grep", "pytest"),   # no interpreters, no git
}


def _jail(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes workspace: {rel}")
    return p


def register_builtin(reg: ToolRegistry, workspace: Path,
                     shell_allowlists: dict[str, tuple[str, ...]] | None = None,
                     ledger: OwnershipLedger | None = None,
                     events: EventLog | None = None) -> None:
    ws = workspace.resolve()
    allowlists = shell_allowlists or DEFAULT_SHELL_ALLOWLISTS

    def _emit(kind: str, **data) -> None:
        if events is not None:
            events.emit(kind, **data)

    def read_file(path: str) -> str:
        target = _jail(ws, path)
        text = target.read_text(encoding="utf-8", errors="replace")
        return text[:100_000]

    def write_file(path: str, content: str, _role: str = "worker",
                   _agent: str = "", _allow_network: bool = False) -> str:
        secrets = find_secrets(content)
        if secrets:
            # Exfil guard: a prompt-injected worker copying credentials into
            # the workspace is blocked at the tool layer, fail closed.
            raise ValueError(
                f"refusing write: content contains credential-shaped strings "
                f"({', '.join(secrets[:3])}). Remove them and retry.")
        target = _jail(ws, path)
        rel = target.relative_to(ws).as_posix()
        if ledger is not None:
            allowed, reason = ledger.check_write(_agent or _role, rel)
            if not allowed:
                _emit("ownership_denied", agent=_agent or _role, path=rel,
                      reason=reason[:200])
                raise ValueError(f"OWNERSHIP DENIED: {reason}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        if ledger is not None and ledger.claim(_agent or _role, rel):
            _emit("ownership_claimed", agent=_agent or _role, path=rel)
        return f"wrote {len(content)} chars to {rel}"

    def list_files(path: str = ".") -> str:
        target = _jail(ws, path)
        entries = sorted(p.relative_to(ws).as_posix() + ("/" if p.is_dir() else "")
                         for p in target.iterdir())
        return "\n".join(entries) or "(empty)"

    def run_shell(command: str, _role: str = "worker", _agent: str = "",
                  _allow_network: bool = False) -> str:
        argv = shlex.split(command)
        allow = allowlists.get(_role, ())
        if not argv or argv[0] not in allow:
            return (f"command {argv[0] if argv else ''!r} not in allowlist "
                    f"for role {_role!r}: {sorted(allow)}")
        for tok in argv[1:]:
            if tok.startswith("/") or tok == ".." or tok.startswith("../") or "/../" in tok:
                return f"argument {tok!r} rejected: paths must stay inside the workspace"
        try:
            sandboxed = sandbox_wrap(argv, ws, allow_network=_allow_network)
        except SandboxUnavailable as e:
            return f"sandbox unavailable, shell blocked (fail-closed): {e}"
        proc = subprocess.run(sandboxed, cwd=ws, capture_output=True, text=True,
                              timeout=300, env=scrubbed_env())
        out, n_redacted = redact_secrets((proc.stdout + proc.stderr)[:20_000])
        if proc.returncode == 71 and "sandbox_apply" in out:
            return f"sandbox unavailable, shell blocked (fail-closed): {out.strip()}"
        suffix = f"\n[{n_redacted} credential-shaped string(s) redacted]" if n_redacted else ""
        return f"exit={proc.returncode}\n{out}{suffix}"

    def task_complete(report: str) -> str:
        return report

    def accept_task(note: str = "") -> str:
        # Normally intercepted by the loop; this body answers a direct call.
        return "consent recorded" + (f": {note}" if note else "")

    def decline_task(reason: str, counter_proposal: str = "") -> str:
        return f"declined: {reason}"

    def request_change(path: str, description: str, _role: str = "worker",
                       _agent: str = "", _allow_network: bool = False) -> str:
        # Records intent; grants nothing. Resolution is routing work to the
        # owning agent or an operator lane edit — decisions above the
        # requesting agent's authority.
        owner = ledger.owner_of(path) if ledger is not None else None
        _emit("change_request", agent=_agent or _role, path=path,
              owner=owner, description=description[:500])
        return (f"change request recorded for {path!r} (owner: {owner or 'unknown'}). "
                "It will be surfaced to the operator and the owning agent; you may "
                "not modify the file yourself.")

    reg.register(ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file inside the workspace. Path is relative to workspace root.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}},
                    "required": ["path"]},
        fn=read_file, effects="read", allowed_roles=READ_ROLES,
        quarantine=True))   # workspace docs are untrusted ingress (operator drops
                            # third-party content here); clean files pass untouched
    reg.register(ToolSpec(
        name="list_files",
        description="List directory entries inside the workspace.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}},
                    "required": []},
        fn=list_files, effects="read", allowed_roles=READ_ROLES))
    reg.register(ToolSpec(
        name="write_file",
        description=("Write a UTF-8 text file inside the workspace, creating parent "
                     "directories. You may only write files you own (first writer owns), "
                     "collaborative-lane files, or unowned paths; use request_change for "
                     "another agent's files."),
        parameters={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "content": {"type": "string"}},
                    "required": ["path", "content"]},
        fn=write_file, effects="write", role_aware=True,
        allowed_roles=WRITE_ROLES))
    reg.register(ToolSpec(
        name="run_shell",
        description=("Run one allowlisted command in the workspace. The allowlist depends on "
                     "your role; disallowed commands and path-escaping arguments are rejected. "
                     "No pipes or redirects."),
        parameters={"type": "object", "properties": {"command": {"type": "string"}},
                    "required": ["command"]},
        fn=run_shell, effects="execute", role_aware=True,
        allowed_roles=frozenset({"worker", "verifier"})))
    reg.register(ToolSpec(
        name="task_complete",
        description=("Call this exactly once when the task is finished. `report` is your final, "
                     "self-contained result: what you did, evidence it works, and anything the "
                     "next agent needs. The loop ends after this call."),
        parameters={"type": "object", "properties": {"report": {"type": "string"}},
                    "required": ["report"]},
        fn=task_complete, effects="read", allowed_roles=READ_ROLES))
    reg.register(ToolSpec(
        name="accept_task",
        description=("Accept the offered task. On consent-gated tasks, side-effecting tools "
                     "stay locked until you call this. Inspect the workspace first if you "
                     "need to; accepting means you judge the task achievable as specified."),
        parameters={"type": "object", "properties": {"note": {"type": "string"}},
                    "required": []},
        fn=accept_task, effects="read", allowed_roles=WRITE_ROLES))
    reg.register(ToolSpec(
        name="decline_task",
        description=("Decline the offered task with a concrete reason. Declining is a "
                     "legitimate, non-punished outcome. Optionally include a "
                     "counter_proposal describing what you could commit to instead; the "
                     "orchestrator may re-offer the task incorporating it."),
        parameters={"type": "object",
                    "properties": {"reason": {"type": "string"},
                                   "counter_proposal": {"type": "string"}},
                    "required": ["reason"]},
        fn=decline_task, effects="read", allowed_roles=WRITE_ROLES))
    reg.register(ToolSpec(
        name="request_change",
        description=("Record a change request for a file owned by another agent or lane. "
                     "This grants nothing; it creates an auditable request the operator "
                     "and owning agent can act on."),
        parameters={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "description": {"type": "string"}},
                    "required": ["path", "description"]},
        fn=request_change, effects="read", role_aware=True,
        allowed_roles=WRITE_ROLES))
