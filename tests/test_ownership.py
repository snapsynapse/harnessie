"""Ownership lanes: agents own their files, not each other's.

OWNERSHIP.yaml lives at the project root (outside the workspace jail, so no
agent can edit it). Enforcement happens at write_file dispatch, fail closed.
"""

import json
import re

from harness.events import EventLog
from harness.ids import verify_check_digit
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.ownership import OwnershipLedger
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


# -- ledger unit behavior ------------------------------------------------------

def test_first_writer_owns(tmp_path):
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    ok, _ = led.check_write("alice", "new.txt")
    assert ok
    led.claim("alice", "new.txt")
    assert led.owner_of("new.txt") == "alice"
    ok, reason = led.check_write("bob", "new.txt")
    assert not ok and "alice" in reason


def test_owner_may_rewrite_own_file(tmp_path):
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    led.claim("alice", "a.txt")
    ok, _ = led.check_write("alice", "a.txt")
    assert ok


def test_operator_lane_denies_all_agents(tmp_path):
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n  operator:\n    - 'frozen/*'\n")
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    ok, reason = led.check_write("alice", "frozen/config.txt")
    assert not ok and "operator" in reason.lower()


def test_agent_lane_grants_and_denies(tmp_path):
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n  agent:\n    alice:\n      - 'src/*'\n")
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    assert led.check_write("alice", "src/mod.py")[0]
    assert not led.check_write("bob", "src/mod.py")[0]


def test_collaborative_lane_allows_everyone(tmp_path):
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n  collaborative:\n    - 'shared/*'\n")
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    assert led.check_write("alice", "shared/notes.md")[0]
    assert led.check_write("bob", "shared/notes.md")[0]
    # collaborative writes never auto-claim exclusive ownership
    led.claim("alice", "shared/notes.md")
    assert led.check_write("bob", "shared/notes.md")[0]


def test_operator_lane_overrides_auto_claim(tmp_path):
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    led.claim("alice", "frozen/x.txt")
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n  operator:\n    - 'frozen/*'\n"
        "files:\n  frozen/x.txt: alice\n")
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    assert not led.check_write("alice", "frozen/x.txt")[0]   # operator wins


def test_ledger_persists_round_trip(tmp_path):
    led = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    led.claim("alice", "a.txt")
    led2 = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    assert led2.owner_of("a.txt") == "alice"


def test_isolated_view_enforces_declared_lanes_without_auto_claims(tmp_path):
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n"
        "  agent:\n"
        "    alice: ['src/*']\n"
        "  collaborative: ['shared/*']\n"
        "  operator: ['frozen/*']\n"
        "files:\n"
        "  ordinary.txt: bob\n")
    view = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml").isolated_view()
    assert view.check_write("alice", "src/a.py")[0]
    assert not view.check_write("bob", "src/a.py")[0]
    assert not view.check_write("alice", "frozen/config.txt")[0]
    assert view.check_write("alice", "shared/note.md")[0]
    assert view.check_write("alice", "ordinary.txt")[0]
    assert view.claim("alice", "ordinary.txt") is False


# -- tool-layer enforcement ----------------------------------------------------

def make_agent_loop(tmp_path, agent, script):
    reg = ToolRegistry()
    ledger = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")
    events = EventLog(tmp_path / "run", echo=False)
    register_builtin(reg, workspace=tmp_path / "ws", ledger=ledger, events=events)
    (tmp_path / "ws").mkdir(exist_ok=True)
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    return AgentLoop(role="worker", model=model, registry=reg, events=events,
                     max_steps=10, agent_name=agent)


def events_of(tmp_path, kind):
    lines = (tmp_path / "run" / "events.jsonl").read_text().splitlines()
    return [json.loads(l) for l in lines if json.loads(l).get("kind") == kind]


def test_cross_agent_write_denied_at_dispatch(tmp_path):
    res = make_agent_loop(tmp_path, "alice", [
        turn_tool("write_file", {"path": "a.txt", "content": "alice-v1"}),
        turn_tool("task_complete", {"report": "done"}),
    ]).run("system", "task")
    assert res.ok
    res = make_agent_loop(tmp_path, "bob", [
        turn_tool("write_file", {"path": "a.txt", "content": "bob-overwrite"}),
        turn_tool("task_complete", {"report": "done"}),
    ]).run("system", "task")
    assert res.ok
    assert (tmp_path / "ws" / "a.txt").read_text() == "alice-v1"
    assert events_of(tmp_path, "ownership_claimed")
    assert events_of(tmp_path, "ownership_denied")


def test_request_change_recorded_not_granted(tmp_path):
    make_agent_loop(tmp_path, "alice", [
        turn_tool("write_file", {"path": "a.txt", "content": "alice-v1"}),
        turn_tool("task_complete", {"report": "done"}),
    ]).run("system", "task")
    res = make_agent_loop(tmp_path, "bob", [
        turn_tool("request_change", {"path": "a.txt",
                                     "description": "typo in line 1"}),
        turn_tool("write_file", {"path": "a.txt", "content": "bob-sneak"}),
        turn_tool("task_complete", {"report": "done"}),
    ]).run("system", "task")
    assert res.ok
    reqs = events_of(tmp_path, "change_request")
    assert reqs and reqs[0]["path"] == "a.txt"
    assert re.match(r"^CR-[0-9ACDFGHJKMNPRUWY]{6}$", reqs[0]["ref"])
    assert verify_check_digit(reqs[0]["ref"].removeprefix("CR-"))
    # the request records intent; it grants nothing
    assert (tmp_path / "ws" / "a.txt").read_text() == "alice-v1"
