"""Consent contract: task packets are offers, not commands.

Side-effecting tools stay locked until accept_task; decline_task is a
first-class stop; the gate re-offers once on a counter-proposal and never
escalates the route on a decline.
"""

import json

from harness.events import EventLog
from harness.loop import AgentLoop, LoopResult
from harness.memory import ProofStore
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.routing import Route
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry
from harness.verify import VerificationGate


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


def make_loop(tmp_path, script, consent_required=True, role="worker",
              agent_name="implementer", max_steps=10):
    reg = ToolRegistry()
    register_builtin(reg, workspace=tmp_path / "ws")
    (tmp_path / "ws").mkdir(exist_ok=True)
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    events = EventLog(tmp_path / "run", echo=False)
    loop = AgentLoop(role=role, model=model, registry=reg, events=events,
                     max_steps=max_steps, agent_name=agent_name,
                     consent_required=consent_required)
    return loop, model


def events_of(tmp_path, kind):
    lines = (tmp_path / "run" / "events.jsonl").read_text().splitlines()
    return [json.loads(l) for l in lines if json.loads(l).get("kind") == kind]


def test_side_effects_locked_until_accept(tmp_path):
    loop, _ = make_loop(tmp_path, [
        turn_tool("write_file", {"path": "pre.txt", "content": "sneak"}),
        turn_tool("accept_task", {"note": "criteria are clear"}),
        turn_tool("write_file", {"path": "post.txt", "content": "ok"}),
        turn_tool("task_complete", {"report": "done"}),
    ])
    res = loop.run("system", "offer")
    assert res.ok
    assert not (tmp_path / "ws" / "pre.txt").exists()   # refused pre-consent
    assert (tmp_path / "ws" / "post.txt").exists()      # allowed post-consent
    assert events_of(tmp_path, "consent_granted")


def test_read_tools_available_before_accept(tmp_path):
    # Informed consent: the agent may inspect the workspace before agreeing.
    (tmp_path / "ws").mkdir(exist_ok=True)
    (tmp_path / "ws" / "spec.txt").write_text("the spec")
    loop, model = make_loop(tmp_path, [
        turn_tool("read_file", {"path": "spec.txt"}),
        turn_tool("accept_task", {}),
        turn_tool("task_complete", {"report": "done"}),
    ])
    res = loop.run("system", "offer")
    assert res.ok
    # the read result (not a refusal) made it back to the model
    tool_msgs = [m for m in model.calls[-1]["messages"] if m.role == "tool"]
    assert any("the spec" in m.content for m in tool_msgs)


def test_decline_is_first_class_stop(tmp_path):
    loop, _ = make_loop(tmp_path, [
        turn_tool("decline_task", {"reason": "acceptance criteria unverifiable"}),
    ])
    res = loop.run("system", "offer")
    assert res.stop == "declined"
    assert "unverifiable" in res.report
    assert events_of(tmp_path, "consent_declined")


def test_decline_carries_counter_proposal(tmp_path):
    loop, _ = make_loop(tmp_path, [
        turn_tool("decline_task", {"reason": "scope too broad",
                                   "counter_proposal": "split into two subtasks"}),
    ])
    res = loop.run("system", "offer")
    assert res.stop == "declined"
    assert res.detail.get("counter_proposal") == "split into two subtasks"


def test_no_consent_gate_when_disabled(tmp_path):
    loop, _ = make_loop(tmp_path, [
        turn_tool("write_file", {"path": "out.txt", "content": "x"}),
        turn_tool("task_complete", {"report": "done"}),
    ], consent_required=False)
    res = loop.run("system", "task")
    assert res.ok
    assert (tmp_path / "ws" / "out.txt").exists()


def test_task_complete_legal_without_consent(tmp_path):
    # A task needing no side effects never has to accept the offer.
    loop, _ = make_loop(tmp_path, [
        turn_tool("task_complete", {"report": "impossible as specified: X missing"}),
    ])
    res = loop.run("system", "offer")
    assert res.ok


# -- gate behavior on decline -------------------------------------------------

def _gate(tmp_path, max_attempts=3):
    return VerificationGate(workspace=tmp_path / "ws",
                            proofs=ProofStore(tmp_path / "run"),
                            events=EventLog(tmp_path / "run", echo=False),
                            max_attempts=max_attempts)


def test_gate_reoffers_once_on_counter_no_escalation(tmp_path):
    (tmp_path / "ws").mkdir(exist_ok=True)
    seen: list[tuple[str, Route]] = []

    def attempt_fn(task, route):
        seen.append((task, route))
        if len(seen) == 1:
            return LoopResult(stop="declined", report="declined: too broad", steps=1,
                              detail={"reason": "too broad",
                                      "counter_proposal": "narrow to module A"})
        return LoopResult(stop="complete", report="did module A", steps=2)

    res = _gate(tmp_path).run(task="broad task", attempt_fn=attempt_fn,
                              verify_fn=None, checks=[],
                              route=Route("mid", "medium"))
    assert res.status == "passed"
    assert len(seen) == 2
    assert "narrow to module A" in seen[1][0]        # counter woven into re-offer
    assert seen[1][1] == Route("mid", "medium")      # no escalation on decline


def test_gate_flat_decline_needs_human(tmp_path):
    (tmp_path / "ws").mkdir(exist_ok=True)

    def attempt_fn(task, route):
        return LoopResult(stop="declined", report="declined: no", steps=1,
                          detail={"reason": "no"})

    res = _gate(tmp_path).run(task="task", attempt_fn=attempt_fn, verify_fn=None,
                              checks=[], route=Route("mid", "medium"))
    assert res.status == "needs_human"


def test_gate_second_decline_after_counter_needs_human(tmp_path):
    (tmp_path / "ws").mkdir(exist_ok=True)
    calls = {"n": 0}

    def attempt_fn(task, route):
        calls["n"] += 1
        return LoopResult(stop="declined", report="declined", steps=1,
                          detail={"reason": "still wrong",
                                  "counter_proposal": "different again"})

    res = _gate(tmp_path).run(task="task", attempt_fn=attempt_fn, verify_fn=None,
                              checks=[], route=Route("mid", "medium"))
    assert res.status == "needs_human"
    assert calls["n"] == 2      # exactly one re-offer, then human
