"""Proves the OS sandbox closes the interpreter-escape gap: an allowlisted
python3 can no longer write outside the workspace or open the network, and
when no sandbox backend exists the harness fails closed.

These tests execute real sandbox-exec on macOS. On a platform with no backend
the escape/allow cases are skipped (there is nothing to confine), but the
fail-closed cases still run and are the important ones there.
"""

import sys
from pathlib import Path

import pytest

from harness import sandbox
from harness.events import EventLog
from harness.memory import ProofStore
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry
from harness.verify import Check, run_checks

HAS_SANDBOX = sandbox.available()
needs_sandbox = pytest.mark.skipif(not HAS_SANDBOX, reason="no OS sandbox backend")


def make_reg(tmp_path):
    reg = ToolRegistry()
    ws = tmp_path / "ws"
    ws.mkdir()
    register_builtin(reg, workspace=ws)
    return reg, ws


# -- policy unit tests (backend-independent) --------------------------------

def test_profile_denies_network_by_default(tmp_path):
    prof = sandbox._seatbelt_profile(tmp_path, allow_network=False)
    assert "(deny network*)" in prof
    assert '(deny file-write* (subpath "' in prof   # home write denied
    open_prof = sandbox._seatbelt_profile(tmp_path, allow_network=True)
    assert "(deny network*)" not in open_prof         # opt-in lifts it


def test_wrap_returns_sandbox_prefixed_argv(tmp_path):
    if not HAS_SANDBOX:
        with pytest.raises(sandbox.SandboxUnavailable):
            sandbox.wrap(["ls"], tmp_path)
        return
    argv = sandbox.wrap(["pytest", "-q"], tmp_path)
    # The wrapper binary is backend-specific: sandbox-exec on macOS, bwrap /
    # firejail / docker on Linux. Assert it matches the admitted backend.
    expected = {"seatbelt": "sandbox-exec", "bwrap": "bwrap",
                "firejail": "firejail", "docker": "docker"}[sandbox.backend_name()]
    assert argv[0] == expected and "pytest" in argv


# -- the actual gap: interpreter escape (needs a real backend) --------------

@needs_sandbox
def test_worker_python_cannot_write_outside_workspace(tmp_path):
    reg, ws = make_reg(tmp_path)
    escape = Path.home() / ".harnessie-sandbox-escape-test.txt"
    if escape.exists():
        escape.unlink()
    # no path ARGUMENT (arg jail can't see it); the write target is inside the
    # code string, exactly the gap the OS sandbox exists to close
    res = reg.dispatch("worker", "run_shell", {
        "command": f"python3 -c \"open('{escape}','w').write('pwned')\""})
    try:
        assert res.ok                       # the tool ran; the WRITE was denied
        # Seatbelt says "not permitted"/"denied"; bwrap's read-only root says
        # "read-only file system". Same guarantee, different kernel phrasing.
        assert any(s in res.content.lower() for s in
                   ("not permitted", "denied", "read-only file system"))
        assert not escape.exists()
    finally:
        if escape.exists():
            escape.unlink()


@needs_sandbox
def test_worker_python_can_write_inside_workspace(tmp_path):
    reg, ws = make_reg(tmp_path)
    res = reg.dispatch("worker", "run_shell", {
        "command": "python3 -c \"open('inside.txt','w').write('ok')\""})
    assert res.ok and "exit=0" in res.content
    assert (ws / "inside.txt").read_text() == "ok"


@needs_sandbox
def test_worker_network_denied_by_default(tmp_path):
    reg, ws = make_reg(tmp_path)
    res = reg.dispatch("worker", "run_shell", {
        "command": "python3 -c \"import socket; socket.create_connection(('example.com',80),3)\""})
    assert res.ok
    # sandbox blocks name resolution / connect; either way it is not a success
    assert "exit=0" not in res.content or "error" in res.content.lower()


# -- fail closed everywhere (runs on all platforms) -------------------------

def test_run_shell_fails_closed_without_backend(tmp_path, monkeypatch):
    reg, ws = make_reg(tmp_path)
    monkeypatch.setattr(sandbox, "backend_name", lambda: None)
    res = reg.dispatch("worker", "run_shell", {"command": "ls"})
    assert res.ok            # tool returned cleanly...
    assert res.refusal and res.refusal.error == "sandbox_unavailable"
    assert res.refusal.boundary == "sandbox"


