import json
import textwrap

from harness.approval import ApprovalPolicy
from harness.memory import ProjectMemory
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


TRIAGE_NO_APPROVAL = """
name: memory-triage
phases:
  - name: triage
    agent: implementer
    task: "Expire stale fact."
    inject_memory_status: true
    verify:
      max_attempts: 1
      memory_lint: true
"""


SCRIPT = [
    turn_tool("accept_task", {"note": "reviewed"}),
    turn_tool("expire_fact", {"slug": "stale-fact", "reason": "past verify_by"}),
    turn_tool("task_complete", {"report": "done"}),
]


def scaffold(root):
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
    (root / "workflows" / "triage.yaml").write_text(textwrap.dedent(TRIAGE_NO_APPROVAL))
    mem = ProjectMemory(root / "memory")
    mem.save_fact("Stale fact", "past due", source="seed", verify_by="2020-01-01")


def run_with_policy(root, policy_text):
    policy_path = root / "approval-policy.yaml"
    policy_path.write_text(textwrap.dedent(policy_text), encoding="utf-8")
    runner = WorkflowRunner(project_root=root, run_id="approvalrun", echo=False,
                            approval_policy=policy_path)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=list(SCRIPT))
    outcomes = runner.run_workflow(root / "workflows" / "triage.yaml", goal="")
    events = [
        json.loads(line)
        for line in (root / "runs" / "approvalrun" / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    return outcomes, events


def test_approval_policy_allows_tool_for_phase(tmp_path):
    scaffold(tmp_path)
    outcomes, events = run_with_policy(tmp_path, """
        allow:
          - tool: expire_fact
            phase: triage
    """)

    assert [o.status for o in outcomes] == ["passed"]
    assert not (tmp_path / "memory" / "facts" / "stale-fact.md").exists()
    assert (tmp_path / "memory" / "archive" / "stale-fact.md").exists()
    grants = [e for e in events if e["kind"] == "approval_granted"]
    assert grants and grants[0]["source"] == "policy-file"


def test_approval_policy_explicit_deny_wins(tmp_path):
    scaffold(tmp_path)
    outcomes, events = run_with_policy(tmp_path, """
        allow:
          - tool: expire_fact
            phase: triage
        deny:
          - tool: expire_fact
            phase: triage
    """)

    assert [o.status for o in outcomes] == ["passed"]
    assert (tmp_path / "memory" / "facts" / "stale-fact.md").exists()
    denies = [e for e in events if e["kind"] == "approval_denied"]
    assert denies and denies[0]["source"] == "policy-file"


def test_approval_policy_rejects_broad_rule_without_tool(tmp_path):
    path = tmp_path / "approval-policy.yaml"
    path.write_text("allow:\n  - phase: triage\n", encoding="utf-8")

    result = ApprovalPolicy.load(path)

    assert result.problems
    assert not result.decide("triage", "expire_fact", {})
