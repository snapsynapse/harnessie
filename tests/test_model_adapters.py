"""Provider adapters fail closed on malformed response envelopes."""

import json

import pytest

from harness.models.anthropic import AnthropicModel
from harness.models.base import ModelSpec
from harness.models.openai_compat import OpenAICompatModel


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
