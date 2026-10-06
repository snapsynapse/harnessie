"""Harnessie tools whose effects land in a remote (Harbor-shaped) environment."""

import asyncio
import importlib.util
import json
import sys
import threading
from pathlib import Path, PurePosixPath

import pytest

from harness.atif import export_dir
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.tools.registry import ToolRegistry

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "harbor-agent"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve annotations through sys.modules[cls.__module__].
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tools = _load("harbor_tools")


class _Result:
    def __init__(self, stdout="", stderr="", return_code=0):
        self.stdout, self.stderr, self.return_code = stdout, stderr, return_code


class FakeEnvironment:
    """A sandbox with a tiny in-memory filesystem under /app."""

    def __init__(self):
        self.files = {"/app/a.txt": "alpha\n"}
        self.commands = []

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        self.commands.append((command, cwd))
        if command.startswith("cat -- "):
            path = command.split("-- ", 1)[1].strip("'")
            if path in self.files:
                return _Result(stdout=self.files[path])
            return _Result(stderr=f"cat: {path}: No such file\n", return_code=1)
        if command.startswith("ls -1Ap -- "):
            path = command.split("-- ", 1)[1].strip("'")
            names = sorted(PurePosixPath(p).name for p in self.files
                           if str(PurePosixPath(p).parent) == path)
            return _Result(stdout="\n".join(names) + "\n")
        if command.startswith("mkdir -p -- "):
            return _Result()
        if command.startswith("python3 -c "):
            return _Result(stdout="42\n")
        return _Result(stdout=f"ran: {command}\n")

    async def upload_file(self, source_path, target_path):
        self.files[target_path] = Path(source_path).read_text(encoding="utf-8")


class LoopThread:
    """An asyncio loop in a background thread, as Harbor's would be."""

    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        return self.loop

    def __exit__(self, *exc):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        self.loop.close()


def _registry(env, loop):
    reg = ToolRegistry()
    bridge = tools.SandboxBridge(environment=env, loop=loop, workdir="/app", timeout_sec=5)
    tools.register_remote_tools(reg, bridge)
    return reg, bridge


def test_jail_keeps_paths_inside_the_remote_workdir():
    assert tools.jail("/app", "notes.md") == "/app/notes.md"
    assert tools.jail("/app", "sub/x.py") == "/app/sub/x.py"
    assert tools.jail("/app", "/app/inner") == "/app/inner"
    assert tools.jail("/app", "") == "/app"
    for bad in ("../etc/passwd", "a/../../b", "/etc/passwd", "/approot"):
        with pytest.raises(tools.Refusal_) as excinfo:
            tools.jail("/app", bad)
        assert excinfo.value.refusal.error == "workspace_jail_escape"


def test_read_list_write_land_in_the_environment_not_the_host(tmp_path):
    env = FakeEnvironment()
    with LoopThread() as loop:
        reg, bridge = _registry(env, loop)
        assert reg.dispatch("worker", "read_file", {"path": "a.txt"}).content == "exit=0\nalpha\n"
        listing = reg.dispatch("worker", "list_files", {}).content
        assert "a.txt" in listing
        out = reg.dispatch("worker", "write_file",
                           {"path": "out/answer.txt", "content": "42\n"}, agent="implementer")
        assert out.ok and out.content.startswith("wrote /app/out/answer.txt")
        assert env.files["/app/out/answer.txt"] == "42\n"
        # shlex.quote leaves a plain path bare and quotes one with specials.
        assert any(c in ("mkdir -p -- /app/out", "mkdir -p -- '/app/out'")
                   for c, _ in env.commands)
        assert all(cwd == "/app" for _, cwd in env.commands)
    assert not (tmp_path / "out").exists()
    assert not Path("out").exists()


def test_run_shell_keeps_the_builtin_allowlist_and_argument_jail():
    env = FakeEnvironment()
    with LoopThread() as loop:
        reg, _ = _registry(env, loop)
        refused = reg.dispatch("worker", "run_shell", {"command": "bash -c id"})
        assert refused.refusal is not None
        assert refused.refusal.error == "command_not_allowlisted"
        escape = reg.dispatch("worker", "run_shell", {"command": "cat ../secret"})
        assert escape.refusal.error == "argument_jail_escape"
        ok = reg.dispatch("worker", "run_shell",
                          {"command": "python3 -c 'print(6*7)'"})
        assert ok.content == "exit=0\n42\n"
        assert env.commands[-1][0] == "python3 -c 'print(6*7)'"
        assert reg.dispatch("worker", "read_file", {"path": "../x"}).refusal.error == \
            "workspace_jail_escape"


