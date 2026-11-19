"""Cumulative accounting survives resume; nonfinite numbers never configure
or update a budget."""

import hashlib
import json
import math
import textwrap

import pytest

from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.routing import Budget
from harness.runner import WorkflowRunner, load_models_config
from harness.schema import validate_data

RATE_IN = 2.0
RATE_OUT = 4.0


def _scaffold(root, max_usd=5.0, max_tokens=100):
    (root / "agents" / "workers").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "verifiers").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "models.yaml").write_text(textwrap.dedent(f"""
        tiers:
          mid:
            provider: mock
            model_id: mock
            cost_per_mtok_in: {RATE_IN}
            cost_per_mtok_out: {RATE_OUT}
        routing:
          default: {{ tier: mid, effort: medium }}
        budget:
          max_usd: {max_usd}
          max_tokens: {max_tokens}
    """))
    (root / "workflows").mkdir(exist_ok=True)
    (root / "workflows" / "one.yaml").write_text(textwrap.dedent("""
        name: one
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {goal}"
    """))


def _spent(tokens_in, tokens_out):
    return (tokens_in * RATE_IN + tokens_out * RATE_OUT) / 1_000_000


def _talk(tokens_in, tokens_out):
    return AssistantTurn(content="thinking", stop_reason="end_turn",
                         input_tokens=tokens_in, output_tokens=tokens_out)


def _decline():
    return AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
        ToolCall(id="d", name="decline_task", arguments={"reason": "halt"})])


def _runner(root, script, run_id="acct"):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock",
                                cost_per_mtok_in=RATE_IN, cost_per_mtok_out=RATE_OUT),
                      script=list(script))
    runner._models["mid"] = brain
    return runner, brain


def _run(runner, root):
    return runner.run_workflow(root / "workflows" / "one.yaml", goal="g")


def _events_path(root, run_id="acct"):
    return root / "runs" / run_id / "events.jsonl"


def test_exhausted_resume_makes_zero_model_calls(tmp_path):
    _scaffold(tmp_path)
    first, _ = _runner(tmp_path, [_talk(80, 40)])
    assert [o.status for o in _run(first, tmp_path)] != ["passed"]
    assert first.budget.exhausted

    resumed, brain = _runner(tmp_path, [_talk(1, 1)])
    assert resumed.budget.spent_tokens == 120
    assert math.isclose(resumed.budget.spent_usd, _spent(80, 40))
    assert resumed.budget.exhausted
    _run(resumed, tmp_path)
    assert brain.calls == []


def test_partial_resume_keeps_exact_remaining_headroom(tmp_path):
    _scaffold(tmp_path)
    first, _ = _runner(tmp_path, [_talk(30, 30), _decline()])
    _run(first, tmp_path)
    assert first.budget.spent_tokens == 60

    resumed, brain = _runner(tmp_path, [_talk(20, 20), _talk(1, 1)])
    assert resumed.budget.spent_tokens == 60
    assert math.isclose(resumed.budget.spent_usd, _spent(30, 30))
    assert not resumed.budget.exhausted
    _run(resumed, tmp_path)
    assert len(brain.calls) == 1
    assert resumed.budget.spent_tokens == 100


def test_repeated_resumes_accumulate_once(tmp_path):
    _scaffold(tmp_path)
    first, _ = _runner(tmp_path, [_talk(10, 0), _decline()])
    _run(first, tmp_path)
    second, _ = _runner(tmp_path, [_talk(0, 20), _decline()])
    assert second.budget.spent_tokens == 10
    _run(second, tmp_path)
    third, _ = _runner(tmp_path, [_decline()])
    assert third.budget.spent_tokens == 30
    assert math.isclose(third.budget.spent_usd, _spent(10, 20))
    fourth, _ = _runner(tmp_path, [])
    assert fourth.budget.spent_tokens == 30


