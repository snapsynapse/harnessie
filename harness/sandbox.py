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
  - Confine writes to the workspace: writes anywhere under the user's home are
    denied except the workspace subtree. Temp dirs outside home stay writable
    so interpreters function; that is a deliberate boundary (the protected
    asset is the user's files and the exfil channel, not scratch space).

Backend today: macOS Seatbelt via `sandbox-exec -p <profile>` (native, no deps).
Linux backends (bubblewrap, firejail, docker) are a documented follow-up; until
one is wired, Linux fails closed.
"""

from __future__ import annotations

import platform
import shutil
from pathlib import Path


class SandboxUnavailable(Exception):
    """Raised when no OS sandbox backend exists. Callers must fail closed."""


def backend_name() -> str | None:
    if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
        return "seatbelt"
    return None


def available() -> bool:
    return backend_name() is not None


def _seatbelt_profile(workspace: Path, allow_network: bool) -> str:
    home = str(Path.home())
    ws = str(workspace.resolve())
    # SBPL: last matching rule wins, so deny-home then allow-workspace confines
    # writes to the workspace even though it sits under home.
    lines = [
        "(version 1)",
        "(allow default)",
        f'(deny file-write* (subpath "{home}"))',
        f'(allow file-write* (subpath "{ws}"))',
    ]
    if not allow_network:
        lines.append("(deny network*)")
    return "\n".join(lines)


def wrap(argv: list[str], workspace: Path, allow_network: bool = False) -> list[str]:
    """Return a sandboxed argv for `argv`, or raise SandboxUnavailable.

    The returned list is passed straight to subprocess.run (no shell), so the
    profile string travels as one argv element and needs no escaping."""
    name = backend_name()
    if name == "seatbelt":
        profile = _seatbelt_profile(Path(workspace), allow_network)
        return ["sandbox-exec", "-p", profile, *argv]
    raise SandboxUnavailable(
        f"no OS sandbox backend on {platform.system()}; child-process "
        "execution is blocked (fail-closed policy). Wire a backend "
        "(bubblewrap / firejail / docker) to enable shell on this platform.")