def test_role_grants_apply_to_remote_tools():
    env = FakeEnvironment()
    with LoopThread() as loop:
        reg, _ = _registry(env, loop)
        from harness.tools.registry import PermissionDenied
        with pytest.raises(PermissionDenied):
            reg.dispatch("verifier", "write_file", {"path": "x", "content": "y"})


def _call(idx, name, **args):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=f"c{idx}", name=name, arguments=args)],
                         input_tokens=50, output_tokens=5)


def test_agent_loop_drives_remote_tools_and_exports_atif(tmp_path):
    env = FakeEnvironment()
    run_dir = tmp_path / "harnessie"
    events = EventLog(run_dir, echo=False)
    events.emit("workflow_start", name="harbor-task", run_id="T1",
                goal="Create hello.txt containing Hello, world!")
    with LoopThread() as loop:
        reg, bridge = _registry(env, loop)
        model = MockModel(ModelSpec(name="harbor", provider="mock", model_id="mock"),
                          script=[
                              _call(1, "bash", command="ls"),
                              _call(2, "list_files"),
                              _call(3, "write_file", path="hello.txt",
                                    content="Hello, world!\n"),
                              _call(4, "run_shell", command="cat hello.txt"),
                              _call(5, "task_complete", report="wrote hello.txt"),
                          ])
        result = AgentLoop(role="worker", model=model, registry=reg, events=events,
                           max_steps=8, agent_name="implementer").run("system", "task")
        events.close()
    assert result.stop == "complete"
    assert env.files["/app/hello.txt"] == "Hello, world!\n"
    doc = export_dir(run_dir)
    assert doc["steps"][0]["source"] == "user"
    agent_steps = [s for s in doc["steps"] if s["source"] == "agent"]
    assert [s["tool_calls"][0]["function_name"] for s in agent_steps] == [
        "bash", "list_files", "write_file", "run_shell", "task_complete"]
    assert agent_steps[0]["observation"]["results"][0]["extra"]["refusal"]["error"] == \
        "action_unsupported"
    assert doc["final_metrics"]["total_completion_tokens"] == 25


def test_cancel_turns_the_host_timeout_into_a_recorded_stop(tmp_path):
    env = FakeEnvironment()
    run_dir = tmp_path / "harnessie"
    events = EventLog(run_dir, echo=False)
    inner = MockModel(ModelSpec(name="harbor", provider="mock", model_id="mock"),
                      script=[_call(1, "list_files"), _call(2, "list_files"),
                              _call(3, "list_files"), _call(4, "task_complete", report="x")])
    model = tools.CancellableModel(inner)
    with LoopThread() as loop:
        reg, _ = _registry(env, loop)
        # Cancel after the first call: a tool fn is the handy place to do it.
        original = reg.tools["list_files"].fn
        def listing_then_cancel(path="."):
            model.cancel()
            return original(path)
        reg.tools["list_files"].fn = listing_then_cancel
        result = AgentLoop(role="worker", model=model, registry=reg, events=events,
                           max_steps=8, agent_name="implementer").run("system", "task")
        events.close()
    assert result.stop == "model_error"
    assert "harness_cancelled" in result.report
    assert len(inner.calls) == 1, "no endpoint call after cancel"
    doc = export_dir(run_dir)
    assert doc["final_metrics"]["extra"]["loops"][0]["stop"] == "model_error"


def test_resolve_endpoint_prefers_explicit_then_harnessie_then_openai_vars():
    assert tools.resolve_endpoint("http://p:8100", "K", env={}) == ("http://p:8100/v1", "K")
    assert tools.resolve_endpoint(env={"HARNESSIE_HARBOR_BASE_URL": "http://p:8100/v1/",
                                       "HARNESSIE_HARBOR_API_KEY": "s"}) == \
        ("http://p:8100/v1", "HARNESSIE_HARBOR_API_KEY")
    assert tools.resolve_endpoint(env={"OPENAI_BASE_URL": "http://o/v1",
                                       "OPENAI_API_KEY": "k"}) == ("http://o/v1", "OPENAI_API_KEY")
    with pytest.raises(ValueError):
        tools.resolve_endpoint(env={})


def test_harbor_agent_loads_where_harbor_is_installed():
    pytest.importorskip("harbor.agents.base")
    sys.path.insert(0, str(EXAMPLE))
    try:
        module = _load("harnessie_harbor_agent")
    finally:
        sys.path.remove(str(EXAMPLE))
    assert module.HarnessieAgent.name() == "harnessie"
    assert module.HarnessieAgent.capabilities.atif is True
