"""Provider adapters fail closed on malformed response envelopes."""

import json

import pytest

from harness.models import build_model
from harness.models.anthropic import AnthropicModel
from harness.models.base import Message, ModelSpec
from harness.models.openai_compat import OpenAICompatModel
from harness.models.openai_responses import OpenAIResponsesModel


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def _stub_response(monkeypatch, payload):
    wire = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda *_args, **_kwargs: _Response(wire))


def _anthropic():
    return AnthropicModel(ModelSpec(
        name="mid", provider="anthropic", model_id="test",
        supports_effort=False))


def _openai_compat():
    return OpenAICompatModel(ModelSpec(
        name="mid", provider="openai-compat", model_id="test",
        base_url="https://example.invalid/v1", supports_effort=False))


def _openai_responses():
    return OpenAIResponsesModel(ModelSpec(
        name="mid", provider="openai-responses", model_id="test",
        base_url="https://example.invalid/v1", supports_effort=True,
        max_tokens=512))


def test_openai_responses_provider_is_registered():
    assert isinstance(build_model(ModelSpec(
        name="mid", provider="openai-responses", model_id="test",
        base_url="https://example.invalid/v1")), OpenAIResponsesModel)


@pytest.mark.parametrize("payload", [
    b"not json",
    [],
    {"content": {}},
    {"content": [{"type": "text", "text": 42}]},
    {"content": [{"type": "tool_use", "id": "x", "name": "read_file",
                  "input": []}]},
    {"content": [], "usage": []},
    {"content": [], "usage": {"input_tokens": "many"}},
    {"content": [], "stop_reason": 42},
    {"content": [], "stop_reason": "future_stop"},
])
def test_anthropic_malformed_response_is_error_turn(monkeypatch, payload):
    _stub_response(monkeypatch, payload)
    turn = _anthropic().complete([])
    assert turn.stop_reason == "error"
    assert turn.content.startswith("provider_response_error:")
    assert turn.raw is None


@pytest.mark.parametrize("payload", [
    b"not json",
    [],
    {"choices": []},
    {"choices": ["not an object"]},
    {"choices": [{"message": None}]},
    {"choices": [{"message": {"content": {}}}]},
    {"choices": [{"message": {"tool_calls": {}}}]},
    {"choices": [{"message": {"tool_calls": [{"function": {}}]}}]},
    {"choices": [{"message": {}}], "usage": []},
    {"choices": [{"message": {}}], "usage": {"prompt_tokens": "many"}},
    {"choices": [{"message": {}, "finish_reason": 42}]},
    {"choices": [{"message": {}, "finish_reason": "future_stop"}]},
])
def test_openai_compat_malformed_response_is_error_turn(monkeypatch, payload):
    _stub_response(monkeypatch, payload)
    turn = _openai_compat().complete([])
    assert turn.stop_reason == "error"
    assert turn.content.startswith("provider_response_error:")
    assert turn.raw is None


def test_anthropic_valid_response_preserves_content_tools_and_usage(monkeypatch):
    _stub_response(monkeypatch, {
        "content": [
            {"type": "text", "text": "working"},
            {"type": "tool_use", "id": "call-1", "name": "read_file",
             "input": {"path": "README.md"}},
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 7, "output_tokens": 3},
    })
    turn = _anthropic().complete([])
    assert turn.stop_reason == "tool_use"
    assert turn.content == "working"
    assert turn.tool_calls[0].arguments == {"path": "README.md"}
    assert (turn.input_tokens, turn.output_tokens) == (7, 3)


