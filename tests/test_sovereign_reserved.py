"""0.7 task 4: the sovereign tier slot and the reserved pre-gate.

Sovereign is a valid configured tier reachable only where policy names it
(routing rows, cascade ladders) — the default escalation walk never enters
it, so existing configs escalate byte-identically. Reserved work classes
never reach any model at any tier.
"""

import textwrap

import pytest

from harness import sandbox
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.routing import Route, TIER_ORDER, VALID_TIERS
from harness.runner import WorkflowRunner, load_models_config


def scaffold(root, sovereign=False, reserved=("arbitration",),
             routing_extra=""):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge.")
    (root / "config").mkdir()
    sov = ""
    if sovereign:
        sov = ("  sovereign:\n"
               "    provider: mock\n"
               "    model_id: mock-sov\n")
    (root / "config" / "models.yaml").write_text(textwrap.dedent(f"""
        tiers:
          local:
            provider: mock
            model_id: mock-local
          mid:
            provider: mock
            model_id: mock-mid
        """) + sov + textwrap.dedent(f"""
        routing:
          default: {{ tier: mid, effort: medium }}
        {routing_extra}
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    reserved_yaml = "\n".join(f"  - {r}" for r in reserved)
    (root / "config" / "cascade.yaml").write_text(
        f"policies: {{}}\nreserved:\n{reserved_yaml}\n" if reserved
        else "policies: {}\n")
    (root / "workflows").mkdir()


def phase_workflow(root, task_class):
    (root / "workflows" / "wf.yaml").write_text(textwrap.dedent(f"""
        name: wf
        phases:
          - name: build
            agent: implementer
            task_class: {task_class}
            task: "Do: {{goal}}"
    """))


def working_brain(messages):
    if getattr(messages[-1], "name", None) == "accept_task":
        return AssistantTurn(content="", stop_reason="tool_use",
                             tool_calls=[ToolCall(id="d", name="task_complete",
                                                  arguments={"report": "done"})])
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="a", name="accept_task",
                                              arguments={})])


def test_sovereign_is_valid_config_and_routes_explicitly(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, sovereign=True,
             routing_extra="  sensitive: { tier: sovereign, effort: medium }")
    phase_workflow(tmp_path, "sensitive")

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    runner._models["sovereign"] = MockModel(
        ModelSpec(name="sovereign", provider="mock", model_id="mock-sov"),
        fn=working_brain)
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")
    assert outcomes[0].status == "passed"


def test_default_escalation_walk_never_enters_sovereign():
    """Byte-identity of the default ladder: sovereign is valid config but the
    walk from any TIER_ORDER tier is exactly what it was before the slot."""
    assert "sovereign" in VALID_TIERS and "sovereign" not in TIER_ORDER
    assert Route("local", "max").escalate() == Route("cheap", "medium")
    assert Route("cheap", "max").escalate() == Route("mid", "medium")
    assert Route("mid", "max").escalate() == Route("frontier", "medium")
    assert Route("frontier", "max").escalate() is None


def test_unknown_tier_still_refused(tmp_path):
    scaffold(tmp_path)
    bad = (tmp_path / "config" / "models.yaml").read_text().replace(
        "  mid:", "  imperial:")
    (tmp_path / "config" / "models.yaml").write_text(bad)
    with pytest.raises(ValueError, match="unknown tier names.*imperial"):
        load_models_config(tmp_path / "config" / "models.yaml")


def test_reserved_task_class_never_reaches_a_model_sequential(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, reserved=("arbitration",),
             routing_extra="  arbitration: { tier: mid, effort: medium }")
    phase_workflow(tmp_path, "arbitration")

    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      fn=working_brain)
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    assert "reserved" in outcomes[0].report
    assert "never reaches any model" in outcomes[0].report
    assert brain.calls == []


def test_reserved_task_class_refused_in_parallel_group(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, reserved=("arbitration",),
             routing_extra="  arbitration: { tier: mid, effort: medium }")
    (tmp_path / "workflows" / "wf.yaml").write_text(textwrap.dedent("""
        name: wf
        phases:
          - name: left
            parallel: workers
            agent: implementer
            task_class: arbitration
            task: "left {goal}"
          - name: right
            parallel: workers
            agent: implementer
            task: "right {goal}"
    """))
    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      fn=working_brain)
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    by_phase = {o.phase: o for o in outcomes}
    assert by_phase["left"].status == "needs_human"
    assert "reserved" in by_phase["left"].report
    assert by_phase["right"].status == "passed"   # only the reserved phase halts


def test_reserved_position_class_halts_adversarial_phase(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, reserved=("arbitration",),
             routing_extra="  arbitration: { tier: mid, effort: medium }")
    (tmp_path / "workflows" / "wf.yaml").write_text(textwrap.dedent("""
        name: wf
        phases:
          - name: decide
            mode: adversarial
            task: "Q: {goal}"
            positions:
              - agent: implementer
                task_class: arbitration
              - agent: implementer
                task_class: default
    """))
    runner = WorkflowRunner(project_root=tmp_path, run_id="r1", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      fn=working_brain)
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    assert outcomes[0].status == "needs_human"
    assert "reserved" in outcomes[0].report
    assert brain.calls == []             # no position ever reached a model
