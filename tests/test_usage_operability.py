"""Unknown usage has an operator remedy, provider counters are bounded, and
error envelopes never dispatch tools.

Offline: the transport's open seam returns synthetic bodies; MockModel
carries every loop test.
"""

import io
import json
import textwrap

import pytest

from harness.accounting import AccountingError, finite_amount
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models import _transport
from harness.models.anthropic import AnthropicModel
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.models.openai_compat import OpenAICompatModel
from harness.models.openai_responses import OpenAIResponsesModel
from harness.routing import Budget
from harness.runner import WorkflowRunner, load_models_config
from harness.schema import ConfigurationError, validate_data
from harness.tools.registry import ToolRegistry


class _Body(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _serve(monkeypatch, payload):
    wire = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    monkeypatch.setattr("harness.models._transport._open",
                        lambda req, timeout=None: _Body(wire))


def _compat():
    return OpenAICompatModel(ModelSpec(
        name="mid", provider="openai-compat", model_id="t",
        base_url="https://origin.invalid/v1", supports_effort=False))


def _anthropic():
    return AnthropicModel(ModelSpec(
        name="mid", provider="anthropic", model_id="t", supports_effort=False))


def _responses():
    return OpenAIResponsesModel(ModelSpec(
        name="mid", provider="openai-responses", model_id="t",
        base_url="https://origin.invalid/v1", supports_effort=False))


_FIELDS = {_compat: ("prompt_tokens", "completion_tokens"),
           _anthropic: ("input_tokens", "output_tokens"),
           _responses: ("input_tokens", "output_tokens")}
_FACTORIES = [_compat, _anthropic, _responses]
CEILING = 10**12   # documented provider usage-counter ceiling


def _envelope(factory, usage):
    if factory is _compat:
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
    elif factory is _anthropic:
        body = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    else:
        body = {"status": "completed", "output": []}
    body["usage"] = usage
    return body


def _events(tmp_path):
    path = tmp_path / "run" / "events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _loop(tmp_path, model, budget):
    return AgentLoop(role="worker", model=model, registry=ToolRegistry(),
                     events=EventLog(tmp_path / "run", echo=False), budget=budget,
                     max_steps=5)


def _mock(turns, unmetered=False, name="mid"):
    return MockModel(ModelSpec(name=name, provider="mock", model_id="mock",
                               unmetered=unmetered), script=list(turns))


def _complete_turn(**usage):
    return AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
        ToolCall(id="c1", name="task_complete", arguments={"report": "done"})], **usage)


# -- item 2: provider counters are bounded; huge integers never escape


@pytest.mark.parametrize("factory", _FACTORIES)
@pytest.mark.parametrize("which", [0, 1])
@pytest.mark.parametrize("value", [10**400, CEILING + 1], ids=["huge", "over_ceiling"])
def test_huge_usage_counter_is_error_with_unknown_usage(monkeypatch, factory, which,
                                                        value):
    fields = _FIELDS[factory]
    usage = {fields[0]: 7, fields[1]: 3}
    usage[fields[which]] = value
    _serve(monkeypatch, _envelope(factory, usage))
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert turn.usage_known is False
    assert turn.input_tokens <= CEILING
    assert turn.output_tokens <= CEILING


def test_usage_counter_ceiling_is_documented_constant():
    assert getattr(_transport, "MAX_USAGE_COUNT", None) == CEILING


@pytest.mark.parametrize("factory", _FACTORIES)
def test_counter_at_ceiling_is_accepted(monkeypatch, factory):
    fields = _FIELDS[factory]
    _serve(monkeypatch, _envelope(factory, {fields[0]: CEILING,
                                            fields[1]: 0}))
    turn = factory().complete([])
    assert turn.stop_reason == "end_turn"
    assert turn.usage_known is True
    assert turn.input_tokens == CEILING


@pytest.mark.parametrize("factory", _FACTORIES)
def test_huge_counter_through_loop_is_journaled_and_stops(monkeypatch, tmp_path,
                                                          factory):
    fields = _FIELDS[factory]
    _serve(monkeypatch, _envelope(factory, {fields[0]: 10**400, fields[1]: 1}))
    budget = Budget(max_usd=10, max_tokens=10_000)
    result = _loop(tmp_path, factory(), budget).run("system", "task")
    assert result.stop == "budget"
    kinds = [e["kind"] for e in _events(tmp_path)]
    assert "model_turn" in kinds
    assert "budget_charge" not in kinds or budget.accounting_unknown


def test_finite_amount_huge_int_is_accounting_error():
    with pytest.raises(AccountingError):
        finite_amount(10**400, "usd")
    finite_amount(10**400, "tokens", integer=True)  # integers are exact


