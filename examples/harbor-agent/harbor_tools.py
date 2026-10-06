"""Harnessie tools whose effects land in a Harbor environment, not on the host.

Harnessie's registry is the enforcement point: role grants, the shell
allowlist, the path jail and the refusal grammar all apply exactly as they
do for the builtin tools. What changes is where a call lands. These tools
run `cat`, `ls` and allowlisted commands through `BaseEnvironment.exec`
and write files through `BaseEnvironment.upload_file`, so the task's
sandbox is the confinement and nothing executes on the host.

Harnessie's `AgentLoop` is synchronous and Harbor's environment is
asyncio. The loop therefore runs in a worker thread and each tool hands its
coroutine back to Harbor's event loop with `run_coroutine_threadsafe`,
which is what `SandboxBridge` does.

This module imports nothing from Harbor, so it is tested against a fake
environment on any machine; `harnessie_harbor_agent.py` adds the thin
`BaseAgent` wrapper where Harbor is installed.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from harness.quarantine import redact_secrets
from harness.tools.registry import Refusal, ToolRegistry, ToolSpec

# The builtin worker allowlist, kept identical on purpose: the point of the
# example is that the same policy applies when the sandbox is someone else's.
SHELL_ALLOWLIST: tuple[str, ...] = ("ls", "cat", "grep", "python3", "pytest", "git")
OUTPUT_CAP = 20_000
WRITE_ROLES = frozenset({"worker"})
READ_ROLES = frozenset({"worker", "verifier"})


class RemoteExecResult(Protocol):
    stdout: str | None
    stderr: str | None
    return_code: int


class RemoteEnvironment(Protocol):
    """The two `BaseEnvironment` primitives these tools need."""

    async def exec(self, command: str, cwd: str | None = None,
                   env: dict[str, str] | None = None,
                   timeout_sec: int | None = None,
                   user: str | int | None = None) -> RemoteExecResult: ...

    async def upload_file(self, source_path: Path | str, target_path: str) -> Any: ...


def jail(workdir: str, rel: str) -> str:
    """Resolve `rel` inside `workdir` (POSIX, remote). Absolute paths are
    accepted only when already inside the workdir; any `..` is refused."""
    base = PurePosixPath(workdir)
    candidate = PurePosixPath(rel) if rel else PurePosixPath(".")
    if ".." in candidate.parts:
        raise Refusal_("workspace_jail_escape", "jail",
                       f"Path {rel!r} escapes the workspace. Use a relative path "
                       "inside the task directory.",
                       "The workspace jail prevents tools from reading or writing "
                       "outside their scope.")
    target = candidate if candidate.is_absolute() else base / candidate
    if target != base and base not in target.parents:
        raise Refusal_("workspace_jail_escape", "jail",
                       f"Path {rel!r} is outside {workdir}.",
                       "The workspace jail prevents tools from reading or writing "
                       "outside their scope.")
    return str(target)


class Refusal_(Exception):
    """Carries a Refusal out of a helper; tools turn it into a return value."""

    def __init__(self, error: str, boundary: str, detail: str, why: str) -> None:
        super().__init__(detail)
        self.refusal = Refusal(error, boundary, detail, why)


@dataclass
class SandboxBridge:
    """Calls into an asyncio environment from Harnessie's synchronous loop."""

    environment: RemoteEnvironment
    loop: asyncio.AbstractEventLoop
    workdir: str = "/app"
    timeout_sec: int = 300
    calls: list[str] = field(default_factory=list)

    def _await(self, coro: Any, timeout: float) -> Any:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout)

    def exec(self, command: str) -> RemoteExecResult:
        self.calls.append(command)
        return self._await(
            self.environment.exec(command=command, cwd=self.workdir,
                                  timeout_sec=self.timeout_sec),
            self.timeout_sec + 30)

    def upload(self, local: Path, target: str) -> None:
        self._await(self.environment.upload_file(local, target), self.timeout_sec)


def _render(result: RemoteExecResult) -> str:
    out = (result.stdout or "") + (result.stderr or "")
    text, n_redacted = redact_secrets(out[:OUTPUT_CAP])
    suffix = f"\n[{n_redacted} credential-shaped string(s) redacted]" if n_redacted else ""
    return f"exit={result.return_code}\n{text}{suffix}"


