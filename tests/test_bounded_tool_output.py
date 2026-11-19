"""SEC-20261118-012 (file and child-output part): read_file and run_shell
stream under byte ceilings with an overflow sentinel instead of reading
everything and truncating afterwards. run_shell enforces a whole-call
deadline, bounds stdout and stderr separately, and kills the child's
process group, including a descendant that keeps the pipes open after the
direct child exits. All fixtures are synthetic and local.
"""

import os
import sys
import threading
import time
import tracemalloc

import pytest

from harness import sandbox
import harness.tools.builtin as builtin
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry

SENTINEL_PREFIX = "[harnessie:truncated "


def _registry(tmp_path, allowlists=None):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    reg = ToolRegistry()
    register_builtin(reg, workspace=ws, shell_allowlists=allowlists)
    return reg, ws


@pytest.fixture
def no_sandbox(monkeypatch):
    monkeypatch.setattr(builtin, "sandbox_wrap",
                        lambda argv, workspace, allow_network=False: argv)


# -- read_file -----------------------------------------------------------------

def test_read_file_exact_limit_has_no_sentinel(tmp_path, monkeypatch):
    monkeypatch.setattr(builtin, "READ_FILE_MAX_BYTES", 1000)
    reg, ws = _registry(tmp_path)
    (ws / "f.txt").write_bytes(b"a" * 1000)
    res = reg.dispatch("worker", "read_file", {"path": "f.txt"})
    assert res.ok and res.content == "a" * 1000


def test_read_file_one_over_limit_is_cut_with_sentinel(tmp_path, monkeypatch):
    monkeypatch.setattr(builtin, "READ_FILE_MAX_BYTES", 1000)
    reg, ws = _registry(tmp_path)
    (ws / "f.txt").write_bytes(b"a" * 1001)
    res = reg.dispatch("worker", "read_file", {"path": "f.txt"})
    assert res.ok
    body, _, marker = res.content.partition("\n" + SENTINEL_PREFIX)
    assert body == "a" * 1000
    assert "source=read_file" in marker and "limit_bytes=1000" in marker


def test_read_file_cut_inside_multibyte_char_drops_partial_sequence(tmp_path, monkeypatch):
    monkeypatch.setattr(builtin, "READ_FILE_MAX_BYTES", 5)
    reg, ws = _registry(tmp_path)
    (ws / "f.txt").write_text("abcdé and more", encoding="utf-8")   # é spans bytes 4-5
    res = reg.dispatch("worker", "read_file", {"path": "f.txt"})
    body = res.content.partition("\n" + SENTINEL_PREFIX)[0]
    assert body == "abcd"


def test_read_file_large_file_is_read_with_bounded_memory(tmp_path):
    reg, ws = _registry(tmp_path)
    with open(ws / "big.txt", "wb") as fh:      # sparse: cheap on disk
        fh.truncate(64 * 1024 * 1024)
    tracemalloc.start()
    try:
        res = reg.dispatch("worker", "read_file", {"path": "big.txt"})
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert res.ok and SENTINEL_PREFIX in res.content
    assert peak < 8 * 1024 * 1024


def test_read_file_refuses_fifo_without_blocking(tmp_path):
    reg, ws = _registry(tmp_path)
    fifo = ws / "pipe"
    os.mkfifo(fifo)
    box = {}
    worker = threading.Thread(
        target=lambda: box.setdefault(
            "res", reg.dispatch("worker", "read_file", {"path": "pipe"})),
        daemon=True)
    worker.start()
    worker.join(5)
    if worker.is_alive():           # unblock the reader so the test can finish
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
        worker.join(5)
        pytest.fail("read_file blocked on a FIFO")
    res = box["res"]
    assert not res.ok
    assert res.refusal.error == "read_target_unsupported"


def test_read_file_normal_text_unchanged(tmp_path):
    reg, ws = _registry(tmp_path)
    (ws / "notes.md").write_text("line one\nline two\n", encoding="utf-8")
    res = reg.dispatch("worker", "read_file", {"path": "notes.md"})
    assert res.ok and res.content == "line one\nline two\n"


# -- run_shell -----------------------------------------------------------------

@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_shell_stream_exact_limit_has_no_sentinel(tmp_path, monkeypatch, no_sandbox, stream):
    monkeypatch.setattr(builtin, "SHELL_STREAM_MAX_BYTES", 1000)
    reg, _ = _registry(tmp_path)
    res = reg.dispatch("worker", "run_shell", {
        "command": f"python3 -c \"import sys; sys.{stream}.write('a' * 1000)\""})
    assert res.ok and res.refusal is None
    assert res.content == "exit=0\n" + "a" * 1000


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_shell_stream_one_over_limit_is_cut_with_sentinel(tmp_path, monkeypatch, no_sandbox, stream):
    monkeypatch.setattr(builtin, "SHELL_STREAM_MAX_BYTES", 1000)
    reg, _ = _registry(tmp_path)
    res = reg.dispatch("worker", "run_shell", {
        "command": f"python3 -c \"import sys; sys.{stream}.write('a' * 1001)\""})
    assert res.ok and res.refusal is None
    head, _, marker = res.content.partition("\n" + SENTINEL_PREFIX)
    assert head == "exit=0\n" + "a" * 1000
    assert f"stream={stream}" in marker and "limit_bytes=1000" in marker


