"""Cascade wiring: policy-driven gate escalation, and the acceptance proof
that a workflow which does not opt in routes byte-identically to 0.6."""

import json
import textwrap

import pytest

from harness import sandbox
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


def scaffold(root, cascade_yaml="", default_effort="medium"):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent(f"""
        tiers:
          local:
            provider: mock
            model_id: mock
          mid:
            provider: mock
            model_id: mock
          frontier:
            provider: mock
            model_id: mock
        routing:
          default: {{ tier: mid, effort: {default_effort} }}
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    if cascade_yaml:
        (root / "config" / "cascade.yaml").write_text(cascade_yaml)
    (root / "workflows").mkdir()


def failing_workflow(root, extra="", max_attempts=4):
    (root / "workflows" / "wf.yaml").write_text(textwrap.dedent(f"""
        name: wf
        phases:
          - name: build
            agent: implementer
            {extra}
            task: "Do the thing: {{goal}}"
            verify:
              max_attempts: {max_attempts}
              checks:
                - name: always-fails
                  command: python3 -c "import sys; sys.exit(1)"
    """))


def worker_brain(messages):
    # accept consent, then complete; the failing check drives gate retries
    if messages[-1].name == "accept_task" if hasattr(messages[-1], "name") else False:
        pass
    last = messages[-1]
    if getattr(last, "name", None) == "accept_task":
        return AssistantTurn(content="", stop_reason="tool_use",
                             tool_calls=[ToolCall(id="d", name="task_complete",
                                                  arguments={"report": "did it"})])
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="a", name="accept_task",
                                              arguments={})])


def run_and_routes(tmp_path):
    runner = WorkflowRunner(project_root=tmp_path, run_id="casc", echo=False)
    brain = MockModel(ModelSpec(name="m", provider="mock", model_id="mock"),
                      fn=worker_brain)
    for tier in ("local", "mid", "frontier"):
        runner._models[tier] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")
    events = [json.loads(l) for l in
              (tmp_path / "runs" / "casc" / "events.jsonl").read_text().splitlines()
              if l.strip()]
    routes = [e["route"] for e in events if e["kind"] == "gate_verdict"]
    cascade_events = [e for e in events if e["kind"] == "cascade_decision"]
    return outcomes, routes, cascade_events


def test_no_opt_in_routes_byte_identical_to_default_ladder(tmp_path, monkeypatch):
    """0.7 acceptance: cascade config present, phase does not opt in — the
    exact pre-cascade escalation sequence, and zero cascade decisions."""
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, cascade_yaml=textwrap.dedent("""
        policies:
          cheap-first:
            ladder: [local, mid]
        reserved: [arbitration]
    """))
    failing_workflow(tmp_path, max_attempts=4)

    outcomes, routes, cascade_events = run_and_routes(tmp_path)

    assert outcomes[0].status == "needs_human"
    # the 0.6 ladder: attempt 1 and 2 at the routed tier/effort, then
    # effort climbs — mid/medium, mid/medium, mid/high, mid/xhigh
    assert routes == [
        {"tier": "mid", "effort": "medium"},
        {"tier": "mid", "effort": "medium"},
        {"tier": "mid", "effort": "high"},
        {"tier": "mid", "effort": "xhigh"},
    ]
    assert cascade_events == []


def test_cascade_phase_climbs_policy_ladder_after_effort(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, default_effort="max", cascade_yaml=textwrap.dedent("""
        policies:
          climb-once:
            ladder: [local, mid]
            escalate_on: [gate_fail]
            max_climb: 1
    """))
    failing_workflow(tmp_path, extra="cascade: climb-once", max_attempts=4)

    outcomes, routes, cascade_events = run_and_routes(tmp_path)

    assert outcomes[0].status == "needs_human"
    # starts on the ladder's first rung at the routed effort (max, so the
    # first escalation is a tier decision), climbs to mid, then effort
    # climbs inside mid
    assert routes == [
        {"tier": "local", "effort": "max"},
        {"tier": "local", "effort": "max"},
        {"tier": "mid", "effort": "medium"},
        {"tier": "mid", "effort": "high"},
    ]
    climb = [e for e in cascade_events if e["action"] == "climb"]
    assert len(climb) == 1
    assert climb[0]["policy"] == "climb-once"
    assert climb[0]["tier"] == "mid"
    assert "gate_fail" in climb[0]["reason"]


def test_cascade_exhaust_is_evented_and_hands_to_operator(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, default_effort="max", cascade_yaml=textwrap.dedent("""
        policies:
          floor-only:
            ladder: [local]
            on_exhaust: defer
    """))
    failing_workflow(tmp_path, extra="cascade: floor-only", max_attempts=3)

    outcomes, routes, cascade_events = run_and_routes(tmp_path)

    assert outcomes[0].status == "needs_human"
    assert all(r == {"tier": "local", "effort": "max"} for r in routes)
    assert len(routes) == 2              # exhausted after attempt 2's escalation
    exhausted = [e for e in cascade_events if e["action"] == "exhausted"]
    assert exhausted and "defer" in exhausted[0]["reason"]


def test_unknown_cascade_policy_fails_closed_with_named_action(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, cascade_yaml="policies: {}\n")
    failing_workflow(tmp_path, extra="cascade: nope", max_attempts=1)

    runner = WorkflowRunner(project_root=tmp_path, run_id="casc", echo=False)
    brain = MockModel(ModelSpec(name="m", provider="mock", model_id="mock"),
                      fn=worker_brain)
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    assert "unknown cascade policy 'nope'" in outcomes[0].report
    assert "config/cascade.yaml" in outcomes[0].report
    assert brain.calls == []             # refused before any model dispatch


def test_policy_naming_unconfigured_tier_refuses_at_startup(tmp_path):
    scaffold(tmp_path, cascade_yaml=textwrap.dedent("""
        policies:
          bad:
            ladder: [local, sovereign]
    """))
    with pytest.raises(ValueError, match="unconfigured tier"):
        WorkflowRunner(project_root=tmp_path, run_id="casc", echo=False)
