"""Proves the OS sandbox closes the interpreter-escape gap: an allowlisted
python3 can no longer write outside the workspace, into a denied ownership
lane, or onto the network, and missing or insufficient backends fail closed.

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
HAS_LANE_SANDBOX = sandbox.readonly_available()
needs_lane_sandbox = pytest.mark.skipif(
    not HAS_LANE_SANDBOX, reason="no read-only lane sandbox backend")


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


def test_seatbelt_network_opt_in_keeps_local_unix_sockets_denied(tmp_path):
    # Only the resolver pathname is exempt from outbound Unix-socket denial.
    prof = sandbox._seatbelt_profile(tmp_path, allow_network=True)
    lines = prof.splitlines()
    deny = "(deny network-outbound (remote unix-socket))"
    resolver = ('(allow network-outbound (remote unix-socket (path-literal '
                '"/private/var/run/mDNSResponder")))')
    assert deny in lines and resolver in lines
    assert lines.index(deny) < lines.index(resolver)   # last match wins
    assert lines[-1] == resolver                         # nothing re-opens after


def test_seatbelt_profile_restricts_lane_after_workspace_allow(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    prof = sandbox._seatbelt_profile(
        tmp_path, allow_network=False, readonly_paths=(protected,))
    workspace_allow = prof.index('(allow file-write* (subpath "')
    lane_deny = prof.index(f'(deny file-write* (subpath "{protected}"))')
    assert lane_deny > workspace_allow


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


needs_seatbelt = pytest.mark.skipif(
    sys.platform != "darwin" or sandbox.backend_name() != "seatbelt",
    reason="Seatbelt-specific Unix-socket policy")


@pytest.fixture(params=["stream", "datagram-connect", "datagram-sendto"])
def unix_endpoint(request):
    import socket
    import tempfile

    # AF_UNIX paths are capped near 104 bytes on macOS. The server belongs
    # to the test, outside the child's workspace; no real control daemon runs.
    with tempfile.TemporaryDirectory(dir="/tmp") as d:
        ws = Path(d) / "ws"
        ws.mkdir()
        path = Path(d) / "ctl.sock"
        kind = (socket.SOCK_STREAM if request.param == "stream"
                else socket.SOCK_DGRAM)
        with socket.socket(socket.AF_UNIX, kind) as server:
            server.bind(str(path))
            server.settimeout(3)
            if kind == socket.SOCK_STREAM:
                server.listen(4)
            yield ws, path, server, request.param


def _unix_child(path, mode):
    kind = "SOCK_STREAM" if mode == "stream" else "SOCK_DGRAM"
    return ("import socket,sys\n"
            f"s=socket.socket(socket.AF_UNIX, socket.{kind})\n"
            "s.settimeout(3)\n"
            "try:\n"
            + (f" s.sendto(b'probe', {str(path)!r})\n" if mode == "datagram-sendto"
               else f" s.connect({str(path)!r})\n s.sendall(b'probe')\n")
            + "except PermissionError:\n sys.exit(3)\n")


def _run_socket_child(child, ws, profile=None):
    import subprocess

    argv = [sys.executable, "-I", "-c", child]
    if profile is not None:
        argv = ["sandbox-exec", "-p", profile, *argv]
    return subprocess.run(argv, cwd=ws, capture_output=True, timeout=15)


def _receive_probe(server, mode):
    if mode == "stream":
        conn, _ = server.accept()
        with conn:
            assert conn.recv(5) == b"probe"
    else:
        assert server.recv(5) == b"probe"


@needs_seatbelt
@pytest.mark.parametrize("allow_network", [False, True])
@pytest.mark.parametrize("path_style", ["canonical", "tmp-alias", "relative", "symlink"])
def test_seatbelt_child_cannot_reach_unconfined_unix_socket(
        unix_endpoint, allow_network, path_style):
    ws, path, server, mode = unix_endpoint
    if path_style == "canonical":
        target = path.resolve()
    elif path_style == "relative":
        target = Path("../ctl.sock")
    elif path_style == "symlink":
        target = ws / "alias.sock"
        target.symlink_to(path)
    else:
        target = path
    child = _unix_child(target, mode)
    # An unsandboxed positive control proves the endpoint and operation work.
    control = _run_socket_child(child, ws)
    assert control.returncode == 0, control.stderr.decode(errors="replace")
    _receive_probe(server, mode)
    profile = sandbox._seatbelt_profile(ws, allow_network=allow_network)
    result = _run_socket_child(child, ws, profile)
    assert result.returncode == 3, result.stderr.decode(errors="replace")


@needs_seatbelt
def test_seatbelt_resolver_exception_is_exact_and_usable(unix_endpoint):
    import json
    import socket

    ws, path, server, mode = unix_endpoint
    profile = sandbox._seatbelt_profile(ws, allow_network=True)
    # Substitute our controlled endpoint for the one resolver literal. This
    # tests native exception precedence without contacting a system service.
    resolver = '"/private/var/run/mDNSResponder"'
    assert profile.count(resolver) == 1
    profile = profile.replace(resolver, json.dumps(str(path.resolve())))
    result = _run_socket_child(_unix_child(path, mode), ws, profile)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    _receive_probe(server, mode)
    other = path.with_name("other.sock")
    with socket.socket(server.family, server.type) as neighbor:
        neighbor.bind(str(other))
        if mode == "stream":
            neighbor.listen(1)
        result = _run_socket_child(_unix_child(other, mode), ws, profile)
        assert result.returncode == 3, result.stderr.decode(errors="replace")


@needs_seatbelt
@pytest.mark.parametrize("allow_network", [False, True])
def test_seatbelt_network_opt_in_preserves_tcp(tmp_path, allow_network):
    import socket

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        child = ("import socket,sys\n"
                 "try:\n"
                 f" s=socket.create_connection({server.getsockname()!r}, 3)\n"
                 "except PermissionError:\n sys.exit(3)\n")
        profile = sandbox._seatbelt_profile(tmp_path, allow_network=allow_network)
        result = _run_socket_child(child, tmp_path, profile)
        assert result.returncode == (0 if allow_network else 3), (
            result.stderr.decode(errors="replace"))


@needs_lane_sandbox
def test_worker_interpreter_cannot_modify_operator_lane(tmp_path):
    ws = tmp_path / "ws"
    frozen = ws / "frozen"
    frozen.mkdir(parents=True)
    target = frozen / "config.txt"
    target.write_text("original")
    ledger_path = tmp_path / "OWNERSHIP.yaml"
    ledger_path.write_text("lanes:\n  operator: ['frozen/*']\n")
    from harness.ownership import OwnershipLedger
    reg = ToolRegistry()
    register_builtin(reg, workspace=ws, ledger=OwnershipLedger.load(ledger_path))
    res = reg.dispatch("worker", "run_shell", {
        "command": "python3 -c \"from pathlib import Path; "
                   "Path('allowed.txt').write_text('ok'); "
                   "Path('frozen/config.txt').write_text('changed')\"",
    }, agent="implementer")
    assert res.ok and "exit=0" not in res.content
    assert (ws / "allowed.txt").read_text() == "ok"
    assert target.read_text() == "original"


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


def test_gate_check_receives_worker_lane_profile(tmp_path, monkeypatch):
    protected = tmp_path / "protected"
    protected.mkdir()
    captured = {}

    def fake_wrap(argv, workspace, allow_network=False, readonly_paths=()):
        captured["readonly"] = readonly_paths
        return ["true"]

    monkeypatch.setattr(sandbox, "wrap", fake_wrap)
    proofs = ProofStore(tmp_path / "run")
    events = EventLog(tmp_path / "run", echo=False)
    results = run_checks(
        [Check(name="t", command="python3 -c pass")],
        tmp_path, proofs, events, attempt=1,
        readonly_paths=(protected,))
    assert results[0].passed
    assert captured["readonly"] == (protected,)


def test_readonly_lane_backend_failure_blocks_child(monkeypatch, tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    monkeypatch.setattr(sandbox, "backend_name", lambda: "docker")
    monkeypatch.setattr(sandbox, "readonly_backend_name", lambda: None)
    with pytest.raises(sandbox.SandboxUnavailable, match="lane enforcement"):
        sandbox.wrap(["ls"], tmp_path, readonly_paths=(protected,))


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


def test_lane_backend_falls_through_to_proven_alternative(monkeypatch):
    _force_linux(monkeypatch, {"bwrap", "firejail", "docker"})
    monkeypatch.setattr(sandbox, "_bwrap_usable", lambda: True)
    monkeypatch.setattr(sandbox, "_firejail_usable", lambda: True)
    monkeypatch.setattr(
        sandbox, "_readonly_backend_usable", lambda name: name == "firejail")
    assert sandbox.readonly_backend_name() == "firejail"


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


def test_backend_argv_adds_nested_readonly_overlays(tmp_path):
    ws = tmp_path.resolve()
    protected = ws / "protected"
    protected.mkdir()
    bwrap = sandbox._bwrap_argv(["true"], ws, False, (protected,))
    pairs = list(zip(bwrap, bwrap[1:], bwrap[2:]))
    assert ("--ro-bind", str(protected), str(protected)) in pairs
    firejail = sandbox._firejail_argv(["true"], ws, False, (protected,))
    assert f"--read-only={protected}" in firejail
    docker = sandbox._docker_argv(["true"], ws, False, (protected,))
    assert f"type=bind,src={protected},dst={protected},readonly" in docker


def test_absent_protected_path_broadens_to_existing_parent(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    roots = sandbox._portable_readonly_roots(
        tmp_path, (parent / "future" / "locked.txt",))
    assert roots == (parent.resolve(),)


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
