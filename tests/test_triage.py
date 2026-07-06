"""Memory-triage workflow: the maintenance-agent pattern under harness
enforcement. Harvest run outcomes into facts, surface stale facts, apply
disposal only under recorded approval — propose-only otherwise. Operator
actions (approvals, arbitrations) land in the same hash-chained audit stream
as agent actions.
"""

import json
import textwrap

from harness.audit import verify_chain
from harness.memory import ProjectMemory
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


TRIAGE_WF = """
name: memory-triage
phases:
  - name: triage
    agent: implementer
    task: |
      Maintain project memory. Review the injected memory status; save new
      facts from recent run outcomes, and expire facts past verify_by.
    inject_memory_status: true
    approve_tools: [expire_fact]
    verify:
      max_attempts: 1
      memory_lint: true
  - name: summary
    agent: orchestrator
    task: "Summarize triage: {triage}"
"""

TRIAGE_WF_NO_APPROVAL = TRIAGE_WF.replace("    approve_tools: [expire_fact]\n", "")


def scaffold(root, workflow=TRIAGE_WF):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock
        routing:
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    (root / "workflows" / "triage.yaml").write_text(textwrap.dedent(workflow))
    mem = ProjectMemory(root / "memory")
    mem.save_fact("Fresh fact", "still good", source="seed",
                  verify_by="2099-01-01")
    mem.save_fact("Stale fact", "past due", source="seed",
                  verify_by="2020-01-01")
    return mem


def run(root, run_id, script):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=script)
    outcomes = runner.run_workflow(root / "workflows" / "triage.yaml", goal="")
    return runner, outcomes


GOLDEN_SCRIPT = [
    turn_tool("accept_task", {"note": "memory status reviewed"}),
    turn_tool("save_fact", {"title": "Run lesson", "body": "gate caught a fake",
                            "fact_type": "lesson"}),
    turn_tool("expire_fact", {"slug": "stale-fact", "reason": "past verify_by"}),
    turn_tool("task_complete", {"report": "saved 1, expired 1"}),
    turn_tool("task_complete", {"report": "TRIAGE SUMMARY: 1 saved, 1 archived"}),
]


def events_of(root, run_id):
    lines = (root / "runs" / run_id / "events.jsonl").read_text().splitlines()
    return [json.loads(l) for l in lines]


def test_triage_applies_under_recorded_approval(tmp_path):
    scaffold(tmp_path)
    runner, outcomes = run(tmp_path, "t1", list(GOLDEN_SCRIPT))
    assert [o.status for o in outcomes] == ["passed", "passed"]
    # new fact saved with provenance; stale fact archived, not deleted
    saved = tmp_path / "memory" / "facts" / "run-lesson.md"
    assert saved.exists() and "run t1" in saved.read_text()
    assert not (tmp_path / "memory" / "facts" / "stale-fact.md").exists()
    assert (tmp_path / "memory" / "archive" / "stale-fact.md").exists()
    # operator pre-approval is in the audit stream, and the chain verifies
    kinds = [e["kind"] for e in events_of(tmp_path, "t1")]
    assert "approval_granted" in kinds
    assert "fact_saved" in kinds and "fact_expired" in kinds
    assert verify_chain(tmp_path / "runs" / "t1")["ok"]
    granted = [e for e in events_of(tmp_path, "t1")
               if e["kind"] == "approval_granted"]
    assert granted[0]["source"] == "workflow-config"


def test_triage_headless_is_propose_only(tmp_path):
    scaffold(tmp_path, workflow=TRIAGE_WF_NO_APPROVAL)
    runner, outcomes = run(tmp_path, "t2", list(GOLDEN_SCRIPT))
    assert [o.status for o in outcomes] == ["passed", "passed"]
    # expiry was refused (fail closed); the fact is untouched
    assert (tmp_path / "memory" / "facts" / "stale-fact.md").exists()
    assert not (tmp_path / "memory" / "archive" / "stale-fact.md").exists()
    kinds = [e["kind"] for e in events_of(tmp_path, "t2")]
    assert "approval_denied" in kinds
    assert "approval_granted" not in kinds


def test_inject_memory_status_reaches_the_agent(tmp_path):
    scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="t3", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      script=list(GOLDEN_SCRIPT))
    runner._models["mid"] = brain
    runner.run_workflow(tmp_path / "workflows" / "triage.yaml", goal="")
    task_msg = brain.calls[0]["messages"][1].content
    assert "stale-fact" in task_msg          # stale facts surfaced by slug
    assert "2020-01-01" in task_msg          # with their verify_by dates
    assert "Fresh fact" in task_msg          # index included


def test_memory_lint_failure_fails_the_gate(tmp_path):
    scaffold(tmp_path)
    # corrupt the index so memory_lint must fail the phase
    idx = tmp_path / "memory" / "MEMORY.md"
    idx.write_text(idx.read_text() + "- [Ghost](facts/ghost.md) `lesson`\n")
    script = [
        turn_tool("accept_task", {}),
        turn_tool("task_complete", {"report": "did nothing"}),
    ]
    _, outcomes = run(tmp_path, "t4", script)
    assert outcomes[0].status == "needs_human"
    assert "ghost" in outcomes[0].report


def test_approve_tools_scope_is_per_phase(tmp_path):
    # a tool approved for the triage phase is NOT approved for other phases
    wf = TRIAGE_WF.replace(
        'task: "Summarize triage: {triage}"',
        'task: "Summarize triage: {triage}"\n    consent: false')
    scaffold(tmp_path, workflow=wf)
    runner, _ = run(tmp_path, "t5", list(GOLDEN_SCRIPT))
    # after the workflow, the registry's approval handler must be back to
    # default-deny (fail closed), not left granting expire_fact forever
    assert runner.registry.approval_handler("expire_fact", {}) is False
