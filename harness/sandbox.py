"""OS-level sandbox for child-process execution.

Closes the gap the allowlist and argument jail only narrow: an allowlisted
interpreter (worker python3, verifier pytest) can still write outside the
workspace and open network sockets, which the string-level jail cannot see.
This module wraps every child command in an OS confinement that denies both.

Policy (operator-chosen, 2026-07-06):
  - Fail closed everywhere: no OS sandbox backend on this platform means shell
    and gate checks are BLOCKED, never run unsandboxed. Wire a backend to
    enable shell on a new platform.
  - Deny network by default; a workflow phase opts in with allow_network: true.
  - Confine writes to the workspace, then overlay ownership paths denied to
    the active agent as read-only. Temp dirs outside home stay writable so
    interpreters function; that is a deliberate boundary (the protected asset
    is the user's files and the exfil channel, not scratch space).

Backends: macOS Seatbelt via `sandbox-exec -p <profile>` (native, no deps);
on Linux, in order of preference, bubblewrap (rootless, no daemon), firejail,
then docker as a heavyweight fallback. Every backend is admitted only after a
startup smoke test proves it can actually confine; a present-but-unusable
backend is treated exactly like a missing one. Nonempty lane overlays require
a second nested-read-only probe and fail closed independently.
"""

from __future__ import annotations

import os
import platform
import json
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

# Overridable because image choice is deployment policy, not harness policy.
DEFAULT_DOCKER_IMAGE = "python:3.12-slim"


class SandboxUnavailable(Exception):
    """Raised when no OS sandbox backend exists. Callers must fail closed."""


def backend_name() -> str | None:
    system = platform.system()
    if system == "Darwin" and shutil.which("sandbox-exec") and _seatbelt_usable():
        return "seatbelt"
    if system == "Linux":
        if shutil.which("bwrap") and _bwrap_usable():
            return "bwrap"
        if shutil.which("firejail") and _firejail_usable():
            return "firejail"
        if shutil.which("docker") and _docker_usable():
            return "docker"
    return None


def available() -> bool:
    return backend_name() is not None


def _portable_readonly_roots(
    workspace: Path, readonly_paths: tuple[Path, ...],
) -> tuple[Path, ...]:
    """Resolve portable read-only overlays, broadening safely when absent.

    Mount backends cannot overlay a path that does not exist. Walking to the
    nearest existing ancestor may deny extra writes, but never permits a lane
    escape. Symlink resolution outside the workspace is invalid.
    """
    ws = workspace.resolve()
    roots: set[Path] = set()
    for raw in readonly_paths:
        path = Path(raw).resolve()
        if not path.is_relative_to(ws):
            raise ValueError(f"read-only lane path {raw} is outside workspace {ws}")
        while not path.exists() and path != ws:
            path = path.parent
        roots.add(path)
    ordered = sorted(roots, key=lambda path: (len(path.parts), str(path)))
    collapsed: list[Path] = []
    for root in ordered:
        if not any(root == parent or root.is_relative_to(parent)
                   for parent in collapsed):
            collapsed.append(root)
    return tuple(collapsed)


def _seatbelt_profile(
    workspace: Path, allow_network: bool,
    readonly_paths: tuple[Path, ...] = (),
) -> str:
    home = json.dumps(str(Path.home()))
    ws = json.dumps(str(workspace.resolve()))
    # SBPL: last matching rule wins, so deny-home then allow-workspace confines
    # writes to the workspace even though it sits under home.
    lines = [
        "(version 1)",
        "(allow default)",
        f"(deny file-write* (subpath {home}))",
        f"(allow file-write* (subpath {ws}))",
    ]
    for path in _portable_readonly_roots(workspace, readonly_paths):
        # Last match wins in SBPL, so these restrictions override the broad
        # workspace allow above.
        literal = json.dumps(str(path))
        lines.append(f"(deny file-write* (literal {literal}))")
        lines.append(f"(deny file-write* (subpath {literal}))")
    if not allow_network:
        lines.append("(deny network*)")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _seatbelt_usable() -> bool:
    """True only when sandbox-exec can actually apply a profile.

    Some managed macOS hosts expose the binary but deny applying Seatbelt
    profiles (`sandbox_apply: Operation not permitted`). Treat that exactly
    like a missing backend so callers fail closed instead of believing the
    child process was confined.
    """
    if platform.system() != "Darwin" or not shutil.which("sandbox-exec"):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="harnessie-sandbox-") as d:
            profile = _seatbelt_profile(Path(d), allow_network=False)
            proc = subprocess.run(
                ["sandbox-exec", "-p", profile, "true"],
                capture_output=True,
                text=True,
                timeout=5,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _bwrap_argv(
    argv: list[str], ws: Path, allow_network: bool,
    readonly_paths: tuple[Path, ...] = (),
) -> list[str]:
    # Read-only root, minimal /dev, private /tmp, the workspace as the only
    # writable subtree. Stricter than Seatbelt's deny-home policy (all of the
    # filesystem is read-only, not just home), which satisfies the same
    # guarantee. --new-session blocks TIOCSTI terminal injection.
    wrapped = ["bwrap",
               "--ro-bind", "/", "/",
               "--dev", "/dev",
               "--proc", "/proc",
               "--tmpfs", "/tmp",
               "--bind", str(ws), str(ws),
               "--die-with-parent", "--new-session"]
    for path in _portable_readonly_roots(ws, readonly_paths):
        wrapped.extend(("--ro-bind", str(path), str(path)))
    if not allow_network:
        wrapped.append("--unshare-net")
    return [*wrapped, "--", *argv]


def _firejail_argv(
    argv: list[str], ws: Path, allow_network: bool,
    readonly_paths: tuple[Path, ...] = (),
) -> list[str]:
    # Mirrors the Seatbelt policy shape: home read-only except the workspace,
    # private /dev and /tmp.
    wrapped = ["firejail", "--quiet", "--noprofile",
               "--private-dev", "--private-tmp",
               f"--read-only={Path.home()}",
               f"--read-write={ws}"]
    wrapped.extend(f"--read-only={path}"
                   for path in _portable_readonly_roots(ws, readonly_paths))
    if not allow_network:
        wrapped.append("--net=none")
    return [*wrapped, "--", *argv]


def _docker_argv(
    argv: list[str], ws: Path, allow_network: bool,
    readonly_paths: tuple[Path, ...] = (),
) -> list[str]:
    image = os.environ.get("HARNESSIE_SANDBOX_IMAGE", DEFAULT_DOCKER_IMAGE)
    wrapped = ["docker", "run", "--rm",
               "--user", f"{os.getuid()}:{os.getgid()}",
               "-v", f"{ws}:{ws}",
               "-w", str(ws)]
    for path in _portable_readonly_roots(ws, readonly_paths):
        wrapped += ["--mount", f"type=bind,src={path},dst={path},readonly"]
    if not allow_network:
        wrapped += ["--network", "none"]
    return [*wrapped, image, *argv]


@lru_cache(maxsize=1)
def _bwrap_usable() -> bool:
    """True only when bubblewrap can create its namespaces here (some hosts
    ship the binary but restrict unprivileged user namespaces)."""
    try:
        proc = subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--unshare-net",
             "--die-with-parent", "true"],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


