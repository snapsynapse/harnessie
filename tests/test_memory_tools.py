"""Memory as substrate: provenance-stamped facts, dated staleness, archival-only
expiry behind an approval gate. Nothing deletes; the operator disposes.
"""

import datetime

from harness.events import EventLog
from harness.loop import AgentLoop
from harness.memory import ProjectMemory
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


def today():
    return datetime.date.today().isoformat()


# -- ProjectMemory provenance + expiry ------------------------------------------

def test_save_fact_stamps_verified_and_default_verify_by(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    path = mem.save_fact("Gate catches sabotage", "Verified in run x.",
                         fact_type="lesson", source="run test")
    text = path.read_text()
    assert f"verified: {today()}" in text
    expected = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    assert f"verify_by: {expected}" in text


def test_save_fact_explicit_verify_by(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    path = mem.save_fact("Pin ollama tag", "qwen3.6 for local tier.",
                         fact_type="constraint", source="run test",
                         verify_by="2099-01-01")
    assert "verify_by: 2099-01-01" in path.read_text()


def test_stale_facts_by_date(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    mem.save_fact("Fresh fact", "body", source="s", verify_by="2099-01-01")
    mem.save_fact("Stale fact", "body", source="s", verify_by="2020-01-01")
    stale = mem.stale_facts()
    assert [f["title"] for f in stale] == ["Stale fact"]
    assert stale[0]["verify_by"] == "2020-01-01"


def test_archive_fact_moves_never_deletes(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    mem.save_fact("Old lesson", "body text survives", source="s",
                  verify_by="2020-01-01")
    archived = mem.archive_fact("old-lesson", reason="superseded by run y")
    assert archived.exists()
    assert archived.parent.name == "archive"
    assert "body text survives" in archived.read_text()          # nothing lost
    assert f"archived: {today()}" in archived.read_text()
    assert "superseded by run y" in archived.read_text()
    assert not (tmp_path / "memory" / "facts" / "old-lesson.md").exists()
    assert "old-lesson" not in mem.index_path.read_text()        # index pruned


def test_memory_lint_flags_inconsistency(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    mem.save_fact("Real fact", "body", source="s")
    # index points at a fact that does not exist
    mem.index_path.write_text(mem.index_path.read_text()
                              + "- [Ghost](facts/ghost.md) `lesson`\n")
    # fact on disk missing from the index
    (mem.facts_dir / "orphan.md").write_text(
        "---\nname: orphan\ntype: lesson\nsource: s\ndate: 2026-01-01\n---\n\nx\n")
    problems = mem.lint()
    assert any("ghost" in p for p in problems)
    assert any("orphan" in p for p in problems)
    assert not any("real-fact" in p for p in problems)


# -- tool layer: auto-stamped provenance, approval-gated expiry -------------------

def make_loop(tmp_path, script, consent_required=False, approval=None):
    reg = ToolRegistry()
    if approval is not None:
        reg.approval_handler = approval
    mem = ProjectMemory(tmp_path / "memory")
    events = EventLog(tmp_path / "run", echo=False)
    register_builtin(reg, workspace=tmp_path / "ws", memory=mem,
                     events=events, provenance="run testrun")
    (tmp_path / "ws").mkdir(exist_ok=True)
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    loop = AgentLoop(role="worker", model=model, registry=reg, events=events,
                     max_steps=8, agent_name="triage",
                     consent_required=consent_required)
    return loop, mem


def test_save_fact_tool_autostamps_source(tmp_path):
    loop, mem = make_loop(tmp_path, [
        turn_tool("save_fact", {"title": "Lesson from run",
                                "body": "verifier caught a fake pass",
                                "fact_type": "lesson",
                                "source": "agent-claimed-source-ignored"}),
        turn_tool("task_complete", {"report": "saved"}),
    ])
    res = loop.run("system", "triage")
    assert res.ok
    text = (tmp_path / "memory" / "facts" / "lesson-from-run.md").read_text()
    assert "run testrun" in text and "agent triage" in text
    assert "agent-claimed-source-ignored" not in text   # provenance is stamped, not claimed


def test_save_fact_is_consent_locked(tmp_path):
    loop, _ = make_loop(tmp_path, [
        turn_tool("save_fact", {"title": "Sneak", "body": "x"}),
        turn_tool("task_complete", {"report": "tried"}),
    ], consent_required=True)
    res = loop.run("system", "offer")
    assert res.ok
    assert not (tmp_path / "memory" / "facts" / "sneak.md").exists()


def test_expire_fact_denied_without_approval(tmp_path):
    loop, mem = make_loop(tmp_path, [
        turn_tool("expire_fact", {"slug": "stale-one", "reason": "old"}),
        turn_tool("task_complete", {"report": "proposed expiry"}),
    ])
    mem.save_fact("Stale one", "body", source="s", verify_by="2020-01-01")
    res = loop.run("system", "triage")
    assert res.ok
    assert (tmp_path / "memory" / "facts" / "stale-one.md").exists()   # fail closed


def test_expire_fact_with_approval_archives_and_logs(tmp_path):
    import json
    loop, mem = make_loop(tmp_path, [
        turn_tool("expire_fact", {"slug": "stale-one", "reason": "past verify_by"}),
        turn_tool("task_complete", {"report": "expired"}),
    ], approval=lambda tool, args: True)
    mem.save_fact("Stale one", "body", source="s", verify_by="2020-01-01")
    res = loop.run("system", "triage")
    assert res.ok
    assert not (tmp_path / "memory" / "facts" / "stale-one.md").exists()
    assert (tmp_path / "memory" / "archive" / "stale-one.md").exists()
    kinds = [json.loads(l)["kind"] for l in
             (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    assert "fact_expired" in kinds