def register_remote_tools(reg: ToolRegistry, bridge: SandboxBridge,
                          allowlist: tuple[str, ...] = SHELL_ALLOWLIST) -> None:
    workdir = bridge.workdir

    def read_file(path: str) -> str:
        try:
            target = jail(workdir, path)
        except Refusal_ as exc:
            return exc.refusal
        return _render(bridge.exec(f"cat -- {shlex.quote(target)}"))

    def list_files(path: str = ".") -> str:
        try:
            target = jail(workdir, path)
        except Refusal_ as exc:
            return exc.refusal
        return _render(bridge.exec(f"ls -1Ap -- {shlex.quote(target)}"))

    def write_file(path: str, content: str, _role: str = "worker",
                   _agent: str = "", _allow_network: bool = False) -> str:
        try:
            target = jail(workdir, path)
        except Refusal_ as exc:
            return exc.refusal
        parent = str(PurePosixPath(target).parent)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                         prefix="harnessie-upload-") as handle:
            handle.write(content)
            local = Path(handle.name)
        try:
            bridge.exec(f"mkdir -p -- {shlex.quote(parent)}")
            bridge.upload(local, target)
        finally:
            local.unlink(missing_ok=True)
        return f"wrote {target} ({len(content.encode('utf-8'))} bytes)"

    def run_shell(command: str, _role: str = "worker", _agent: str = "",
                  _allow_network: bool = False) -> str:
        argv = shlex.split(command)
        if not argv or argv[0] not in allowlist:
            return Refusal(
                "command_not_allowlisted", "allowlist",
                f"Command {argv[0] if argv else ''!r} is not in the allowlist "
                f"for role {_role!r}: {sorted(allowlist)}.",
                "Shell access is allowlist-first so prompts cannot expand "
                "execution authority.")
        for tok in argv[1:]:
            if tok.startswith("/") or tok == ".." or tok.startswith("../") or "/../" in tok:
                return Refusal(
                    "argument_jail_escape", "jail",
                    f"Argument {tok!r} was rejected. Paths must stay inside the workspace.",
                    "The argument jail blocks simple path escapes before process launch.")
        return _render(bridge.exec(shlex.join(argv)))

    def task_complete(report: str) -> str:
        return report

    schema = lambda props, required: {  # noqa: E731
        "type": "object", "properties": props, "required": required}

    reg.register(ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file inside the task workspace. Path is "
                    "relative to the workspace root.",
        parameters=schema({"path": {"type": "string"}}, ["path"]),
        fn=read_file, effects="read", allowed_roles=READ_ROLES, quarantine=True))
    reg.register(ToolSpec(
        name="list_files",
        description="List directory entries inside the task workspace.",
        parameters=schema({"path": {"type": "string"}}, []),
        fn=list_files, effects="read", allowed_roles=READ_ROLES))
    reg.register(ToolSpec(
        name="write_file",
        description="Write a UTF-8 text file inside the task workspace, creating "
                    "parent directories.",
        parameters=schema({"path": {"type": "string"}, "content": {"type": "string"}},
                          ["path", "content"]),
        fn=write_file, effects="write", role_aware=True, allowed_roles=WRITE_ROLES))
    reg.register(ToolSpec(
        name="run_shell",
        description="Run one allowlisted command in the task workspace. Disallowed "
                    "commands and path-escaping arguments are rejected. No pipes "
                    "or redirects.",
        parameters=schema({"command": {"type": "string"}}, ["command"]),
        fn=run_shell, effects="execute", role_aware=True,
        allowed_roles=frozenset({"worker", "verifier"})))
    reg.register(ToolSpec(
        name="task_complete",
        description="Call this exactly once when the task is finished. `report` is "
                    "your final, self-contained result: what you did and the "
                    "evidence it works. The loop ends after this call.",
        parameters=schema({"report": {"type": "string"}}, ["report"]),
        fn=task_complete, effects="read", allowed_roles=READ_ROLES))


class CancellableModel:
    """Wrap a model so an external cancel (Harbor's agent timeout) becomes a
    recorded Harnessie stop condition instead of an orphaned thread.

    `AgentLoop` has no cancellation hook, but it treats two consecutive error
    turns as `model_error` and finishes through `loop_finished`, which is what
    the audit log and the ATIF export need. Once the flag is set, every call
    returns an error turn without touching the endpoint."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.spec = inner.spec
        self.cancelled = False
        self._flag = __import__("threading").Event()

    def cancel(self) -> None:
        self.cancelled = True
        self._flag.set()

    def complete(self, messages: Any, tools: Any = None, effort: str = "medium") -> Any:
        from harness.models.base import AssistantTurn
        if self._flag.is_set():
            return AssistantTurn(content="harness_cancelled: the host stopped this agent",
                                 stop_reason="error")
        turn = self.inner.complete(messages, tools=tools, effort=effort)
        if self._flag.is_set():
            # The call that was in flight when the host cancelled still
            # counts for tokens, but the loop must not act on it.
            return AssistantTurn(content="harness_cancelled: the host stopped this agent",
                                 stop_reason="error",
                                 input_tokens=turn.input_tokens,
                                 output_tokens=turn.output_tokens)
        return turn


def resolve_endpoint(base_url: str | None = None, api_key_env: str | None = None,
                     env: dict[str, str] | None = None) -> tuple[str, str]:
    """Where the model is and which environment variable holds the key.

    Explicit arguments win. Otherwise `HARNESSIE_HARBOR_BASE_URL` and
    `HARNESSIE_HARBOR_API_KEY`, then the OpenAI-style pair a generic seam
    would set. The key's value is never read here; Harnessie's adapter reads
    the named variable at call time."""
    env = os.environ if env is None else env
    url = base_url or env.get("HARNESSIE_HARBOR_BASE_URL") or env.get("OPENAI_BASE_URL") or ""
    if api_key_env:
        key_env = api_key_env
    elif env.get("HARNESSIE_HARBOR_API_KEY"):
        key_env = "HARNESSIE_HARBOR_API_KEY"
    elif env.get("OPENAI_API_KEY"):
        key_env = "OPENAI_API_KEY"
    else:
        key_env = ""
    if not url:
        raise ValueError(
            "no model endpoint: pass base_url or set HARNESSIE_HARBOR_BASE_URL "
            "(or OPENAI_BASE_URL)")
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    return url, key_env


__all__ = [
    "SHELL_ALLOWLIST",
    "CancellableModel",
    "SandboxBridge",
    "jail",
    "register_remote_tools",
    "resolve_endpoint",
]
