"""End-to-end: a scripted mock brain drives a full plan -> implement (gated) ->
integrate workflow, then the run resumes from its journal without re-running."""

import textwrap

from harness import sandbox
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


def scaffold_project(root):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan and integrate.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo the task.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge it.")
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
    (root / "workflows" / "mini.yaml").write_text(textwrap.dedent("""
        name: mini
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {goal}"
          - name: implement
            agent: implementer
            task: "Do this plan: {plan}"
            verify:
              max_attempts: 2
              checks:
                - name: file-exists
                  command: python3 -c "import pathlib,sys; sys.exit(0 if pathlib.Path('greeting.txt').exists() else 1)"
              verifier: code-verifier
              criteria: greeting.txt exists and contains hello
          - name: integrate
            agent: orchestrator
            task: "Summarize: {implement}"
    """))


SCRIPT = [
    # plan (orchestrator)
    turn_tool("task_complete", {"report": "PLAN: create greeting.txt containing hello"}),
    # implement (worker): write, then done
    turn_tool("write_file", {"path": "greeting.txt", "content": "hello"}),
    turn_tool("task_complete", {"report": "wrote greeting.txt with hello"}),
    # code-verifier: reads, then verdict
    turn_tool("read_file", {"path": "greeting.txt"}),
    turn_tool("task_complete", {"report": '{"passed": true, "reasons": "greeting.txt contains hello"}'}),
    # integrate (orchestrator)
    turn_tool("task_complete", {"report": "FINAL: goal met, gated and verified"}),
]


def test_full_workflow_then_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="testrun", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      script=list(SCRIPT))
    runner._models["mid"] = brain

    outcomes = runner.run_workflow(tmp_path / "workflows" / "mini.yaml",
                                   goal="greet the world")
    assert [o.status for o in outcomes] == ["passed", "passed", "passed"]
    assert (tmp_path / "workspace" / "greeting.txt").read_text() == "hello"
    assert outcomes[2].report.startswith("FINAL")
    # goal flowed into the plan task; plan report flowed into implement task
    assert "greet the world" in brain.calls[0]["messages"][1].content
    assert "PLAN:" in brain.calls[1]["messages"][1].content
    # check output persisted as proof artifact
    proofs = list((tmp_path / "runs" / "testrun" / "proofs").iterdir())
    assert any("check-file-exists" in p.name for p in proofs)

    # resume: same run_id, a brain that would fail if consulted
    runner2 = WorkflowRunner(project_root=tmp_path, run_id="testrun", echo=False)
    dead_brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"))
    runner2._models["mid"] = dead_brain
    outcomes2 = runner2.run_workflow(tmp_path / "workflows" / "mini.yaml",
                                     goal="greet the world")
    assert [o.status for o in outcomes2] == ["skipped_resume"] * 3
    assert dead_brain.calls == []


def test_gate_failure_stops_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="failrun", echo=False)
    # worker never creates greeting.txt -> deterministic check fails on both
    # attempts -> needs_human -> integrate never runs
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"), script=[
        turn_tool("task_complete", {"report": "PLAN: create greeting.txt"}),
        turn_tool("task_complete", {"report": "claimed done, wrote nothing"}),
        turn_tool("task_complete", {"report": "still wrote nothing"}),
    ])
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    # reformulated retry task carried the failure evidence to the worker
    assert "FAILED" in brain.calls[2]["messages"][1].content


def test_resume_reruns_needs_human_phase(tmp_path, monkeypatch):
    """A journaled needs_human phase must NOT be skipped on resume: that would
    let downstream phases build on unverified work."""
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="haltrun", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=[
            turn_tool("task_complete", {"report": "PLAN: create greeting.txt"}),
            turn_tool("task_complete", {"report": "claimed done, wrote nothing"}),
            turn_tool("task_complete", {"report": "still wrote nothing"}),
        ])
    outcomes = runner.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    assert [o.status for o in outcomes] == ["passed", "needs_human"]

    # resume with a brain that now does the work: plan skips, implement re-runs
    runner2 = WorkflowRunner(project_root=tmp_path, run_id="haltrun", echo=False)
    runner2._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=[
            turn_tool("write_file", {"path": "greeting.txt", "content": "hello"}),
            turn_tool("task_complete", {"report": "wrote greeting.txt"}),
            turn_tool("read_file", {"path": "greeting.txt"}),
            turn_tool("task_complete",
                      {"report": '{"passed": true, "reasons": "file exists"}'}),
            turn_tool("task_complete", {"report": "FINAL: done for real"}),
        ])
    outcomes2 = runner2.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    assert [o.status for o in outcomes2] == ["skipped_resume", "passed", "passed"]