@pytest.mark.parametrize("tokens", [(10**400, 0), (0, 10**400)])
def test_budget_charge_huge_counter_is_accounting_error_not_overflow(tokens):
    budget = Budget(max_usd=10.0, max_tokens=100)
    spec = ModelSpec(name="mid", provider="mock", model_id="m", cost_per_mtok_in=1.0,
                     cost_per_mtok_out=1.0)
    with pytest.raises(AccountingError):
        budget.charge(spec, *tokens)
    assert (budget.spent_usd, budget.spent_tokens) == (0.0, 0)


def test_budget_huge_ceiling_is_accounting_error_not_overflow():
    with pytest.raises(AccountingError):
        Budget(max_usd=10**400)


def test_loop_survives_a_brain_reporting_huge_counters(tmp_path):
    model = _mock([_complete_turn(input_tokens=10**400, output_tokens=1)])
    budget = Budget(max_usd=10, max_tokens=10_000)
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "budget"
    assert result.detail.get("accounting") == "unknown"
    assert budget.accounting_unknown is True
    kinds = [e["kind"] for e in _events(tmp_path)]
    assert "model_turn" in kinds and "task_complete" not in kinds


def _models_yaml(tmp_path, tier_extra="", budget="max_usd: 5.0\n  max_tokens: 100"):
    path = tmp_path / "models.yaml"
    path.write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock
        {extra}
        routing:
          default: {{ tier: mid, effort: medium }}
        budget:
          {budget}
    """).format(extra=textwrap.indent(tier_extra, "    "), budget=budget))
    return path


@pytest.mark.parametrize("tier_extra,budget", [
    ("max_tokens: " + "9" * 400, "max_usd: 5.0\n  max_tokens: 100"),
    ("", "max_usd: 5.0\n  max_tokens: " + "9" * 400),
    ("", "max_usd: " + "9" * 400 + "\n  max_tokens: 100"),
    ("cost_per_mtok_in: " + "9" * 400, "max_usd: 5.0\n  max_tokens: 100"),
    ("max_tokens: 1000000000001", "max_usd: 5.0\n  max_tokens: 100"),
], ids=["tier_max_tokens", "budget_max_tokens", "budget_max_usd", "rate",
        "tier_max_tokens_over_ceiling"])
def test_huge_integer_in_models_yaml_is_configuration_error(tmp_path, tier_extra,
                                                            budget):
    with pytest.raises(ConfigurationError):
        load_models_config(_models_yaml(tmp_path, tier_extra, budget))


# -- item 1: explicit per-tier unmetered opt-out with an operator remedy


def test_models_yaml_accepts_unmetered_and_fallbacks_inherit(tmp_path):
    tiers, _, _, fallbacks = load_models_config(_models_yaml(
        tmp_path, "unmetered: true\nfallbacks:\n  - model_id: other"))
    assert tiers["mid"].unmetered is True
    assert fallbacks["mid"][0].unmetered is True


def test_models_yaml_default_is_metered(tmp_path):
    tiers, _, _, _ = load_models_config(_models_yaml(tmp_path))
    assert tiers["mid"].unmetered is False


@pytest.mark.parametrize("tier", [
    {"unmetered": "yes"},
    {"unmetered": 1},
    {"unmetered": True, "cost_per_mtok_in": 0.5},
    {"unmetered": True, "cost_per_mtok_out": 2},
    {"unmetered": True, "fallbacks": [{"model_id": "x", "cost_per_mtok_out": 1.0}]},
    {"fallbacks": [{"model_id": "x", "unmetered": True}]},
], ids=["string", "int", "paid_in", "paid_out", "paid_fallback", "fallback_opt_out"])
def test_schema_refuses_invalid_unmetered(tier):
    doc = {"tiers": {"mid": {"provider": "mock", "model_id": "m", **tier}}}
    assert validate_data(doc, "models") != []


def test_schema_accepts_unmetered_zero_cost_tier():
    doc = {"tiers": {"local": {"provider": "openai-compat", "model_id": "m",
                               "base_url": "http://127.0.0.1:11434/v1",
                               "unmetered": True, "cost_per_mtok_in": 0,
                               "cost_per_mtok_out": 0.0}}}
    assert validate_data(doc, "models") == []


def test_unknown_usage_stop_names_the_remedy(tmp_path):
    model = _mock([_complete_turn(usage_known=False)], name="local")
    result = _loop(tmp_path, model, Budget(max_usd=10, max_tokens=10_000)).run(
        "system", "task")
    assert result.stop == "budget"
    assert result.detail["accounting"] == "unknown"
    assert result.detail["tier"] == "local"
    assert "unmetered: true" in result.detail["remedy"]
    assert "unmetered: true" in result.report


def test_unmetered_tier_still_enforces_reported_token_ceiling(tmp_path):
    model = _mock([AssistantTurn(content="thinking", input_tokens=60, output_tokens=60),
                   _complete_turn(input_tokens=1, output_tokens=1)], unmetered=True)
    budget = Budget(max_usd=10, max_tokens=100)
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "budget"
    assert len(model.calls) == 1
    assert budget.spent_tokens == 120


def test_unmetered_charge_is_recorded(tmp_path):
    records = []
    budget = Budget(max_usd=10, max_tokens=10_000,
                    recorder=lambda **fields: records.append(fields))
    model = _mock([_complete_turn(input_tokens=2, usage_known=False)],
                  unmetered=True, name="local")
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "complete"
    assert records[0]["unmetered"] is True
    assert records[0]["usage_known"] is False
    assert records[0]["tier"] == "local"


def _scaffold(root):
    (root / "agents" / "workers").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "verifiers").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid: { provider: mock, model_id: mock }
        routing:
          default: { tier: mid, effort: medium }
        budget: { max_usd: 5.0, max_tokens: 1000 }
    """))
    (root / "workflows").mkdir(exist_ok=True)
    (root / "workflows" / "one.yaml").write_text(textwrap.dedent("""
        name: one
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {goal}"
    """))


