"""Boundary wired into the runner and loop end-to-end: opt-in, strip through
a real workflow, map persisted outside the run tree, secret halt, and the
byte-identical guarantee when the boundary is off.
"""

import json
import textwrap

from harness import sandbox
from harness.boundary import Boundary, StripMap
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def scaffold(root, boundary=False, include_contextual=False):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid: { provider: mock, model_id: mock }
        routing:
          default: { tier: mid, effort: medium }
        budget: { max_usd: 5.0, max_tokens: 100000 }
    """))
    if boundary:
        (root / "config" / "boundary.yaml").write_text(
            f"enabled: true\ninclude_contextual: {str(include_contextual).lower()}\n")
    (root / "workflows").mkdir()
    (root / "workflows" / "wf.yaml").write_text(textwrap.dedent("""
        name: wf
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for: {goal}"
          - name: integrate
            agent: orchestrator
            task: "Summarize: {plan}"
    """))


def run(root, goal, capture=None):
    runner = WorkflowRunner(project_root=root, run_id="r1", echo=False)

    def brain(messages):
        if capture is not None:
            # record what the model actually sees (the last user/tool content)
            capture.append(messages[-1].content)
        return AssistantTurn(
            content="", stop_reason="tool_use",
            tool_calls=[ToolCall(id="c", name="task_complete",
                                 arguments={"report": "done: " + messages[-1].content[:60]})])
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), fn=brain)
    outcomes = runner.run_workflow(root / "workflows" / "wf.yaml", goal=goal)
    return runner, outcomes


def events_blob(root):
    return (root / "runs" / "r1" / "events.jsonl").read_text()


def test_boundary_off_is_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap", lambda a, w, allow_network=False: a)
    scaffold(tmp_path, boundary=False)
    runner, outcomes = run(tmp_path, "contact casey@example.com now")
    assert [o.status for o in outcomes] == ["passed", "passed"]
    assert runner.boundary is None
    assert "casey@example.com" in events_blob(tmp_path)   # unstripped: off
    assert not (tmp_path / ".boundary").exists()


def test_boundary_on_strips_pii_from_everything_the_model_sees(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap", lambda a, w, allow_network=False: a)
    scaffold(tmp_path, boundary=True)
    seen: list[str] = []
    runner, outcomes = run(tmp_path, "contact casey@example.com and 415-555-0187",
                           capture=seen)
    assert [o.status for o in outcomes] == ["passed", "passed"]
    # the model never saw a raw value
    joined = "\n".join(seen)
    assert "casey@example.com" not in joined
    assert "415-555-0187" not in joined
    assert "[EMAIL_1]" in joined
    # nor did any run artifact
    blob = events_blob(tmp_path)
    assert "casey@example.com" not in blob and "415-555-0187" not in blob


def test_strip_map_persists_outside_run_and_rehydrates(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap", lambda a, w, allow_network=False: a)
    scaffold(tmp_path, boundary=True)
    run(tmp_path, "reach casey@example.com")
    # the map is at the operator boundary, not in the run tree
    map_path = tmp_path / ".boundary" / "r1.json"
    assert map_path.exists()
    assert "runs" not in map_path.parts
    saved = json.loads(map_path.read_text())
    assert saved["mapping"]["[EMAIL_1]"] == "casey@example.com"
    # operator-boundary rehydration restores the original
    assert Boundary.rehydrate("[EMAIL_1]", saved["mapping"]) == "casey@example.com"
    assert (map_path.stat().st_mode & 0o777) == 0o600


def test_secret_in_goal_halts_before_workflow_start(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap", lambda a, w, allow_network=False: a)
    scaffold(tmp_path, boundary=True)
    seen: list[str] = []
    runner, outcomes = run(tmp_path, "use key AKIACANARY0INTEGT000 to deploy",
                           capture=seen)
    assert [o.status for o in outcomes] == ["needs_human"]
    assert "secret egress halted" in outcomes[0].report
    assert "aws_access_key" in outcomes[0].report
    assert "AKIACANARY0INTEGT000" not in outcomes[0].report   # kind only
    assert seen == []                                          # model never ran
    assert "AKIACANARY0INTEGT000" not in events_blob(tmp_path)


def test_resume_with_missing_map_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap", lambda a, w, allow_network=False: a)
    scaffold(tmp_path, boundary=True)
    run(tmp_path, "reach casey@example.com")
    # simulate a resume whose map has been lost: journal present, map deleted
    (tmp_path / ".boundary" / "r1.json").unlink()
    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    assert runner.strip_map.status == "missing"
    assert not runner.strip_map.rehydration_available
