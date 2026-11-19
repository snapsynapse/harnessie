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
  - Allowlisted interpreters and test runners receive an ownership-derived
    read-only overlay at the OS sandbox. Operator lanes, other-agent lanes,
    and other agents' first-writer claims stay protected even when a write
    target is hidden inside code executed by the child process.
  - Direct writes replace only the authorized directory entry: anchored
    no-follow traversal, an exclusive same-directory temp file, then an
    atomic rename. A hardlink alias never mutates another name's inode, and
    an existing file the agent cannot write is refused, not replaced.
  - File reads and child output stream under byte ceilings with an overflow
    sentinel; run_shell has a whole-call deadline and kills its process group.
  - task_complete is how a loop ends deliberately. Requiring an explicit final
    report beats inferring completion from silence.
"""

from __future__ import annotations

import codecs
import errno
import os
import re
import secrets as _secrets
import selectors
import shlex
import signal
import stat
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..blast_radius import BlastRadiusExceeded, PhaseBlastRadius
from ..events import EventLog
from ..memory import FACT_TYPES, ProjectMemory
from ..ownership import IsolatedOwnershipView, OwnershipLedger
from ..quarantine import find_secrets, redact_secrets
from ..sandbox import SandboxUnavailable, wrap as sandbox_wrap
from .registry import Refusal, ToolRefusal, ToolRegistry, ToolSpec
from ..ids import generate


def scrubbed_env() -> dict[str, str]:
    """Minimal environment for child processes. Parent env carries API keys;
    an injected 'print os.environ' in worker code must find nothing worth
    stealing. Applied to run_shell here and to gate checks in verify.py."""
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    # Verification must not inherit operator-wide Git behavior such as commit
    # signing, hooks paths, aliases, or credential helpers. Repository-local
    # configuration remains visible, while global and system configuration are
    # removed deterministically on every supported platform.
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env

# Byte ceilings and the whole-call deadline. Output is streamed under these
# limits; nothing reads a file or a child pipe wholly before truncating.
READ_FILE_MAX_BYTES = 100_000
SHELL_STREAM_MAX_BYTES = 20_000          # per stream: stdout and stderr each
SHELL_OUTPUT_MAX_CHARS = 20_000          # combined observation
SHELL_DEADLINE_S = 300.0                 # whole call, not per read
SHELL_DRAIN_GRACE_S = 1.0                # after the direct child exits
_READ_CHUNK = 64 * 1024

# Direct writes replace only the authorized directory entry. New files and
# detached hardlink aliases get WRITE_FILE_MODE minus the process umask; an
# existing singly linked regular file keeps its permission bits (never
# setuid, setgid or sticky). An existing file without write permission is
# refused, never replaced.
WRITE_FILE_MODE = 0o666
WRITE_DIR_MODE = 0o755
_WRITE_TMP_PREFIX = ".harnessie-write-"
_DIR_FLAGS = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
              | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))


def _overflow_sentinel(source: str, limit: int, stream: str = "") -> str:
    where = f" stream={stream}" if stream else ""
    return f"\n[harnessie:truncated source={source}{where} limit_bytes={limit}]"


def _decode_prefix(data: bytes, complete: bool) -> str:
    """UTF-8 decode; a cut stream drops its trailing partial sequence."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    return decoder.decode(data, final=complete)


def _safe_truncated_prefix(text: str) -> str:
    """Withhold an unfinished final token when its remaining bytes are unknown.

    A byte or character ceiling can split a credential before it satisfies a
    full-secret pattern. Removing the entire trailing non-whitespace token is
    conservative, but keeps an unmatched credential prefix out of the next
    model turn and event log. Complete tokens before the cut remain visible.
    """
    match = re.search(r"\S+$", text)
    return text[:match.start()] if match else text


