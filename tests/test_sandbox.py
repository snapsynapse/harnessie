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
    assert argv[0] == "sandbox-exec" and "pytest" in argv


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
        assert "not permitted" in res.content.lower() or "denied" in res.content.lower()
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
    assert "sandbox unavailable" in res.content and "blocked" in res.content


def test_gate_check_fails_closed_without_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "backend_name", lambda: None)
    proofs = ProofStore(tmp_path / "run")
    events = EventLog(tmp_path / "run", echo=False)
    results = run_checks([Check(name="t", command="python3 -c pass")],
                         tmp_path, proofs, events, attempt=1)
    assert not results[0].passed
    assert "sandbox unavailable" in results[0].output