@lru_cache(maxsize=1)
def _firejail_usable() -> bool:
    try:
        proc = subprocess.run(
            ["firejail", "--quiet", "--noprofile", "true"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


@lru_cache(maxsize=1)
def _docker_usable() -> bool:
    """Requires a reachable daemon, not just the CLI. Image availability is
    not probed; a missing image surfaces as a nonzero exit at run time."""
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _backend_argv(
    name: str, argv: list[str], workspace: Path, allow_network: bool,
    readonly_paths: tuple[Path, ...] = (),
) -> list[str]:
    if name == "seatbelt":
        profile = _seatbelt_profile(workspace, allow_network, readonly_paths)
        return ["sandbox-exec", "-p", profile, *argv]
    if name == "bwrap":
        return _bwrap_argv(argv, workspace, allow_network, readonly_paths)
    if name == "firejail":
        return _firejail_argv(argv, workspace, allow_network, readonly_paths)
    if name == "docker":
        return _docker_argv(argv, workspace, allow_network, readonly_paths)
    raise SandboxUnavailable(f"sandbox backend {name!r} is unavailable")


@lru_cache(maxsize=None)
def _readonly_backend_usable(name: str) -> bool:
    """Probe that a backend enforces a nested read-only overlay.

    Docker remains unavailable for lane profiles until its configured image is
    explicitly probe-admitted; `docker info` alone proves only the daemon.
    """
    if name == "docker":
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="harnessie-lanes-") as raw:
            ws = Path(raw).resolve()
            protected = ws / "protected"
            protected.mkdir()
            locked = protected / "locked.txt"
            locked.write_text("original", encoding="utf-8")
            script = (
                "from pathlib import Path; "
                "Path('allowed.txt').write_text('ok'); "
                "\ntry: Path('protected/locked.txt').write_text('changed')"
                "\nexcept OSError: raise SystemExit(0)"
                "\nraise SystemExit(9)"
            )
            argv = _backend_argv(
                name, [sys.executable, "-c", script], ws, False,
                (protected,))
            proc = subprocess.run(
                argv, cwd=ws, capture_output=True, text=True, timeout=10)
            return (proc.returncode == 0
                    and (ws / "allowed.txt").read_text(encoding="utf-8") == "ok"
                    and locked.read_text(encoding="utf-8") == "original")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False


def readonly_available() -> bool:
    return readonly_backend_name() is not None


def readonly_backend_name() -> str | None:
    """Best available backend that proves nested read-only enforcement."""
    system = platform.system()
    candidates: list[tuple[str, bool]] = []
    if system == "Darwin":
        candidates.append((
            "seatbelt", bool(shutil.which("sandbox-exec") and _seatbelt_usable())))
    elif system == "Linux":
        candidates.extend((
            ("bwrap", bool(shutil.which("bwrap") and _bwrap_usable())),
            ("firejail", bool(shutil.which("firejail") and _firejail_usable())),
        ))
    for name, base_usable in candidates:
        if base_usable and _readonly_backend_usable(name):
            return name
    return None


def wrap(
    argv: list[str], workspace: Path, allow_network: bool = False,
    readonly_paths: tuple[Path, ...] = (),
) -> list[str]:
    """Return a sandboxed argv for `argv`, or raise SandboxUnavailable.

    The returned list is passed straight to subprocess.run (no shell), so the
    profile string travels as one argv element and needs no escaping."""
    base_name = backend_name()
    ws = Path(workspace).resolve()
    if base_name is None:
        raise SandboxUnavailable(
            f"no OS sandbox backend on {platform.system()}; child-process "
            "execution is blocked (fail-closed policy). Wire a backend "
            "(bubblewrap / firejail / docker) to enable shell on this platform.")
    readonly = _portable_readonly_roots(ws, readonly_paths)
    name = readonly_backend_name() if readonly else base_name
    if name is None:
        raise SandboxUnavailable(
            f"available OS sandbox backend {base_name!r} did not prove nested "
            "read-only lane enforcement; child-process execution is blocked "
            "fail-closed")
    return _backend_argv(name, argv, ws, allow_network, readonly)