def _path_changed(rel: str, op: str) -> ToolRefusal:
    return ToolRefusal(
        f"{op}_target_changed", "jail",
        f"Path {rel!r} changed between authorization and {op}; nothing was "
        f"{'written' if op == 'write' else 'read'}.",
        "Filesystem tools act only on the directory entry that was "
        "authorized; a symlink swapped in afterwards is refused.")


def _is_symlink(name: str, dir_fd: int) -> bool:
    try:
        return stat.S_ISLNK(os.stat(name, dir_fd=dir_fd,
                                    follow_symlinks=False).st_mode)
    except OSError:
        return False


def _anchored_dir(ws: Path, parts: list[str], rel: str, op: str,
                  create: bool) -> int:
    """Open the parent directory of rel from the workspace root one
    component at a time, never following a symlink. Returns an fd."""
    if not {os.open, os.stat, os.rename, os.mkdir, os.access} <= os.supports_dir_fd \
            or not getattr(os, "O_NOFOLLOW", 0):
        raise ToolRefusal(
            f"{op}_unsupported_platform", "jail",
            "This platform cannot anchor filesystem access to the workspace.",
            "Direct file access fails closed where traversal cannot be anchored.")
    fd = os.open(ws, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                 | getattr(os, "O_CLOEXEC", 0))
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, WRITE_DIR_MODE, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                child = os.open(part, _DIR_FLAGS, dir_fd=fd)
            except OSError as e:
                # A symlink now sits where a directory was authorized (ELOOP,
                # or ENOTDIR where O_DIRECTORY is checked first), or the
                # directory vanished after our own mkdir.
                if e.errno == errno.ELOOP or (create and e.errno == errno.ENOENT):
                    raise _path_changed(rel, op) from e
                if e.errno == errno.ENOTDIR and _is_symlink(part, fd):
                    raise _path_changed(rel, op) from e
                raise
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _replace_entry(ws: Path, rel: str, data: bytes) -> int:
    """Write data to a same-directory exclusive temp file, then atomically
    rename it over rel's directory entry. The previous inode (a hardlink
    alias, possibly shared with a protected name) is never opened for
    writing. Returns the replaced entry's link count (0 when new)."""
    *parents, name = rel.split("/")
    dfd = _anchored_dir(ws, parents, rel, "write", create=True)
    try:
        try:
            st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
        except FileNotFoundError:
            st = None
        if st is not None and stat.S_ISLNK(st.st_mode):
            raise _path_changed(rel, "write")
        if st is not None and not stat.S_ISREG(st.st_mode):
            raise _unsupported_target(rel)
        if st is not None and not os.access(
                name, os.W_OK, dir_fd=dfd,
                follow_symlinks=os.access not in os.supports_follow_symlinks):
            # Replacing the entry needs only directory write permission;
            # refuse anyway, as an in-place open for writing would have.
            raise ToolRefusal(
                "write_target_readonly", "permissions",
                f"Path {rel!r} exists and is not writable; nothing was written.",
                "write_file never replaces a file the agent could not open "
                "for writing.")
        # An existing singly linked file keeps its permission bits; a new file
        # or detached alias takes WRITE_FILE_MODE minus the process umask,
        # applied by the kernel at creation (never os.umask, which races).
        keep = (stat.S_IMODE(st.st_mode) & 0o777
                if st is not None and st.st_nlink == 1 else None)
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                 | getattr(os, "O_CLOEXEC", 0))
        while True:
            tmp = _WRITE_TMP_PREFIX + _secrets.token_hex(8)
            try:
                tfd = os.open(tmp, flags,
                              0o600 if keep is not None else WRITE_FILE_MODE,
                              dir_fd=dfd)
                break
            except FileExistsError:
                continue
        try:
            with os.fdopen(tfd, "wb") as fh:
                fh.write(data)
                if keep is not None:
                    os.fchmod(fh.fileno(), keep)
            try:
                os.rename(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
            except (IsADirectoryError, NotADirectoryError) as e:
                raise _unsupported_target(rel) from e
        except BaseException:
            try:
                os.unlink(tmp, dir_fd=dfd)
            except FileNotFoundError:
                pass
            raise
        return st.st_nlink if st is not None else 0
    finally:
        os.close(dfd)


def _unsupported_target(rel: str) -> ToolRefusal:
    return ToolRefusal(
        "write_target_unsupported", "jail",
        f"Path {rel!r} is not a regular file.",
        "write_file replaces regular files only.")


def _read_entry(ws: Path, rel: str, limit: int) -> tuple[bytes, bool]:
    """Read at most limit bytes of rel's regular file through an anchored,
    no-follow, non-blocking open. Returns (data, truncated)."""
    *parents, name = rel.split("/")
    dfd = _anchored_dir(ws, parents, rel, "read", create=False)
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                         | getattr(os, "O_CLOEXEC", 0), dir_fd=dfd)
        except OSError as e:
            if e.errno == errno.ELOOP:
                raise _path_changed(rel, "read") from e
            raise
    finally:
        os.close(dfd)
    with os.fdopen(fd, "rb") as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            raise ToolRefusal(
                "read_target_unsupported", "jail",
                f"Path {rel!r} is not a regular file.",
                "read_file reads regular files only; devices, pipes and "
                "directories could block or stream without end.")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            chunk = fh.read(min(_READ_CHUNK, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    data = b"".join(chunks)
    return data[:limit], len(data) > limit


@dataclass
class _ShellOutcome:
    returncode: int | None
    stdout: bytes = b""
    stderr: bytes = b""
    overflow: dict[str, bool] = field(default_factory=dict)
    timed_out: bool = False
    # A descendant outside the killed process group (setsid) still held the
    # output pipes when the drain grace ran out. One that closed its pipes
    # first is not observable here and is not reported.
    escaped: bool = False


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _leader_exited(proc: subprocess.Popen) -> bool:
    # WNOWAIT leaves the exited child unreaped, so its pid (the process
    # group id) cannot be recycled before the group is killed.
    if hasattr(os, "waitid") and hasattr(os, "WNOWAIT"):
        try:
            return os.waitid(os.P_PID, proc.pid,
                             os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        except ChildProcessError:
            return True
    return proc.poll() is not None


def _run_bounded(argv: list[str], cwd: Path, env: dict[str, str]) -> _ShellOutcome:
    """Run argv in its own process group with both pipes streamed under
    SHELL_STREAM_MAX_BYTES and the whole call under SHELL_DEADLINE_S. When
    the direct child exits, any group member still holding the pipes is
    killed and draining stops after SHELL_DRAIN_GRACE_S."""
    limit = SHELL_STREAM_MAX_BYTES
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    out = _ShellOutcome(returncode=None,
                        overflow={"stdout": False, "stderr": False})
    bufs = {"stdout": bytearray(), "stderr": bytearray()}
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
    sel.register(proc.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + SHELL_DEADLINE_S
    exited_at: float | None = None
    try:
        while True:
            now = time.monotonic()
            if now >= deadline:
                out.timed_out = True
                break
            if exited_at is None and _leader_exited(proc):
                exited_at = now
                _kill_group(proc.pid)
            if exited_at is not None and (
                    not sel.get_map() or now - exited_at >= SHELL_DRAIN_GRACE_S):
                out.escaped = bool(sel.get_map())
                break
            wait = min(deadline - now, 0.05)
            if not sel.get_map():
                time.sleep(wait)
                continue
            for key, _ in sel.select(wait):
                chunk = os.read(key.fd, _READ_CHUNK)
                if not chunk:
                    sel.unregister(key.fileobj)
                    continue
                buf = bufs[key.data]
                room = limit - len(buf)
                if room > 0:
                    buf += chunk[:room]
                if len(chunk) > room:
                    out.overflow[key.data] = True
    finally:
        _kill_group(proc.pid)
        sel.close()
        proc.stdout.close()
        proc.stderr.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    out.returncode = proc.returncode
    out.stdout, out.stderr = bytes(bufs["stdout"]), bytes(bufs["stderr"])
    return out


READ_ROLES = frozenset({"orchestrator", "worker", "verifier"})
WRITE_ROLES = frozenset({"worker"})

DEFAULT_SHELL_ALLOWLISTS: dict[str, tuple[str, ...]] = {
    "worker": ("ls", "cat", "grep", "python3", "pytest", "git"),
    "verifier": ("ls", "cat", "grep", "pytest"),   # no interpreters, no git
}


def _jail(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ToolRefusal(
            "workspace_jail_escape", "jail",
            f"Path {rel!r} escapes the workspace. Use a relative path inside the project.",
            "The workspace jail prevents tools from reading or writing outside their scope.")
    return p


def register_builtin(reg: ToolRegistry, workspace: Path,
                     shell_allowlists: dict[str, tuple[str, ...]] | None = None,
                     ledger: OwnershipLedger | IsolatedOwnershipView | None = None,
                     events: EventLog | None = None,
                     memory: ProjectMemory | None = None,
                     provenance: str = "",
                     blast_radius: PhaseBlastRadius | None = None) -> None:
    ws = workspace.resolve()
    allowlists = shell_allowlists or DEFAULT_SHELL_ALLOWLISTS
    if ledger is not None:
        reg.readonly_paths_for = lambda agent: ledger.confinement_roots(agent, ws)

    def _emit(kind: str, **data) -> None:
        if events is not None:
            events.emit(kind, **data)

    def read_file(path: str) -> str:
        target = _jail(ws, path)
        limit = READ_FILE_MAX_BYTES
        data, truncated = _read_entry(ws, target.relative_to(ws).as_posix(), limit)
        text = _decode_prefix(data, complete=not truncated)
        if truncated:
            text = _safe_truncated_prefix(text)
        return text + (_overflow_sentinel("read_file", limit) if truncated else "")

    def write_file(path: str, content: str, _role: str = "worker",
                   _agent: str = "", _allow_network: bool = False) -> str:
        secrets = find_secrets(content)
        if secrets:
            # Exfil guard: a prompt-injected worker copying credentials into
            # the workspace is blocked at the tool layer, fail closed.
            raise ToolRefusal(
                "secret_write_refused", "secrets",
                "Content contains credential-shaped strings "
                f"(kinds: {', '.join(secrets[:3])}). Remove them and retry.",
                "Secrets must not be copied into workspace artifacts.")
        target = _jail(ws, path)
        rel = target.relative_to(ws).as_posix()
        if ledger is not None:
            allowed, reason = ledger.check_write(_agent or _role, rel)
            if not allowed:
                _emit("ownership_denied", agent=_agent or _role, path=rel,
                      reason=reason[:200])
                error = ("operator_lane_denied" if "operator-owned lane" in reason
                         else "ownership_denied")
                raise ToolRefusal(
                    error, "ownership",
                    reason,
                    "Ownership lanes keep agents from mutating files outside their authority.")
        data = content.encode("utf-8")

        def apply_write() -> int:
            return _replace_entry(ws, rel, data)
        try:
            meter = blast_radius or reg.blast_radius
            links = (meter.apply("write_file", apply_write)
                     if meter is not None else apply_write())
        except BlastRadiusExceeded as e:
            raise ToolRefusal(
                "blast_radius_exceeded", "blast_radius", e.detail,
                "Artifact-volume ceilings stop a phase before workspace damage "
                "can exceed the operator's declared bound.") from e
        if links > 1:
            # The written name was a hardlink alias; it now has its own inode
            # and every other name keeps the previous content.
            _emit("hardlink_detached", agent=_agent or _role, path=rel,
                  links=links)
        if ledger is not None and ledger.claim(_agent or _role, rel):
            _emit(getattr(ledger, "claim_event", "ownership_claimed"),
                  agent=_agent or _role, path=rel)
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
            return Refusal(
                "command_not_allowlisted", "allowlist",
                f"Command {argv[0] if argv else ''!r} is not in the allowlist "
                f"for role {_role!r}: {sorted(allow)}.",
                "Shell access is allowlist-first so prompts cannot expand execution authority.")
        for tok in argv[1:]:
            if tok.startswith("/") or tok == ".." or tok.startswith("../") or "/../" in tok:
                return Refusal(
                    "argument_jail_escape", "jail",
                    f"Argument {tok!r} was rejected. Paths must stay inside the workspace.",
                    "The argument jail blocks simple path escapes before process launch.")
        try:
            readonly_paths = reg.readonly_paths_for(_agent or _role)
            sandboxed = (sandbox_wrap(
                argv, ws, allow_network=_allow_network,
                readonly_paths=readonly_paths)
                if readonly_paths else
                sandbox_wrap(argv, ws, allow_network=_allow_network))
        except (SandboxUnavailable, ValueError) as e:
            _emit("lane_confinement_refused", agent=_agent or _role,
                  detail=str(e)[:500])
            return Refusal(
                "sandbox_unavailable", "sandbox",
                f"Sandbox unavailable; shell blocked fail-closed: {e}",
                "Shell commands require OS confinement before execution.")
        def apply_shell() -> _ShellOutcome:
            return _run_bounded(sandboxed, ws, scrubbed_env())
        try:
            meter = blast_radius or reg.blast_radius
            proc = (meter.apply("run_shell", apply_shell)
                    if meter is not None else apply_shell())
        except BlastRadiusExceeded as e:
            raise ToolRefusal(
                "blast_radius_exceeded", "blast_radius", e.detail,
                "Artifact-volume ceilings stop a phase before workspace damage "
                "can exceed the operator's declared bound.") from e
        except OSError as e:
            if e.errno not in (errno.ENOENT, errno.EACCES, errno.ENOEXEC):
                raise
            return Refusal(
                "command_unavailable", "environment",
                f"Command {argv[0]!r} is allowlisted but could not be started "
                f"({errno.errorcode.get(e.errno, e.errno)}).",
                "An allowlisted command must exist and be executable; a missing "
                "tool is an environment fault, not a failed command.")
        if proc.timed_out:
            return Refusal(
                "shell_deadline_exceeded", "deadline",
                f"Command exceeded the {SHELL_DEADLINE_S:g}s whole-call deadline; "
                "its process group was killed.",
                "Shell calls run under a whole-call deadline so slow or endless "
                "output cannot monopolize a run.")
        streams = []
        for stream, data in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            text = _decode_prefix(data, not proc.overflow[stream])
            streams.append(_safe_truncated_prefix(text)
                           if proc.overflow[stream] else text)
        combined = "".join(streams)
        redacted, n_redacted = redact_secrets(combined)
        out = redacted[:SHELL_OUTPUT_MAX_CHARS]
        if len(redacted) > SHELL_OUTPUT_MAX_CHARS:
            out = _safe_truncated_prefix(out)
        for stream in ("stdout", "stderr"):
            if proc.overflow[stream]:
                out += _overflow_sentinel("run_shell", SHELL_STREAM_MAX_BYTES,
                                          stream)
        if len(combined) > SHELL_OUTPUT_MAX_CHARS:
            out += _overflow_sentinel("run_shell", SHELL_OUTPUT_MAX_CHARS)
        if proc.returncode == 71 and "sandbox_apply" in out:
            return Refusal(
                "sandbox_unavailable", "sandbox",
                f"Sandbox unavailable; shell blocked fail-closed: {out.strip()}",
                "Shell commands require a sandbox profile that can actually apply.")
        suffix = f"\n[{n_redacted} credential-shaped string(s) redacted]" if n_redacted else ""
        if proc.escaped:
            # Informational only: the exit status stays the direct child's.
            _emit("shell_escaped_descendant", agent=_agent or _role,
                  command=argv[0])
            suffix += "\n[harnessie:escaped_descendant held_output_open=true]"
        return f"exit={proc.returncode}\n{out}{suffix}"

    def task_complete(report: str) -> str:
        return report

    def accept_task(note: str = "") -> str:
        # Normally intercepted by the loop; this body answers a direct call.
        return "consent recorded" + (f": {note}" if note else "")

    def decline_task(reason: str, counter_proposal: str = "") -> str:
        return f"declined: {reason}"

    def save_fact(title: str, body: str, fact_type: str = "lesson",
                  source: str = "", verify_by: str = "",
                  _role: str = "worker", _agent: str = "",
                  _allow_network: bool = False) -> str:
        if memory is None:
            return "no project memory configured for this run"
        if fact_type not in FACT_TYPES:
            return f"fact_type must be one of {FACT_TYPES}"
        # Provenance is STAMPED by the harness, never claimed by the agent:
        # a fact's source must be auditable back to the run and agent that
        # wrote it (any agent-supplied source is ignored by design).
        stamped = f"{provenance or 'run unknown'}, agent {_agent or _role}"
        path = memory.save_fact(title, body, fact_type=fact_type,
                                source=stamped, verify_by=verify_by or None)
        _emit("fact_saved", agent=_agent or _role, slug=path.stem,
              fact_type=fact_type)
        return f"saved fact {path.stem!r} (source stamped: {stamped})"

    def expire_fact(slug: str, reason: str, _role: str = "worker",
                    _agent: str = "", _allow_network: bool = False) -> str:
        if memory is None:
            return "no project memory configured for this run"
        # Archival-only: the fact moves to memory/archive/ with a stamp.
        # Deletion does not exist as a capability. This tool additionally
        # requires approval (registry-enforced), so a headless run without a
        # recorded grant proposes instead of disposing.
        dest = memory.archive_fact(slug, reason=reason)
        _emit("fact_expired", agent=_agent or _role, slug=slug,
              reason=reason[:200])
        return f"archived fact {slug!r} to {dest.name} (never deleted)"

    def request_change(path: str, description: str, _role: str = "worker",
                       _agent: str = "", _allow_network: bool = False) -> str:
        # Records intent; grants nothing. Resolution is routing work to the
        # owning agent or an operator lane edit — decisions above the
        # requesting agent's authority.
        owner = ledger.owner_of(path) if ledger is not None else None
        ref = "CR-" + generate(5, check_digit=True)
        _emit("change_request", agent=_agent or _role, path=path,
              owner=owner, description=description[:500], ref=ref)
        return (f"change request {ref} recorded for {path!r} "
                f"(owner: {owner or 'unknown'}). "
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
        name="save_fact",
        description=("Save one durable project-memory fact (one lesson, decision, "
                     "constraint, or reference per fact). Provenance (run + agent) is "
                     "stamped by the harness. verify_by (YYYY-MM-DD) sets when the fact "
                     "goes stale; default is 30 days out."),
        parameters={"type": "object",
                    "properties": {"title": {"type": "string"},
                                   "body": {"type": "string"},
                                   "fact_type": {"type": "string",
                                                 "enum": list(FACT_TYPES)},
                                   "verify_by": {"type": "string"}},
                    "required": ["title", "body"]},
        fn=save_fact, effects="write", role_aware=True,
        allowed_roles=WRITE_ROLES))
    reg.register(ToolSpec(
        name="expire_fact",
        description=("Archive a stale project-memory fact (moves it to memory/archive/; "
                     "nothing is ever deleted). Requires operator approval: without a "
                     "recorded grant this call is refused and stands as a proposal."),
        parameters={"type": "object",
                    "properties": {"slug": {"type": "string"},
                                   "reason": {"type": "string"}},
                    "required": ["slug", "reason"]},
        fn=expire_fact, effects="write", role_aware=True,
        requires_approval=True,
        allowed_roles=WRITE_ROLES))
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