def test_shell_large_output_is_captured_with_bounded_memory(tmp_path, no_sandbox):
    reg, _ = _registry(tmp_path)
    tracemalloc.start()
    try:
        res = reg.dispatch("worker", "run_shell", {
            "command": "python3 -c \"import sys; [sys.stdout.write('b' * 65536) for _ in range(512)]\""})
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert res.ok and res.refusal is None
    assert res.content.startswith("exit=0\n")
    assert SENTINEL_PREFIX in res.content
    assert peak < 8 * 1024 * 1024


def test_shell_slow_trickle_hits_whole_call_deadline(tmp_path, monkeypatch, no_sandbox):
    monkeypatch.setattr(builtin, "SHELL_DEADLINE_S", 1.0)
    reg, _ = _registry(tmp_path)
    started = time.monotonic()
    res = reg.dispatch("worker", "run_shell", {
        "command": "python3 -c \"import sys, time\nwhile True:\n sys.stdout.write('.'); sys.stdout.flush(); time.sleep(0.05)\""})
    elapsed = time.monotonic() - started
    assert res.refusal is not None
    assert res.refusal.error == "shell_deadline_exceeded"
    assert res.refusal.boundary == "deadline"
    assert elapsed < 10


def test_shell_missing_executable_is_structured_refusal(tmp_path, no_sandbox):
    reg, _ = _registry(tmp_path, allowlists={
        "worker": ("harnessie-absent-executable-fixture",)})
    res = reg.dispatch("worker", "run_shell",
                       {"command": "harnessie-absent-executable-fixture --help"})
    assert res.refusal is not None
    assert res.refusal.error == "command_unavailable"


ORPHAN_SCRIPT = """\
import subprocess, sys
subprocess.Popen([sys.executable, "-c",
                  "import os, time; open('orphan.pid', 'w').write(str(os.getpid())); "
                  "time.sleep(20)"])
print("parent done")
"""


def _orphan_command(ws) -> str:
    (ws / "orphan.py").write_text(ORPHAN_SCRIPT)
    return "python3 orphan.py"


def _orphan_pid(ws) -> int:
    end = time.monotonic() + 5
    while time.monotonic() < end:
        text = (ws / "orphan.pid").read_text() if (ws / "orphan.pid").exists() else ""
        if text:
            return int(text)
        time.sleep(0.05)
    raise AssertionError("descendant never recorded its pid")


def _wait_gone(pid: int, timeout: float = 5.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_shell_descendant_holding_pipes_is_killed_and_reader_returns(tmp_path, no_sandbox):
    reg, ws = _registry(tmp_path)
    started = time.monotonic()
    res = reg.dispatch("worker", "run_shell", {"command": _orphan_command(ws)})
    elapsed = time.monotonic() - started
    assert res.ok and res.refusal is None, res.content
    assert res.content.startswith("exit=0\n")
    assert "parent done" in res.content
    assert elapsed < 10
    assert _wait_gone(_orphan_pid(ws))


@pytest.mark.skipif(sys.platform != "darwin" or not sandbox.available(),
                    reason="native Seatbelt backend only")
def test_shell_descendant_under_native_sandbox_is_killed(tmp_path):
    reg, ws = _registry(tmp_path)
    started = time.monotonic()
    res = reg.dispatch("worker", "run_shell", {"command": _orphan_command(ws)})
    elapsed = time.monotonic() - started
    assert res.refusal is None, res.content
    assert elapsed < 10
    assert _wait_gone(_orphan_pid(ws))


def test_shell_ordinary_command_output_unchanged(tmp_path, no_sandbox):
    reg, ws = _registry(tmp_path)
    (ws / "a.txt").write_text("hello\n")
    res = reg.dispatch("worker", "run_shell", {"command": "cat a.txt"})
    assert res.ok and res.content == "exit=0\nhello\n"
    res = reg.dispatch("worker", "run_shell", {"command": "ls missing-entry"})
    assert res.ok and res.content.startswith("exit=") and not res.content.startswith("exit=0")


ESCAPED_MARKER = "[harnessie:escaped_descendant held_output_open=true]"

SETSID_SCRIPT = """\
import subprocess, sys
subprocess.Popen([sys.executable, "-c",
                  "import os, time; open('escaped.pid', 'w').write(str(os.getpid())); "
                  "time.sleep(20)"], start_new_session=True)
print("parent done")
"""


def _pid_from(ws, name) -> int:
    end = time.monotonic() + 5
    while time.monotonic() < end:
        text = (ws / name).read_text() if (ws / name).exists() else ""
        if text:
            return int(text)
        time.sleep(0.05)
    raise AssertionError("descendant never recorded its pid")


def test_shell_escaped_descendant_is_signalled_without_changing_exit(
        tmp_path, no_sandbox, monkeypatch):
    monkeypatch.setattr(builtin, "SHELL_DRAIN_GRACE_S", 0.3)
    reg, ws = _registry(tmp_path)
    (ws / "escape.py").write_text(SETSID_SCRIPT)
    try:
        res = reg.dispatch("worker", "run_shell", {"command": "python3 escape.py"})
        assert res.ok and res.refusal is None, res.content
        assert res.content.startswith("exit=0\n")
        assert "parent done" in res.content
        assert res.content.count(ESCAPED_MARKER) == 1
    finally:
        try:
            os.kill(_pid_from(ws, "escaped.pid"), 9)
        except ProcessLookupError:
            pass


def test_shell_in_group_descendant_is_not_reported_escaped(tmp_path, no_sandbox):
    reg, ws = _registry(tmp_path)
    res = reg.dispatch("worker", "run_shell", {"command": _orphan_command(ws)})
    assert res.ok and ESCAPED_MARKER not in res.content
    assert _wait_gone(_orphan_pid(ws))
