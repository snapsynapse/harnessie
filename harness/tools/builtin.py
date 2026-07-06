"""Built-in tool set: scoped filesystem, allowlisted shell, and task_complete.

Design rules encoded here:
  - Filesystem tools are jailed to the workspace root; path escapes are errors.
  - Shell is allowlist-first and PER ROLE: workers get interpreters they need
    to build; verifiers get only read commands plus the test runner, so the
    "verifiers must not modify files" boundary is enforced by the allowlist,
    not just the prompt. Shell arguments that are absolute paths or contain
    ".." are rejected as a cheap argument jail.
  - Honest limit: an allowlisted interpreter (python3 for workers) or a test
    runner executing workspace code (pytest for verifiers) can still perform
    writes the argument jail cannot see. Full containment needs an OS sandbox
    (implementation plan, Phase 2); until then the allowlist narrows the hole
    and the journal records every call.
  - task_complete is how a loop ends deliberately. Requiring an explicit final
    report beats inferring completion from silence.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

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
                     shell_allowlists: dict[str, tuple[str, ...]] | None = None) -> None:
    ws = workspace.resolve()
    allowlists = shell_allowlists or DEFAULT_SHELL_ALLOWLISTS

    def read_file(path: str) -> str:
        target = _jail(ws, path)
        text = target.read_text(encoding="utf-8", errors="replace")
        return text[:100_000]

    def write_file(path: str, content: str) -> str:
        secrets = find_secrets(content)
        if secrets:
            # Exfil guard: a prompt-injected worker copying credentials into
            # the workspace is blocked at the tool layer, fail closed.
            raise ValueError(
                f"refusing write: content contains credential-shaped strings "
                f"({', '.join(secrets[:3])}). Remove them and retry.")
        target = _jail(ws, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {target.relative_to(ws)}"

    def list_files(path: str = ".") -> str:
        target = _jail(ws, path)
        entries = sorted(p.relative_to(ws).as_posix() + ("/" if p.is_dir() else "")
                         for p in target.iterdir())
        return "\n".join(entries) or "(empty)"

    def run_shell(command: str, _role: str = "worker",
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
        suffix = f"\n[{n_redacted} credential-shaped string(s) redacted]" if n_redacted else ""
        return f"exit={proc.returncode}\n{out}{suffix}"

    def task_complete(report: str) -> str:
        return report

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
        description="Write a UTF-8 text file inside the workspace, creating parent directories.",
        parameters={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "content": {"type": "string"}},
                    "required": ["path", "content"]},
        fn=write_file, effects="write", allowed_roles=WRITE_ROLES))
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
