"""No-opt-in artifact and governance guards for AIDR-0009.

These pass today and must keep passing after the features land: a workflow
that does not opt in emits no bid or observer events, and observer output
never joins the governance timeline. They are deliberately outside the
strict-xfail files, because a guard that is expected to fail is not a guard.
"""

from __future__ import annotations

import json
import textwrap

from harness import sandbox
from harness.audit import GOVERNANCE_KINDS
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


def scaffold(root):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\n")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\n")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\n")
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
    (root / "workflows" / "wf.yaml").write_text(textwrap.dedent("""
        name: wf
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan: {goal}"
          - name: implement
            agent: implementer
            task: "Do: {plan}"
            verify:
              max_attempts: 1
              checks:
                - name: exists
                  command: python3 -c "import pathlib,sys; sys.exit(0 if pathlib.Path('out.txt').exists() else 1)"
              verifier: code-verifier
              criteria: out.txt exists
    """))


SCRIPT = [
    turn_tool("task_complete", {"report": "PLAN"}),
    turn_tool("accept_task", {"note": "ok"}),
    turn_tool("write_file", {"path": "out.txt", "content": "x"}),
    turn_tool("task_complete", {"report": "wrote"}),
    turn_tool("task_complete", {"report": '{"passed": true, "reasons": "ok"}'}),
]


def test_workflow_without_opt_in_emits_no_bid_or_observer_artifacts(
        tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="plain", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=list(SCRIPT))
    statuses = [o.status for o in
                runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")]
    assert statuses == ["passed", "passed"]

    path = tmp_path / "runs" / "plain" / "events.jsonl"
    kinds = {json.loads(l)["kind"] for l in path.read_text().splitlines() if l.strip()}
    assert not {k for k in kinds if k.startswith("bid_")}
    assert "observation" not in kinds
    assert not (tmp_path / "runs" / "plain" / "observer").exists()


def test_observer_output_kinds_never_join_the_governance_timeline():
    assert "observation" not in GOVERNANCE_KINDS
    assert "narration" not in GOVERNANCE_KINDS
