"""Ownership lanes: agents own their files, not each other's.

OWNERSHIP.yaml lives at the project root (outside the workspace jail, so no
agent can edit it). Direct writes are checked at dispatch; child processes get
the same denials as a kernel-enforced read-only overlay.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from harness.cli import main
from harness.events import EventLog
from harness.ids import verify_check_digit
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.ownership import OwnershipLedger
from harness.tools import builtin
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


def test_explain_write_names_source_owner_pattern_and_remedy(tmp_path):
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n"
        "  agent:\n"
        "    alice: ['src/*']\n"
        "  collaborative: ['shared/*']\n"
        "  operator: ['config/*']\n"
        "files:\n"
        "  notes/bob.md: bob\n")
    ledger = OwnershipLedger.load(tmp_path / "OWNERSHIP.yaml")

    own = ledger.explain_write("alice", "src/app.py")
    assert own.allowed and own.source == "agent_lane"
    assert own.owner == "alice" and own.pattern == "src/*"

    crossed = ledger.explain_write("bob", "src/app.py")
    assert not crossed.allowed and crossed.source == "agent_lane"
    assert crossed.owner == "alice" and crossed.remedy == "request_change"

    shared = ledger.explain_write("bob", "shared/notes.md")
    assert shared.allowed and shared.source == "collaborative_lane"

    operator = ledger.explain_write("alice", "config/models.yaml")
    assert not operator.allowed and operator.owner == "operator"
    assert operator.remedy == "operator_reassignment"

    claimed = ledger.explain_write("alice", "notes/bob.md")
    assert not claimed.allowed and claimed.source == "first_writer"
    assert claimed.owner == "bob" and claimed.remedy == "request_change"

    claimed_owner = ledger.explain_write("bob", "notes/bob.md")
    assert claimed_owner.allowed and claimed_owner.source == "first_writer"
    assert claimed_owner.owner == "bob"

    unowned = ledger.explain_write("alice", "new.txt")
    assert unowned.allowed and unowned.source == "unowned"

    for decision in (own, crossed, shared, operator, claimed,
                     claimed_owner, unowned):
        assert ledger.check_write(decision.agent, decision.path) == (
            decision.allowed, decision.reason)


def test_cli_ownership_explains_without_mutating_ledger(tmp_path, capsys):
    ledger_path = tmp_path / "OWNERSHIP.yaml"
    ledger_path.write_text(
        "schema_version: 1\n"
        "lanes:\n"
        "  agent:\n"
        "    alice: ['src/*']\n"
        "  collaborative: []\n"
        "  operator: []\n"
        "files: {}\n")
    before = ledger_path.read_bytes()

    code = main(["--root", str(tmp_path), "ownership", "src/app.py",
                 "--agent", "bob"])
    assert code == 0
    out = capsys.readouterr().out
    assert "ownership: DENIED" in out
    assert "owner: alice" in out
    assert "pattern: src/*" in out
    assert "remedy: request_change" in out
    assert ledger_path.read_bytes() == before

    code = main(["--root", str(tmp_path), "ownership", "src/app.py",
                 "--agent", "alice", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["allowed"] is True
    assert payload["source"] == "agent_lane"
    assert payload["owner"] == "alice"
    assert set(payload) == {
        "schema_version", "allowed", "agent", "path", "source", "reason",
        "owner", "pattern", "remedy",
    }
    assert ledger_path.read_bytes() == before


@pytest.mark.parametrize("path", [
    "../outside.txt",
    "/tmp/outside.txt",
    "\\outside.txt",
    " leading.txt",
    "trailing.txt ",
    "control\x1f.txt",
    "delete\x7f.txt",
    ".",
])
def test_cli_ownership_rejects_ambiguous_or_escaping_paths(
        tmp_path, capsys, path):
    assert main(["--root", str(tmp_path), "ownership", path,
                 "--agent", "alice"]) == 2
    assert "PATH must" in capsys.readouterr().err


def test_cli_ownership_rejects_symlink_escape(tmp_path, capsys):
    (tmp_path / "workspace").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "workspace" / "link").symlink_to(outside,
                                                   target_is_directory=True)

    assert main(["--root", str(tmp_path), "ownership", "link/file.txt",
                 "--agent", "alice"]) == 2
    assert "inside workspace" in capsys.readouterr().err


@pytest.mark.parametrize("agent", ["", " ", " alice", "alice ",
                                    "ali\x1fce", "ali\x7fce"])
def test_cli_ownership_rejects_invalid_agent_identity(tmp_path, capsys, agent):
    assert main(["--root", str(tmp_path), "ownership", "inside.txt",
                 "--agent", agent]) == 2
    assert "AGENT must be" in capsys.readouterr().err


def test_cli_ownership_accepts_safe_normalization_without_claiming(
        tmp_path, capsys):
    ledger_path = tmp_path / "OWNERSHIP.yaml"
    ledger_path.write_text("lanes: {}\nfiles: {}\n")
    before = ledger_path.read_bytes()

    assert main(["--root", str(tmp_path), "ownership",
                 "nested/../safe report.txt", "--agent", "alice",
                 "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["allowed"] is True
    assert payload["path"] == "safe report.txt"
    assert payload["source"] == "unowned"
    assert ledger_path.read_bytes() == before


def test_ownership_collision_example_proves_denial():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "examples/ownership-collision/demo.py"],
        cwd=root, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "alice first write: ALLOWED",
        "bob overwrite: DENIED (ownership_denied)",
        "surviving artifact: alice-v1",
        "recorded owner: alice",
        "Golden Rule proof: PASS",
    ]


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


def test_confinement_roots_cover_operator_other_agent_and_claims(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    ledger = OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml",
        agent_lanes={"alice": ["alice/*"], "bob": ["bob/*"]},
        collaborative=["shared/*"],
        operator=["frozen/*"],
        files={"alice-owned.txt": "alice", "bob-owned.txt": "bob"},
    )
    assert set(ledger.confinement_roots("alice", ws)) == {
        (ws / "bob").resolve(),
        (ws / "frozen").resolve(),
        (ws / "bob-owned.txt").resolve(),
    }


def test_root_level_glob_conservatively_protects_whole_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    ledger = OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml", operator=["*.lock"])
    assert ledger.confinement_roots("alice", ws) == (ws.resolve(),)


@pytest.mark.parametrize("pattern", ["/absolute/*", "../escape/*", "bad\\path/*"])
def test_invalid_lane_pattern_refuses_confinement(tmp_path, pattern):
    ws = tmp_path / "ws"
    ws.mkdir()
    ledger = OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml", operator=[pattern])
    with pytest.raises(ValueError, match="ownership lane pattern"):
        ledger.confinement_roots("alice", ws)


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


def test_run_shell_receives_agent_specific_readonly_roots(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    (ws / "frozen").mkdir(parents=True)
    ledger = OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml", operator=["frozen/*"])
    captured = {}

    def fake_wrap(argv, workspace, allow_network=False, readonly_paths=()):
        captured["readonly"] = readonly_paths
        return ["true"]

    monkeypatch.setattr(builtin, "sandbox_wrap", fake_wrap)
    registry = ToolRegistry()
    register_builtin(registry, workspace=ws, ledger=ledger)
    result = registry.dispatch(
        "worker", "run_shell", {"command": "ls"}, agent="alice")
    assert result.ok and "exit=0" in result.content
    assert captured["readonly"] == ((ws / "frozen").resolve(),)


def test_invalid_lane_pattern_blocks_shell_fail_closed(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    ledger = OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml", operator=["../escape/*"])
    registry = ToolRegistry()
    register_builtin(registry, workspace=ws, ledger=ledger)
    result = registry.dispatch(
        "worker", "run_shell", {"command": "ls"}, agent="alice")
    assert result.refusal
    assert result.refusal.error == "sandbox_unavailable"
    assert "ownership lane pattern" in result.refusal.detail


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