def test_parallel_child_charges_counted_once(tmp_path):
    _scaffold(tmp_path)
    runner, _ = _runner(tmp_path, [])
    a, b = runner.budget.child(), runner.budget.child()
    spec = ModelSpec(name="mid", provider="mock", model_id="mock",
                     cost_per_mtok_in=RATE_IN, cost_per_mtok_out=RATE_OUT)
    a.charge(spec, 5, 5)
    b.charge(spec, 7, 3)
    resumed, _ = _runner(tmp_path, [])
    assert resumed.budget.spent_tokens == 20
    assert math.isclose(resumed.budget.spent_usd, _spent(12, 8))


def _rechain(lines):
    """Rebuild seq/prev links so a test edit isolates the accounting check
    from the tamper-evidence check."""
    out, prev = [], "genesis"
    for seq, line in enumerate(lines, 1):
        event = json.loads(line)
        event["seq"], event["prev"] = seq, prev
        text = json.dumps(event, ensure_ascii=False)
        out.append(text)
        prev = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return out


def _edit_charges(root, mutate, drop=False):
    path = _events_path(root)
    lines = []
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event["kind"] == "budget_charge":
            if drop:
                continue
            mutate(event)
            line = json.dumps(event)
        lines.append(line)
    path.write_text("\n".join(_rechain(lines)) + "\n")


def _halted_run(root):
    _scaffold(root)
    runner, _ = _runner(root, [_talk(10, 10), _decline()])
    _run(runner, root)


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(usage_known=False),
    lambda e: e.update(tokens="20"),
    lambda e: e.update(tokens=True),
    lambda e: e.update(tokens=-1),
    lambda e: e.update(usd=-0.5),
    lambda e: e.update(usd="0.1"),
    lambda e: e.pop("usd"),
    lambda e: e.pop("tokens"),
    lambda e: e.update(spent_tokens=e["spent_tokens"] - 1),
    lambda e: e.update(spent_usd=e["spent_usd"] + 0.01),
    lambda e: e.update(usage_known="yes"),
])
def test_unknown_or_malformed_accounting_refuses_resume(tmp_path, mutate):
    _halted_run(tmp_path)
    _edit_charges(tmp_path, mutate)
    with pytest.raises(ValueError):
        _runner(tmp_path, [])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["usd", "spent_usd"])
def test_nonfinite_recorded_accounting_refuses_resume(tmp_path, value, field):
    _halted_run(tmp_path)
    _edit_charges(tmp_path, lambda e: e.update({field: value}))
    assert "NaN" in _events_path(tmp_path).read_text() or "Infinity" in \
        _events_path(tmp_path).read_text()
    with pytest.raises(ValueError):
        _runner(tmp_path, [])


def test_model_turns_without_accounting_records_refuse_resume(tmp_path):
    _halted_run(tmp_path)
    _edit_charges(tmp_path, None, drop=True)
    with pytest.raises(ValueError):
        _runner(tmp_path, [])


def test_broken_chain_refuses_resume(tmp_path):
    _halted_run(tmp_path)
    path = _events_path(tmp_path)
    lines = path.read_text().splitlines()
    first = json.loads(lines[0])
    first["tampered"] = True
    lines[0] = json.dumps(first)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        _runner(tmp_path, [])


def test_unmetered_unknown_usage_is_replayable(tmp_path):
    _halted_run(tmp_path)
    _edit_charges(tmp_path, lambda e: e.update(usage_known=False, unmetered=True))
    resumed, _ = _runner(tmp_path, [])
    assert resumed.budget.spent_tokens == 20


def test_fresh_run_starts_at_zero(tmp_path):
    _scaffold(tmp_path)
    runner, _ = _runner(tmp_path, [])
    assert (runner.budget.spent_usd, runner.budget.spent_tokens) == (0.0, 0)


# -- SEC-20261118-020: nonfinite configuration and accounting


def _models_doc(budget=None, cost_in=0.0):
    doc = {"tiers": {"mid": {"provider": "mock", "model_id": "mock",
                             "cost_per_mtok_in": cost_in}},
           "routing": {"default": {"tier": "mid", "effort": "medium"}}}
    if budget is not None:
        doc["budget"] = budget
    return doc


NONFINITE = [float("nan"), float("inf"), float("-inf")]


