from pathlib import Path

import pytest

from harness.tools.builtin import register_builtin
from harness.tools.registry import PermissionDenied, ToolRegistry, ToolSpec


def make_registry(tmp_path: Path) -> ToolRegistry:
    reg = ToolRegistry()
    register_builtin(reg, workspace=tmp_path)
    return reg


def test_role_filtering(tmp_path):
    reg = make_registry(tmp_path)
    worker_tools = {t["name"] for t in reg.schemas("worker")}
    verifier_tools = {t["name"] for t in reg.schemas("verifier")}
    orch_tools = {t["name"] for t in reg.schemas("orchestrator")}
    assert "write_file" in worker_tools
    assert "write_file" not in verifier_tools       # verifiers are read-only
    assert "write_file" not in orch_tools           # orchestrator has no side effects
    assert "run_shell" in verifier_tools            # but verifiers run tests
    assert "run_shell" not in orch_tools


def test_dispatch_denies_ungrated_role(tmp_path):
    reg = make_registry(tmp_path)
    with pytest.raises(PermissionDenied) as err:
        reg.dispatch("verifier", "write_file", {"path": "x.txt", "content": "hi"})
    assert err.value.refusal
    assert err.value.refusal.error == "authority_insufficient"
    assert err.value.refusal.boundary == "role"


def test_unknown_tool_is_structured_refusal(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "missing_tool", {})
    assert not res.ok
    assert res.refusal and res.refusal.error == "action_unsupported"
    assert res.refusal.boundary == "allowlist"


def test_workspace_jail(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "write_file",
                       {"path": "../escape.txt", "content": "nope"})
    assert not res.ok
    assert res.refusal and res.refusal.error == "workspace_jail_escape"
    assert res.refusal.boundary == "jail"


def test_approval_fails_closed(tmp_path):
    reg = ToolRegistry()   # default approval_handler denies everything
    reg.register(ToolSpec(name="deploy", description="d",
                          parameters={"type": "object", "properties": {}},
                          fn=lambda: "deployed", effects="write",
                          allowed_roles=frozenset({"worker"}),
                          requires_approval=True))
    res = reg.dispatch("worker", "deploy", {})
    assert not res.ok
    assert res.refusal and res.refusal.error == "approval_required"
    assert res.refusal.boundary == "approval"


def test_malformed_args_rejected(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "write_file", {"_malformed": "{bad json"})
    assert not res.ok
    assert res.refusal and res.refusal.error == "malformed_arguments"


def test_bad_arguments_are_structured_refusal(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "write_file", {"path": "x.txt"})
    assert not res.ok
    assert res.refusal and res.refusal.error == "bad_arguments"


def test_tool_exception_is_structured_refusal(tmp_path):
    reg = ToolRegistry()
    reg.register(ToolSpec(name="boom", description="d",
                          parameters={"type": "object", "properties": {}},
                          fn=lambda: (_ for _ in ()).throw(RuntimeError("nope")),
                          effects="read",
                          allowed_roles=frozenset({"worker"})))
    res = reg.dispatch("worker", "boom", {})
    assert not res.ok
    assert res.refusal and res.refusal.error == "tool_exception"


def test_shell_allowlist(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "run_shell", {"command": "rm -rf /"})
    assert res.ok
    assert res.refusal and res.refusal.error == "command_not_allowlisted"
    assert res.refusal.boundary == "allowlist"


def test_verifier_shell_is_read_only(tmp_path):
    reg = make_registry(tmp_path)
    # interpreters and git are worker-only; the verifier read-only boundary is
    # enforced by the allowlist, not just the prompt
    res = reg.dispatch("verifier", "run_shell",
                       {"command": "python3 -c \"open('x','w').write('pwned')\""})
    assert res.refusal and res.refusal.error == "command_not_allowlisted"
    assert not (tmp_path / "x").exists()
    res = reg.dispatch("verifier", "run_shell", {"command": "git checkout ."})
    assert res.refusal and res.refusal.error == "command_not_allowlisted"
    # but the test runner stays available
    res = reg.dispatch("verifier", "run_shell", {"command": "ls"})
    assert res.ok


def test_shell_argument_jail(tmp_path):
    reg = make_registry(tmp_path)
    res = reg.dispatch("worker", "run_shell", {"command": "cat /etc/passwd"})
    assert res.refusal and res.refusal.error == "argument_jail_escape"
    res = reg.dispatch("worker", "run_shell", {"command": "ls ../.."})
    assert res.refusal and res.refusal.error == "argument_jail_escape"


def test_duplicate_registration_rejected(tmp_path):
    reg = make_registry(tmp_path)
    with pytest.raises(ValueError):
        reg.register(ToolSpec(name="read_file", description="dupe",
                              parameters={}, fn=lambda: ""))
