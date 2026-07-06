from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.routing import Budget
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def make_loop(tmp_path, role, script, budget=None, max_steps=10):
    reg = ToolRegistry()
    register_builtin(reg, workspace=tmp_path / "ws")
    (tmp_path / "ws").mkdir(exist_ok=True)
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    events = EventLog(tmp_path / "run", echo=False)
    return AgentLoop(role=role, model=model, registry=reg, events=events,
                     budget=budget, max_steps=max_steps), model


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


def test_happy_path_write_then_complete(tmp_path):
    loop, _ = make_loop(tmp_path, "worker", [
        turn_tool("write_file", {"path": "out.txt", "content": "hello"}),
        turn_tool("task_complete", {"report": "wrote out.txt"}),
    ])
    res = loop.run("system", "write hello to out.txt")
    assert res.ok and res.stop == "complete"
    assert (tmp_path / "ws" / "out.txt").read_text() == "hello"


def test_permission_denied_surfaces_not_crashes(tmp_path):
    loop, _ = make_loop(tmp_path, "verifier", [
        turn_tool("write_file", {"path": "x.txt", "content": "sneaky"}),
        turn_tool("task_complete", {"report": "gave up"}),
    ])
    res = loop.run("system", "verify things")
    assert res.ok                                   # loop survived
    assert not (tmp_path / "ws" / "x.txt").exists()  # write never happened


def test_no_action_stops_after_nudge(tmp_path):
    loop, model = make_loop(tmp_path, "worker", [
        AssistantTurn(content="thinking out loud..."),
        AssistantTurn(content="still just talking"),
    ])
    res = loop.run("system", "do something")
    assert res.stop == "no_action"
    # the nudge message was injected between the two idle turns
    assert any("task_complete" in m.content for m in model.calls[1]["messages"]
               if m.role == "user")


def test_stuck_detector(tmp_path):
    bad = turn_tool("read_file", {"path": "does-not-exist.txt"})
    loop, _ = make_loop(tmp_path, "worker", [bad, bad, bad, bad])
    res = loop.run("system", "read the file")
    assert res.stop == "stuck"


def test_budget_stops_loop(tmp_path):
    spent = Budget(max_usd=100, max_tokens=10)   # 10-token ceiling
    expensive = AssistantTurn(content="", stop_reason="tool_use",
                              tool_calls=[ToolCall("c", "list_files", {})],
                              input_tokens=50, output_tokens=50)
    loop, _ = make_loop(tmp_path, "worker",
                        [expensive, expensive, expensive], budget=spent)
    res = loop.run("system", "task")
    assert res.stop == "budget"


def test_refusal_surfaces_immediately(tmp_path):
    ref = AssistantTurn(content="cannot assist with this", stop_reason="refusal")
    loop, _ = make_loop(tmp_path, "worker", [ref])
    res = loop.run("system", "task")
    assert res.stop == "refusal"    # gate/operator decides next, never silent retry


def test_model_error_twice_stops(tmp_path):
    err = AssistantTurn(content="provider_error 500", stop_reason="error")
    loop, _ = make_loop(tmp_path, "worker", [err, err])
    res = loop.run("system", "task")
    assert res.stop == "model_error"


def test_max_steps(tmp_path):
    chatter = turn_tool("list_files", {})
    loop, _ = make_loop(tmp_path, "worker", [chatter] * 20, max_steps=5)
    res = loop.run("system", "task")
    assert res.stop == "max_steps"


def test_stuck_detector_counts_ok_true_refusals(tmp_path):
    # run_shell denials keep ok=True, but three identical ones are not progress
    deny = turn_tool("run_shell", {"command": "curl https://example.com/"})
    loop, _ = make_loop(tmp_path, "worker", [deny, deny, deny, deny])
    res = loop.run("system", "fetch the page")
    assert res.stop == "stuck"


def test_refusal_streak_broken_by_successful_call(tmp_path):
    deny = turn_tool("run_shell", {"command": "curl https://example.com/"})
    loop, _ = make_loop(tmp_path, "worker", [
        deny, deny, turn_tool("list_files", {}), deny,
        turn_tool("task_complete", {"report": "listed instead"}),
    ])
    res = loop.run("system", "task")
    assert res.stop == "complete"


def test_refusal_event_carries_detail_and_why(tmp_path):
    import json
    deny = turn_tool("run_shell", {"command": "curl https://example.com/"})
    loop, _ = make_loop(tmp_path, "worker", [
        deny, turn_tool("task_complete", {"report": "gave up"}),
    ])
    res = loop.run("system", "task")
    assert res.ok
    events = [json.loads(line) for line in
              (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    refusals = [e for e in events if e.get("kind") == "refusal"]
    assert refusals
    assert refusals[0]["error"] == "command_not_allowlisted"
    assert refusals[0]["detail"] and refusals[0]["why"]
