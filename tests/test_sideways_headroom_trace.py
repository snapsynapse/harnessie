"""0.7 task 3: sideways provider fallback, escalation headroom, routing_trace.

Sideways moves cross providers at the same tier and never climb; a climb the
policy approves is still refused without budget headroom; every attempt's
tier, model, and outcome is a routing_trace event.
"""

import json
import textwrap

import pytest

from harness import sandbox
from harness.cascade import CascadePolicy
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.routing import Route
from harness.runner import WorkflowRunner, load_models_config


def scaffold(root, cascade_yaml="", default_effort="medium",
             local_fallback=None, mid_cost=(3.0, 15.0), budget_usd=5.0):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge.")
    (root / "config").mkdir()
    fb = (f"\n            fallbacks:\n              - model_id: {local_fallback}"
          if local_fallback else "")
    (root / "config" / "models.yaml").write_text(textwrap.dedent(f"""
        tiers:
          local:
            provider: mock
            model_id: mock-a{fb}
          mid:
            provider: mock
            model_id: mock-mid
            max_tokens: 8192
            cost_per_mtok_in: {mid_cost[0]}
            cost_per_mtok_out: {mid_cost[1]}
        routing:
          default: {{ tier: local, effort: {default_effort} }}
        budget:
          max_usd: {budget_usd}
          max_tokens: 100000
    """))
    if cascade_yaml:
        (root / "config" / "cascade.yaml").write_text(cascade_yaml)
    (root / "workflows").mkdir()


def workflow(root, extra="", max_attempts=3, checks=True):
    lines = [
        "name: wf",
        "phases:",
        "  - name: build",
        "    agent: implementer",
    ]
    if extra:
        lines.append(f"    {extra}")
    lines += [
        '    task: "Do the thing: {goal}"',
        "    verify:",
        f"      max_attempts: {max_attempts}",
    ]
    if checks:
        lines += [
            "      checks:",
            "        - name: always-fails",
            '          command: python3 -c "import sys; sys.exit(1)"',
        ]
    (root / "workflows" / "wf.yaml").write_text("\n".join(lines) + "\n")


def refusing_brain(messages):
    return AssistantTurn(content="no", stop_reason="refusal")


def erroring_brain(messages):
    return AssistantTurn(content="boom", stop_reason="error")


def working_brain(messages):
    if getattr(messages[-1], "name", None) == "accept_task":
        return AssistantTurn(content="", stop_reason="tool_use",
                             tool_calls=[ToolCall(id="d", name="task_complete",
                                                  arguments={"report": "done"})])
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="a", name="accept_task",
                                              arguments={})])


def events_of(root, run_id="r1"):
    return [json.loads(l) for l in
            (root / "runs" / run_id / "events.jsonl").read_text().splitlines()
            if l.strip()]


def test_fallbacks_parse_and_route_by_alt(tmp_path):
    scaffold(tmp_path, local_fallback="mock-b")
    tiers, _, _, fallbacks = load_models_config(tmp_path / "config" / "models.yaml")
    assert [s.model_id for s in fallbacks["local"]] == ["mock-b"]
    assert fallbacks["local"][0].provider == "mock"      # inherited
    assert fallbacks["local"][0].name == "local~alt1"
    assert fallbacks["mid"] == []

    from harness.routing import Router
    router = Router(tiers=tiers, fallbacks=fallbacks)
    assert router.spec_for(Route("local", "medium")).model_id == "mock-a"
    assert router.spec_for(Route("local", "medium", 1)).model_id == "mock-b"
    with pytest.raises(ValueError, match="no fallback #2"):
        router.spec_for(Route("local", "medium", 2))


def test_refusal_moves_sideways_and_fallback_completes(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, local_fallback="mock-b", cascade_yaml=textwrap.dedent("""
        policies:
          contained-local:
            ladder: [local]
            contained: true
    """))
    workflow(tmp_path, extra="cascade: contained-local", max_attempts=3,
             checks=False)

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    spec = ModelSpec(name="x", provider="mock", model_id="mock")
    runner._models["local"] = MockModel(spec, fn=refusing_brain)
    runner._models["local~alt1"] = MockModel(spec, fn=working_brain)
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "passed"
    ev = events_of(tmp_path)
    sideways = [e for e in ev if e["kind"] == "cascade_decision"
                and e["action"] == "sideways"]
    assert len(sideways) == 1
    assert "refusal moves sideways to mock-b" in sideways[0]["reason"]
    trace = [(e["model"], e["outcome"]) for e in ev
             if e["kind"] == "routing_trace"]
    assert trace == [("mock-a", "refusal"), ("mock-a", "refusal"),
                     ("mock-b", "complete")]
    # sideways stayed on the tier: no climb ever happened
    assert not [e for e in ev if e["kind"] == "cascade_decision"
                and e["action"] == "climb"]