def test_openai_compat_valid_response_preserves_content_tools_and_usage(monkeypatch):
    _stub_response(monkeypatch, {
        "choices": [{
            "message": {"content": "working", "tool_calls": [{
                "id": "call-1",
                "function": {"name": "read_file",
                             "arguments": '{"path":"README.md"}'},
            }]},
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    })
    turn = _openai_compat().complete([])
    assert turn.stop_reason == "tool_use"
    assert turn.content == "working"
    assert turn.tool_calls[0].arguments == {"path": "README.md"}
    assert (turn.input_tokens, turn.output_tokens) == (7, 3)


def test_openai_compat_content_filter_maps_to_refusal(monkeypatch):
    _stub_response(monkeypatch, {
        "choices": [{"message": {}, "finish_reason": "content_filter"}],
    })
    assert _openai_compat().complete([]).stop_reason == "refusal"


def test_openai_responses_preserves_reasoning_and_function_outputs(monkeypatch):
    captured = []
    replies = iter([
        {
            "id": "resp_1",
            "status": "completed",
            "output": [
                {"id": "rs_1", "type": "reasoning", "encrypted_content": "opaque"},
                {"id": "fc_1", "type": "function_call", "call_id": "call_1",
                 "name": "read_file", "arguments": '{"path":"README.md"}'},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 4},
        },
        {
            "id": "resp_2",
            "status": "completed",
            "output": [{
                "id": "msg_1", "type": "message", "role": "assistant",
                "content": [{"type": "output_text", "text": "done"}],
            }],
            "usage": {"input_tokens": 15, "output_tokens": 2},
        },
    ])

    def _capture(req, **_kwargs):
        captured.append(json.loads(req.data.decode()))
        return _Response(json.dumps(next(replies)).encode())

    monkeypatch.setattr("urllib.request.urlopen", _capture)
    model = _openai_responses()
    tools = [{"name": "read_file", "description": "Read one file",
              "parameters": {"type": "object"}}]
    initial = [Message(role="system", content="verify"),
               Message(role="user", content="inspect")]
    first = model.complete(initial, tools=tools, effort="high")
    assert first.stop_reason == "tool_use"
    assert first.tool_calls[0].id == "call_1"
    assert captured[0]["reasoning"] == {"effort": "high"}
    assert captured[0]["max_output_tokens"] == 512
    assert captured[0]["store"] is False
    assert captured[0]["include"] == ["reasoning.encrypted_content"]
    assert captured[0]["tools"][0] == {
        "type": "function", "name": "read_file", "description": "Read one file",
        "parameters": {"type": "object"},
    }

    initial.extend([
        Message(role="assistant", tool_calls=first.tool_calls),
        Message(role="tool", tool_call_id="call_1", name="read_file",
                content="contents"),
    ])
    second = model.complete(initial, tools=tools, effort="high")
    assert second.stop_reason == "end_turn"
    assert second.content == "done"
    assert captured[1]["input"][-3:] == [
        {"id": "rs_1", "type": "reasoning", "encrypted_content": "opaque"},
        {"id": "fc_1", "type": "function_call", "call_id": "call_1",
         "name": "read_file", "arguments": '{"path":"README.md"}'},
        {"type": "function_call_output", "call_id": "call_1",
         "output": "contents"},
    ]


def test_openai_responses_resets_state_for_a_new_conversation(monkeypatch):
    captured = []

    def _capture(req, **_kwargs):
        captured.append(json.loads(req.data.decode()))
        return _Response(json.dumps({
            "status": "completed",
            "output": [{"type": "reasoning", "encrypted_content": "opaque"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }).encode())

    monkeypatch.setattr("urllib.request.urlopen", _capture)
    model = _openai_responses()
    model.complete([Message(role="system", content="one"),
                    Message(role="user", content="first")])
    model.complete([Message(role="system", content="two"),
                    Message(role="user", content="second")])
    assert captured[0]["input"] == [{"role": "user", "content": "first"}]
    assert captured[1]["input"] == [{"role": "user", "content": "second"}]
    assert captured[1]["instructions"] == "two"


@pytest.mark.parametrize("payload", [
    b"not json",
    [],
    {"output": {}},
    {"output": ["not an object"]},
    {"output": [{"type": "function_call", "call_id": "call_1"}]},
    {"output": [], "usage": []},
    {"output": [], "usage": {"input_tokens": "many"}},
    {"output": [], "status": "future_status"},
])
def test_openai_responses_malformed_response_is_error_turn(monkeypatch, payload):
    _stub_response(monkeypatch, payload)
    turn = _openai_responses().complete([])
    assert turn.stop_reason == "error"
    assert turn.content.startswith("provider_response_error:")
    assert turn.raw is None


def test_openai_responses_refusal_maps_to_refusal(monkeypatch):
    _stub_response(monkeypatch, {
        "status": "completed",
        "output": [{"type": "message", "content": [
            {"type": "refusal", "refusal": "cannot comply"},
        ]}],
    })
    turn = _openai_responses().complete([])
    assert turn.stop_reason == "refusal"
    assert turn.content == "cannot comply"