@pytest.mark.parametrize("value", NONFINITE)
@pytest.mark.parametrize("where", ["max_usd", "cost_in", "nested_extra"])
def test_schema_rejects_nonfinite_numbers(value, where):
    if where == "max_usd":
        doc = _models_doc({"max_usd": value, "max_tokens": 10})
    elif where == "cost_in":
        doc = _models_doc(cost_in=value)
    else:
        doc = _models_doc()
        doc["tiers"]["mid"]["extra"] = {"options": [{"temperature": value}]}
    problems = validate_data(doc, "models")
    assert any(p.code == "schema.nonfinite" for p in problems)


def test_schema_accepts_finite_controls():
    assert validate_data(_models_doc({"max_usd": 0.5, "max_tokens": 10},
                                     cost_in=0.0), "models") == []
    assert validate_data(_models_doc({"max_usd": 3, "max_tokens": 10},
                                     cost_in=1.25), "models") == []


@pytest.mark.parametrize("literal", [".nan", ".inf", "-.inf"])
@pytest.mark.parametrize("field", ["max_usd", "cost_per_mtok_in", "cost_per_mtok_out"])
def test_models_yaml_with_nonfinite_value_refuses_to_load(tmp_path, literal, field):
    budget_usd = literal if field == "max_usd" else "5.0"
    rate_in = literal if field == "cost_per_mtok_in" else "0.0"
    rate_out = literal if field == "cost_per_mtok_out" else "0.0"
    path = tmp_path / "models.yaml"
    path.write_text(textwrap.dedent(f"""
        tiers:
          mid:
            provider: mock
            model_id: mock
            cost_per_mtok_in: {rate_in}
            cost_per_mtok_out: {rate_out}
        routing:
          default: {{ tier: mid, effort: medium }}
        budget:
          max_usd: {budget_usd}
          max_tokens: 100
    """))
    with pytest.raises(ValueError):
        load_models_config(path)


@pytest.mark.parametrize("kwargs", [
    {"max_usd": float("nan")}, {"max_usd": float("inf")}, {"max_usd": -1.0},
    {"max_usd": True}, {"max_usd": "5"}, {"max_tokens": float("inf")},
    {"max_tokens": True}, {"max_tokens": -1}, {"max_tokens": 1.5},
])
def test_budget_rejects_nonfinite_or_invalid_ceilings(kwargs):
    with pytest.raises(ValueError):
        Budget(**kwargs)


@pytest.mark.parametrize("usd,tokens", [
    (float("nan"), 1), (float("inf"), 1), (-1.0, 1), (1.0, -1), (True, 1),
    (1.0, True), ("1", 1), (1.0, 1.5),
])
def test_budget_rejects_nonfinite_or_negative_spend(usd, tokens):
    budget = Budget(max_usd=10.0, max_tokens=100)
    with pytest.raises(ValueError):
        budget.add_spend(usd, tokens)
    assert (budget.spent_usd, budget.spent_tokens) == (0.0, 0)


def test_budget_rejects_nonfinite_rate_on_charge():
    budget = Budget(max_usd=10.0, max_tokens=100)
    spec = ModelSpec(name="mid", provider="mock", model_id="mock",
                     cost_per_mtok_in=float("nan"))
    with pytest.raises(ValueError):
        budget.charge(spec, 1, 1)
    assert budget.spent_usd == 0.0


def test_finite_budget_controls():
    budget = Budget(max_usd=1.0, max_tokens=100)
    budget.add_spend(0.0, 0)
    assert not budget.exhausted
    budget.add_spend(1.0, 0)
    assert budget.exhausted


def test_cli_resume_with_unknown_accounting_refuses_cleanly(tmp_path, capsys):
    from harness.cli import main

    _halted_run(tmp_path)
    _edit_charges(tmp_path, lambda e: e.update(usage_known=False))
    before = _events_path(tmp_path).read_text()
    code = main(["--root", str(tmp_path), "resume", "acct", "workflows/one.yaml"])
    assert code == 2
    assert _events_path(tmp_path).read_text() == before
