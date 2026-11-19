"""Provider envelopes: terminal status wins over tool calls, and usage that
the provider did not report is represented as unknown, never as zero.

Offline: the transport's open seam returns synthetic bodies.
"""

import io
import json

import pytest

from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.anthropic import AnthropicModel
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.models.openai_compat import OpenAICompatModel
from harness.models.openai_responses import OpenAIResponsesModel
from harness.routing import Budget
from harness.tools.registry import ToolRegistry


class _Body(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _serve(monkeypatch, payload):
    wire = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    calls = []

    def _open(req, timeout=None):
        calls.append(req.full_url)
        return _Body(wire)

    monkeypatch.setattr("harness.models._transport._open", _open)
    return calls


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


_COMPLETE = {"id": "c1", "function": {"name": "task_complete",
                                      "arguments": '{"report":"synthetic"}'}}


def _compat_payload(finish, tools, usage, refusal=None):
    message = {"content": ""}
    if tools:
        message["tool_calls"] = [_COMPLETE]
    if refusal is not None:
        message["refusal"] = refusal
    body = {"choices": [{"message": message, "finish_reason": finish}]}
    if usage:
        body["usage"] = {"prompt_tokens": 5, "completion_tokens": 2}
    return body


def _anthropic_payload(stop, tools, usage):
    content = [{"type": "text", "text": ""}]
    if tools:
        content.append({"type": "tool_use", "id": "c1", "name": "task_complete",
                        "input": {"report": "synthetic"}})
    body = {"content": content, "stop_reason": stop}
    if usage:
        body["usage"] = {"input_tokens": 5, "output_tokens": 2}
    return body


def _responses_payload(status, tools, usage, refusal=False, item_status=None):
    output = []
    if refusal:
        output.append({"type": "message", "content": [
            {"type": "refusal", "refusal": "no"}]})
    if tools:
        item = {"type": "function_call", "call_id": "c1", "name": "task_complete",
                "arguments": '{"report":"synthetic"}'}
        if item_status is not None:
            item["status"] = item_status
        output.append(item)
    body = {"status": status, "output": output}
    if status == "incomplete":
        body["incomplete_details"] = {"reason": "max_output_tokens"}
    if usage:
        body["usage"] = {"input_tokens": 5, "output_tokens": 2}
    return body


# (adapter factory, payload, expected terminal stop)
_BLOCKED = []
for _tools in (True, False):
    for _usage in (True, False):
        _BLOCKED += [
            ("compat-content_filter", _compat, _compat_payload("content_filter", _tools, _usage),
             "refusal", _usage),
            ("compat-refusal-field", _compat, _compat_payload("stop", _tools, _usage, "no"),
             "refusal", _usage),
            ("compat-length", _compat, _compat_payload("length", _tools, _usage),
             "max_tokens", _usage),
            ("anthropic-refusal", _anthropic, _anthropic_payload("refusal", _tools, _usage),
             "refusal", _usage),
            ("anthropic-max_tokens", _anthropic, _anthropic_payload("max_tokens", _tools, _usage),
             "max_tokens", _usage),
            ("responses-failed", _responses, _responses_payload("failed", _tools, _usage),
             "error", _usage),
            ("responses-cancelled", _responses, _responses_payload("cancelled", _tools, _usage),
             "error", _usage),
            ("responses-incomplete", _responses,
             _responses_payload("incomplete", _tools, _usage), "max_tokens", _usage),
            ("responses-refusal", _responses,
             _responses_payload("completed", _tools, _usage, refusal=True), "refusal", _usage),
            ("responses-failed-refusal", _responses,
             _responses_payload("failed", _tools, _usage, refusal=True), "error", _usage),
        ]


@pytest.mark.parametrize("label,factory,payload,stop,usage", _BLOCKED,
                         ids=[f"{b[0]}-tools{bool(b[2])}-{i}" for i, b in enumerate(_BLOCKED)])
def test_terminal_status_takes_precedence_over_tool_calls(
        monkeypatch, label, factory, payload, stop, usage):
    _serve(monkeypatch, payload)
    turn = factory().complete([])
    assert turn.stop_reason == stop
    assert turn.tool_calls == []
    assert not turn.wants_tools
    if usage:
        assert (turn.input_tokens, turn.output_tokens) == (5, 2)
        assert turn.usage_known is True
    else:
        assert turn.usage_known is False


@pytest.mark.parametrize("factory,payload", [
    (_compat, _compat_payload("tool_calls", False, True)),
    (_anthropic, _anthropic_payload("tool_use", False, True)),
    (_anthropic, _anthropic_payload("end_turn", True, True)),
    (_responses, _responses_payload("completed", True, True, item_status="in_progress")),
    (_responses, _responses_payload("completed", True, True, item_status="incomplete")),
])
def test_contradictory_envelope_is_error_with_usage_preserved(monkeypatch, factory, payload):
    _serve(monkeypatch, payload)
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert turn.tool_calls == []
    assert (turn.input_tokens, turn.output_tokens, turn.usage_known) == (5, 2, True)


@pytest.mark.parametrize("factory,payload", [
    (_compat, _compat_payload("tool_calls", True, True)),
    (_compat, _compat_payload("stop", True, True)),
    (_compat, _compat_payload(None, True, True)),
    (_anthropic, _anthropic_payload("tool_use", True, True)),
    (_responses, _responses_payload("completed", True, True)),
    (_responses, _responses_payload("completed", True, True, item_status="completed")),
])
def test_valid_tool_use_positive_controls(monkeypatch, factory, payload):
    _serve(monkeypatch, payload)
    turn = factory().complete([])
    assert turn.stop_reason == "tool_use"
    assert [tc.name for tc in turn.tool_calls] == ["task_complete"]
    assert (turn.input_tokens, turn.output_tokens, turn.usage_known) == (5, 2, True)


def _envelope(factory, usage):
    if factory is _compat:
        body = {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
    elif factory is _anthropic:
        body = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    else:
        body = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": "ok"}]}]}
    if usage is not _ABSENT:
        body["usage"] = usage
    return body


_ABSENT = object()
_FIELDS = {_compat: ("prompt_tokens", "completion_tokens"),
           _anthropic: ("input_tokens", "output_tokens"),
           _responses: ("input_tokens", "output_tokens")}
_FACTORIES = [_compat, _anthropic, _responses]


@pytest.mark.parametrize("factory", _FACTORIES)
@pytest.mark.parametrize("usage", [_ABSENT, None, {}])
def test_missing_usage_is_unknown_not_zero(monkeypatch, factory, usage):
    _serve(monkeypatch, _envelope(factory, usage))
    turn = factory().complete([])
    assert turn.stop_reason == "end_turn"
    assert turn.usage_known is False


@pytest.mark.parametrize("factory", _FACTORIES)
@pytest.mark.parametrize("missing", [0, 1])
@pytest.mark.parametrize("absent_as", ["omitted", "null"])
def test_partial_usage_preserves_the_reported_counter(monkeypatch, factory, missing,
                                                      absent_as):
    fields = _FIELDS[factory]
    usage = {fields[1 - missing]: 9}
    if absent_as == "null":
        usage[fields[missing]] = None
    _serve(monkeypatch, _envelope(factory, usage))
    turn = factory().complete([])
    assert turn.usage_known is False
    counts = (turn.input_tokens, turn.output_tokens)
    assert counts[1 - missing] == 9


@pytest.mark.parametrize("factory", _FACTORIES)
@pytest.mark.parametrize("bad", [True, False, "3", -1, 1.5, 3.0, [], {}])
def test_malformed_counter_is_error_with_unknown_usage(monkeypatch, factory, bad):
    fields = _FIELDS[factory]
    _serve(monkeypatch, _envelope(factory, {fields[0]: 7, fields[1]: bad}))
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert turn.usage_known is False
    assert turn.input_tokens == 7


@pytest.mark.parametrize("factory", _FACTORIES)
@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity", b"1e999"])
def test_nonfinite_counter_is_error_with_unknown_usage(monkeypatch, factory, literal):
    fields = _FIELDS[factory]
    body = json.dumps(_envelope(factory, {fields[0]: 7, fields[1]: 0})).encode()
    body = body.replace(f'"{fields[1]}": 0'.encode(), f'"{fields[1]}": '.encode() + literal)
    _serve(monkeypatch, body)
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert turn.usage_known is False


@pytest.mark.parametrize("factory", _FACTORIES)
def test_known_zero_usage_is_known(monkeypatch, factory):
    fields = _FIELDS[factory]
    _serve(monkeypatch, _envelope(factory, {fields[0]: 0, fields[1]: 0}))
    turn = factory().complete([])
    assert turn.stop_reason == "end_turn"
    assert (turn.input_tokens, turn.output_tokens, turn.usage_known) == (0, 0, True)


@pytest.mark.parametrize("factory,broken", [
    (_compat, {"choices": [{"message": {"tool_calls": [{"function": {}}]}}]}),
    (_anthropic, {"content": [{"type": "text", "text": 42}]}),
    (_responses, {"output": [{"type": "function_call", "call_id": "x"}],
                  "status": "completed"}),
])
def test_malformed_result_keeps_intact_usage(monkeypatch, factory, broken):
    fields = _FIELDS[factory]
    broken = dict(broken, usage={fields[0]: 7, fields[1]: 3})
    _serve(monkeypatch, broken)
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert (turn.input_tokens, turn.output_tokens, turn.usage_known) == (7, 3, True)


@pytest.mark.parametrize("factory", _FACTORIES)
def test_unparseable_success_body_is_unknown_usage(monkeypatch, factory):
    _serve(monkeypatch, b"not json")
    turn = factory().complete([])
    assert turn.stop_reason == "error"
    assert turn.usage_known is False


# -- loop: refused/blocked turns never dispatch; unknown usage stops metered runs


def _loop(tmp_path, model, budget):
    return AgentLoop(role="worker", model=model, registry=ToolRegistry(),
                     events=EventLog(tmp_path / "run", echo=False), budget=budget,
                     max_steps=5)


def _events(tmp_path):
    path = tmp_path / "run" / "events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.parametrize("label,factory,payload,stop,usage",
                         [b for b in _BLOCKED if b[4]][:10])
def test_blocked_envelope_never_reaches_tool_dispatch(
        tmp_path, monkeypatch, label, factory, payload, stop, usage):
    _serve(monkeypatch, payload)
    result = _loop(tmp_path, factory(), Budget(max_usd=10, max_tokens=10_000)).run(
        "system", "task")
    kinds = [e["kind"] for e in _events(tmp_path)]
    assert result.stop != "complete"
    assert "task_complete" not in kinds
    assert "tool_result" not in kinds


def _mock(turns, unmetered=False):
    return MockModel(ModelSpec(name="mid", provider="mock", model_id="mock",
                               unmetered=unmetered), script=list(turns))


def _complete_turn(**usage):
    return AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
        ToolCall(id="c1", name="task_complete", arguments={"report": "done"})], **usage)