def test_availability_holds_when_no_fallback_left(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, cascade_yaml=textwrap.dedent("""
        policies:
          local-only:
            ladder: [local, mid]
            escalate_on: [gate_fail]
    """))
    workflow(tmp_path, extra="cascade: local-only", max_attempts=3, checks=False)

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    runner._models["local"] = MockModel(
        ModelSpec(name="x", provider="mock", model_id="mock"), fn=erroring_brain)
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    ev = events_of(tmp_path)
    holds = [e for e in ev if e["kind"] == "cascade_decision"
             and e["action"] == "hold"]
    assert holds and "availability never climbs" in holds[0]["reason"]
    # availability never reached the mid tier despite it being on the ladder
    assert not [e for e in ev if e["kind"] == "routing_trace"
                and e["tier"] == "mid"]


def test_climb_without_headroom_is_refused_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    # mid worst-case turn: 8192 * (300 + 1500) / 1e6 = $14.75 > $5.00 budget
    scaffold(tmp_path, default_effort="max", mid_cost=(300.0, 1500.0),
             budget_usd=5.0, cascade_yaml=textwrap.dedent("""
        policies:
          climb-up:
            ladder: [local, mid]
    """))
    workflow(tmp_path, extra="cascade: climb-up", max_attempts=4, checks=True)

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    runner._models["local"] = MockModel(
        ModelSpec(name="x", provider="mock", model_id="mock"), fn=working_brain)
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    ev = events_of(tmp_path)
    refused = [e for e in ev if e["kind"] == "cascade_decision"
               and e["action"] == "refused_headroom"]
    assert len(refused) == 1
    assert refused[0]["tier"] == "mid"
    assert "$14.7456" in refused[0]["reason"]
    assert "refused before dispatch" in refused[0]["reason"]
    # the climb never dispatched: no attempt ever ran at mid
    assert not [e for e in ev if e["kind"] == "routing_trace"
                and e["tier"] == "mid"]


def test_contained_policy_cannot_climb_on_refusal():
    with pytest.raises(ValueError, match="containment leak"):
        CascadePolicy(name="p", ladder=("local",), contained=True,
                      escalate_on=("gate_fail", "refusal"))


def test_escalated_run_never_exceeds_ceiling_plus_one_turn(tmp_path, monkeypatch):
    """The headroom invariant (AIDR-0005): with Option A as the climb-
    admission floor, per-turn ceiling enforcement bounds an escalated run's
    total spend to at most the ceiling plus one worst-case turn — the same
    residual the budget hardening accepted (a turn cannot be un-called
    mid-flight). The floor's worst-case-turn proxy is max_tokens at both
    rates; a prompt larger than max_tokens could exceed the proxy, which is
    the estimate's stated limit, not a hole in enforcement."""
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    # mid worst-case turn: 8192 * (3 + 15) / 1e6 = $0.1475; budget $0.50 —
    # the climb is admitted (0.1475 <= 0.50 remaining) and the escalated
    # attempts then burn real dollars per turn until enforcement stops them
    scaffold(tmp_path, default_effort="max", mid_cost=(3.0, 15.0),
             budget_usd=0.5, cascade_yaml=textwrap.dedent("""
        policies:
          climb-up:
            ladder: [local, mid]
    """))
    workflow(tmp_path, extra="cascade: climb-up", max_attempts=6, checks=True)

    def burning_brain(messages):
        turn = working_brain(messages)
        turn.input_tokens, turn.output_tokens = 8000, 8000   # ~$0.144/turn at mid
        return turn

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    runner._models["local"] = MockModel(
        ModelSpec(name="local", provider="mock", model_id="mock"),
        fn=working_brain)
    # the loop charges from the model's own spec, so the mock must carry the
    # mid tier's real rates for escalated turns to bill dollars
    runner._models["mid"] = MockModel(runner.router.tiers["mid"],
                                      fn=burning_brain)
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    ev = events_of(tmp_path)
    assert [e for e in ev if e["kind"] == "cascade_decision"
            and e["action"] == "climb"], "the climb must have been admitted"
    from harness.runner import _climb_cost_estimate
    mid_spec = runner.router.tiers["mid"]
    worst_turn = _climb_cost_estimate(mid_spec)
    assert runner.budget.spent_usd > 0            # escalated turns really billed
    assert runner.budget.spent_usd <= runner.budget.max_usd + worst_turn + 1e-9


def test_routing_trace_covers_every_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path)
    workflow(tmp_path, max_attempts=2, checks=True)

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    runner._models["local"] = MockModel(
        ModelSpec(name="x", provider="mock", model_id="mock"), fn=working_brain)
    runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    trace = [e for e in events_of(tmp_path) if e["kind"] == "routing_trace"]
    assert len(trace) == 2               # one per gate attempt
    assert all(e["model"] == "mock-a" and e["tier"] == "local"
               and e["provider"] == "mock" and e["alt"] == 0
               and e["outcome"] == "complete" for e in trace)