def _unknown_usage_run(root):
    _scaffold(root)
    runner = WorkflowRunner(project_root=root, run_id="acct", echo=False)
    runner._models["mid"] = _mock([AssistantTurn(content="x", usage_known=False)])
    runner.run_workflow(root / "workflows" / "one.yaml", goal="g")


def test_resume_refusal_for_unknown_usage_names_the_remedy(tmp_path):
    _unknown_usage_run(tmp_path)
    with pytest.raises(AccountingError) as caught:
        WorkflowRunner(project_root=tmp_path, run_id="acct", echo=False)
    assert "unmetered: true" in caught.value.remedy
    assert "mid" in caught.value.remedy


def test_cli_resume_refusal_prints_the_remedy(tmp_path, capsys):
    from harness.cli import main

    _unknown_usage_run(tmp_path)
    code = main(["--root", str(tmp_path), "resume", "acct", "workflows/one.yaml"])
    assert code == 2
    err = capsys.readouterr().err
    assert "resume refused" in err
    assert "unmetered: true" in err


# -- item 5: error envelopes are error turns and never dispatch tools


_TOOL_OUTPUT = [{"type": "function_call", "call_id": "c1", "name": "task_complete",
                 "arguments": '{"report":"x"}', "status": "completed"}]


@pytest.mark.parametrize("error", [{"code": "server_error", "message": "boom"},
                                   {"message": "x"}, "boom"])
def test_responses_completed_with_error_object_is_error_turn(monkeypatch, error):
    _serve(monkeypatch, {"status": "completed", "error": error, "output": _TOOL_OUTPUT,
                         "usage": {"input_tokens": 4, "output_tokens": 2}})
    turn = _responses().complete([])
    assert turn.stop_reason == "error"
    assert turn.tool_calls == []
    assert (turn.input_tokens, turn.output_tokens, turn.usage_known) == (4, 2, True)


def test_responses_completed_with_null_error_is_positive_control(monkeypatch):
    _serve(monkeypatch, {"status": "completed", "error": None, "output": _TOOL_OUTPUT,
                         "usage": {"input_tokens": 4, "output_tokens": 2}})
    turn = _responses().complete([])
    assert turn.stop_reason == "tool_use"
    assert [tc.name for tc in turn.tool_calls] == ["task_complete"]


@pytest.mark.parametrize("usage,known", [
    (None, False), ({"input_tokens": 3, "output_tokens": 1}, True)])
def test_anthropic_error_envelope_is_error_turn(monkeypatch, usage, known):
    body = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    if usage is not None:
        body["usage"] = usage
    _serve(monkeypatch, body)
    turn = _anthropic().complete([])
    assert turn.stop_reason == "error"
    assert turn.tool_calls == []
    assert turn.usage_known is known


def test_anthropic_error_envelope_with_tool_blocks_never_dispatches(monkeypatch,
                                                                    tmp_path):
    _serve(monkeypatch, {"type": "error", "error": {"type": "api_error"},
                         "content": [{"type": "tool_use", "id": "c1",
                                      "name": "task_complete",
                                      "input": {"report": "x"}}],
                         "stop_reason": "tool_use",
                         "usage": {"input_tokens": 1, "output_tokens": 1}})
    result = _loop(tmp_path, _anthropic(), Budget(max_usd=10, max_tokens=10_000)).run(
        "system", "task")
    kinds = [e["kind"] for e in _events(tmp_path)]
    assert result.stop != "complete"
    assert "task_complete" not in kinds


def test_anthropic_message_type_is_positive_control(monkeypatch):
    _serve(monkeypatch, {"type": "message", "content": [{"type": "text", "text": "ok"}],
                         "stop_reason": "end_turn",
                         "usage": {"input_tokens": 1, "output_tokens": 1}})
    turn = _anthropic().complete([])
    assert turn.stop_reason == "end_turn"