def test_unknown_usage_stops_metered_loop_before_dispatch(tmp_path):
    model = _mock([_complete_turn(input_tokens=4, usage_known=False)])
    budget = Budget(max_usd=10, max_tokens=10_000)
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "budget"
    assert result.detail.get("accounting") == "unknown"
    assert len(model.calls) == 1
    assert budget.accounting_unknown is True
    assert budget.exhausted is True
    assert budget.spent_tokens == 4
    assert "task_complete" not in [e["kind"] for e in _events(tmp_path)]


def test_unknown_usage_on_error_turn_is_not_retried(tmp_path):
    model = _mock([AssistantTurn(content="provider_response_error: x",
                                 stop_reason="error", usage_known=False),
                   _complete_turn(input_tokens=1, output_tokens=1)])
    result = _loop(tmp_path, model, Budget(max_usd=10, max_tokens=10_000)).run(
        "system", "task")
    assert result.stop == "budget"
    assert len(model.calls) == 1


def test_unknown_usage_latches_parent_budget_from_parallel_child(tmp_path):
    parent = Budget(max_usd=10, max_tokens=10_000)
    child = parent.child()
    model = _mock([_complete_turn(usage_known=False)])
    result = _loop(tmp_path, model, child).run("system", "task")
    assert result.stop == "budget"
    assert parent.accounting_unknown is True
    assert parent.exhausted is True


def test_explicitly_unmetered_tier_continues_on_unknown_usage(tmp_path):
    model = _mock([_complete_turn(input_tokens=3, usage_known=False)], unmetered=True)
    budget = Budget(max_usd=10, max_tokens=10_000)
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "complete"
    assert budget.accounting_unknown is False
    assert budget.spent_tokens == 3


def test_known_usage_positive_control(tmp_path):
    model = _mock([_complete_turn(input_tokens=3, output_tokens=2)])
    budget = Budget(max_usd=10, max_tokens=10_000)
    result = _loop(tmp_path, model, budget).run("system", "task")
    assert result.stop == "complete"
    assert budget.spent_tokens == 5
    assert budget.accounting_unknown is False