def test_gate_check_fails_closed_without_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "backend_name", lambda: None)
    proofs = ProofStore(tmp_path / "run")
    events = EventLog(tmp_path / "run", echo=False)
    results = run_checks([Check(name="t", command="python3 -c pass")],
                         tmp_path, proofs, events, attempt=1)
    assert not results[0].passed
    assert "sandbox unavailable" in results[0].output


# -- Linux backend selection and policy construction (run on any host) ------

def _force_linux(monkeypatch, which_available):
    monkeypatch.setattr(sandbox.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        sandbox.shutil, "which",
        lambda name: f"/usr/bin/{name}" if name in which_available else None)


def test_linux_backend_preference_order(monkeypatch):
    _force_linux(monkeypatch, {"bwrap", "firejail", "docker"})
    monkeypatch.setattr(sandbox, "_bwrap_usable", lambda: True)
    monkeypatch.setattr(sandbox, "_firejail_usable", lambda: True)
    monkeypatch.setattr(sandbox, "_docker_usable", lambda: True)
    assert sandbox.backend_name() == "bwrap"
    monkeypatch.setattr(sandbox, "_bwrap_usable", lambda: False)
    assert sandbox.backend_name() == "firejail"
    monkeypatch.setattr(sandbox, "_firejail_usable", lambda: False)
    assert sandbox.backend_name() == "docker"
    monkeypatch.setattr(sandbox, "_docker_usable", lambda: False)
    assert sandbox.backend_name() is None


def test_linux_present_but_unusable_backend_fails_closed(monkeypatch):
    # binary on PATH, smoke test failing (e.g. userns restricted) = no backend
    _force_linux(monkeypatch, {"bwrap"})
    monkeypatch.setattr(sandbox, "_bwrap_usable", lambda: False)
    assert sandbox.backend_name() is None
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.wrap(["ls"], Path("/tmp"))


def test_bwrap_policy_confines_writes_and_network(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "backend_name", lambda: "bwrap")
    ws = tmp_path.resolve()
    argv = sandbox.wrap(["python3", "-c", "pass"], tmp_path)
    assert argv[0] == "bwrap"
    assert "--unshare-net" in argv and "--die-with-parent" in argv
    i = argv.index("--ro-bind")
    assert argv[i + 1] == "/" and argv[i + 2] == "/"
    j = argv.index("--bind")
    assert argv[j + 1] == str(ws) and argv[j + 2] == str(ws)
    assert argv[argv.index("--") + 1:] == ["python3", "-c", "pass"]
    open_net = sandbox.wrap(["ls"], tmp_path, allow_network=True)
    assert "--unshare-net" not in open_net


def test_firejail_policy_confines_writes_and_network(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "backend_name", lambda: "firejail")
    ws = tmp_path.resolve()
    argv = sandbox.wrap(["pytest", "-q"], tmp_path)
    assert argv[0] == "firejail" and "--net=none" in argv
    assert f"--read-only={Path.home()}" in argv
    assert f"--read-write={ws}" in argv
    assert "--noprofile" in argv and "--private-tmp" in argv
    assert "--net=none" not in sandbox.wrap(["ls"], tmp_path, allow_network=True)


def test_docker_policy_confines_writes_and_network(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "backend_name", lambda: "docker")
    ws = tmp_path.resolve()
    argv = sandbox.wrap(["python3", "-c", "pass"], tmp_path)
    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert f"{ws}:{ws}" in argv
    u = argv.index("--user")
    assert argv[u + 1] == f"{sandbox.os.getuid()}:{sandbox.os.getgid()}"
    # non-root even if the image defaults to root
    assert argv[u + 1] != "0:0" or sandbox.os.getuid() == 0
    open_net = sandbox.wrap(["ls"], tmp_path, allow_network=True)
    assert "--network" not in open_net


def test_docker_image_env_override(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "backend_name", lambda: "docker")
    monkeypatch.setenv("HARNESSIE_SANDBOX_IMAGE", "custom:tag")
    argv = sandbox.wrap(["ls"], tmp_path)
    assert "custom:tag" in argv and sandbox.DEFAULT_DOCKER_IMAGE not in argv
