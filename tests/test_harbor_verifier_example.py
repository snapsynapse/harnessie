"""The Harbor verifier example: exit codes map to rewards, exit 2 stays unscorable."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from harness import sandbox

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "harbor-verifier"
TASK = EXAMPLE / "tasks" / "calc-add-mean"

needs_sandbox = pytest.mark.skipif(
    not sandbox.available(),
    reason="no OS sandbox backend: harnessie verify reports cannot-verify by design")


def _load_reward_module():
    spec = importlib.util.spec_from_file_location(
        "harnessie_reward", EXAMPLE / "harnessie_reward.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reward = _load_reward_module()

GOOD_CALC = (
    "def add(a, b):\n    return a + b\n\n\n"
    "def mean(xs):\n    if not xs:\n        raise ValueError('empty')\n"
    "    return sum(xs) / len(xs)\n")
BAD_CALC = GOOD_CALC.replace("return a + b", "return a - b")


def test_exit_codes_map_to_rewards_and_two_is_unscorable():
    assert reward.reward_from_exit(0) == {"reward": 1.0}
    assert reward.reward_from_exit(1) == {"reward": 0.0}
    assert reward.reward_from_exit(2) is None
    assert reward.reward_from_exit(137) is None


@pytest.mark.parametrize("code,expect_file,expect_value", [
    (0, True, "1"), (1, True, "0"), (2, False, None), (99, False, None)])
def test_reward_files_follow_the_mapping(tmp_path, code, expect_file, expect_value):
    out = reward.write_reward_files(tmp_path / "verifier", code)
    reward_txt = tmp_path / "verifier" / "reward.txt"
    diagnostic = json.loads((tmp_path / "verifier" / "harnessie-verify.json").read_text())
    assert reward_txt.exists() is expect_file
    if expect_file:
        assert reward_txt.read_text().strip() == expect_value
        assert out == {"reward": float(expect_value)}
    else:
        assert out is None
        assert diagnostic["outcome"] == "cannot_verify"
    assert diagnostic["scored"] is expect_file


def test_parse_checks_accepts_harbor_kwarg_strings_and_lists():
    assert reward.parse_checks("a ;; b ;;  ") == ["a", "b"]
    assert reward.parse_checks(["x", "y"]) == ["x", "y"]
    assert reward.parse_checks(None) == []


def test_verify_command_is_deterministic_checks_only(tmp_path):
    argv = reward.verify_command(tmp_path, tmp_path / "c.md", ["true", "false"],
                                 tmp_path / "r", python="py")
    assert argv[:4] == ["py", "-m", "harness.cli", "verify"]
    assert "--no-verifier" in argv
    assert argv.count("--check") == 2


def _run_test_sh(tmp_path, stub_exit):
    stub = tmp_path / "stub.sh"
    stub.write_text(f"#!/bin/sh\necho stub args: \"$@\"\nexit {stub_exit}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    logs = tmp_path / "logs"
    env = {**os.environ, "HARBOR_VERIFIER_DIR": str(logs),
           "HARBOR_WORKSPACE": str(tmp_path), "HARBOR_CLAIMS": str(TASK / "tests" / "claims.md"),
           "HARNESSIE_VERIFY_CMD": str(stub)}
    completed = subprocess.run(["bash", str(TASK / "tests" / "test.sh")], env=env,
                               capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    return logs


@pytest.mark.parametrize("stub_exit,expect_file,expect_value", [
    (0, True, "1"), (1, True, "0"), (2, False, None), (3, False, None)])
def test_in_sandbox_script_maps_exit_codes(tmp_path, stub_exit, expect_file, expect_value):
    logs = _run_test_sh(tmp_path, stub_exit)
    assert (logs / "reward.txt").exists() is expect_file
    if expect_file:
        assert (logs / "reward.txt").read_text().strip() == expect_value
    diagnostic = json.loads((logs / "harnessie-verify.json").read_text())
    assert diagnostic["scored"] is expect_file
    if not expect_file:
        assert diagnostic["outcome"] == "cannot_verify"
        assert diagnostic["exit_code"] == 2
    log = (logs / "harnessie-verify.log").read_text()
    assert "--no-verifier" in log and log.count("--check") == 2


def test_task_files_are_executable_and_complete():
    for name in ("tests/test.sh", "solution/solve.sh"):
        mode = (TASK / name).stat().st_mode
        assert mode & stat.S_IXUSR, f"{name} is not executable"
    for name in ("instruction.md", "task.toml", "environment/Dockerfile",
                 "tests/claims.md"):
        assert (TASK / name).is_file(), name


@needs_sandbox
@pytest.mark.parametrize("calc,expected", [(GOOD_CALC, 0), (BAD_CALC, 1)])
def test_real_verify_scores_good_and_bad_workspaces(tmp_path, calc, expected):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "calc.py").write_text(calc, encoding="utf-8")
    checks = [
        "python3 -c 'import calc; assert calc.add(2, 3) == 5'",
        "python3 -c \"import calc\nraised = False\ntry:\n    calc.mean([])\n"
        "except ValueError:\n    raised = True\nassert raised\"",
    ]
    code = reward.run_harnessie_verify(workspace, TASK / "tests" / "claims.md", checks,
                                       tmp_path / "report", python=sys.executable)
    assert code == expected
    assert reward.write_reward_files(tmp_path / "v", code) == {"reward": float(code == 0)}


def test_real_verify_with_no_checks_is_cannot_verify(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "calc.py").write_text(GOOD_CALC, encoding="utf-8")
    code = reward.run_harnessie_verify(workspace, TASK / "tests" / "claims.md", [],
                                       tmp_path / "report", python=sys.executable)
    assert code == 2
    assert reward.write_reward_files(tmp_path / "v", code) is None
    assert not (tmp_path / "v" / "reward.txt").exists()


def test_host_side_verifier_loads_where_harbor_is_installed():
    pytest.importorskip("harbor.verifier.base")
    sys.path.insert(0, str(EXAMPLE))
    try:
        spec = importlib.util.spec_from_file_location(
            "harnessie_verifier", EXAMPLE / "harnessie_verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(EXAMPLE))
    assert len(module.DEFAULT_CHECKS) == 2
