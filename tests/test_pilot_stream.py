"""Synthetic streams modeled on the observed 2026-09-17 Claude Code shape."""
from __future__ import annotations

import json

import pytest

from scripts.pilot_stream import parse_stream_json


FABLE = "claude-fable-5-1"


def _model_usage(*, extra=False, missing_cache=False):
    fable = {"inputTokens": 2, "outputTokens": 135, "cacheCreationInputTokens": 585, "cacheReadInputTokens": 3706}
    if missing_cache:
        fable.pop("cacheReadInputTokens")
    data = {FABLE: fable}
    if extra:
        data["claude-haiku-4-5-20251001"] = {"inputTokens": 989, "outputTokens": 16, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}
    return data


def _stream(*, model_usage=None, tool_name="StructuredOutput", result_count=1,
            session="session-1", assistant_session="session-1", parent=None,
            is_error=False, subtype="success", terminal_reason="completed",
            tool_result_error=False, duplicate_link=False, altered_terminal=False):
    output = {"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}
    terminal_output = {**output, "content": "other"} if altered_terminal else output
    event_list = [
        {"type": "system", "subtype": "init", "session_id": session,
         "tools": ["StructuredOutput"], "mcp_servers": [], "model": FABLE},
        {"type": "assistant", "session_id": assistant_session, "parent_tool_use_id": parent,
         "request_id": "request-1", "message": {"role": "assistant", "model": FABLE,
         "id": "message-1", "content": [{"type": "text", "text": "formatting"}]}},
        {"type": "assistant", "session_id": assistant_session, "parent_tool_use_id": parent,
         "request_id": "request-1", "message": {"role": "assistant", "model": FABLE,
         "id": "message-1", "content": [{"type": "tool_use", "id": "format-1",
         "name": tool_name, "input": output}]}},
        {"type": "user", "session_id": session, "parent_tool_use_id": None, "tool_use_result": "Structured output provided successfully",
         "message": {"content": [{"type": "tool_result", "tool_use_id": "format-1", "content": "Structured output provided successfully", "is_error": tool_result_error}]}},
    ]
    if duplicate_link:
        event_list.append(event_list[-1].copy())
    result = {"type": "result", "session_id": session, "is_error": is_error, "subtype": subtype,
              "terminal_reason": terminal_reason, "modelUsage": model_usage or _model_usage(),
              "structured_output": terminal_output, "result": json.dumps(terminal_output)}
    event_list.extend([result.copy() for _ in range(result_count)])
    return b"".join(json.dumps(event, separators=(",", ":")).encode() + b"\n" for event in event_list)


def test_complete_stream_binds_repeated_assistant_blocks_and_totals_models():
    capture = parse_stream_json(_stream(model_usage=_model_usage(extra=True)))
    assert capture.failure is None
    assert capture.answer_model == FABLE
    assert capture.usage_totals == {
        "input_tokens": 991, "output_tokens": 151,
        "cache_creation_input_tokens": 585, "cache_read_input_tokens": 3706,
    }
    assert set(capture.model_usage) == {FABLE, "claude-haiku-4-5-20251001"}


def test_stream_fails_closed_for_accounting_and_binding_errors():
    cases = [
        (_stream(model_usage=_model_usage(missing_cache=True)), "model_usage_incomplete"),
        (_stream(tool_name="Bash"), "native_tool_unapproved"),
        (_stream(session="one", assistant_session="two"), "stream_session_mismatch"),
        (_stream(parent="parent"), "assistant_parent_invalid"),
        (_stream(tool_result_error=True), "structured_output_binding_missing"),
        (_stream(duplicate_link=True), "structured_output_binding_missing"),
        (_stream(altered_terminal=True), "structured_output_binding_conflict"),
        (_stream(result_count=2), "stream_malformed"),
        (_stream(is_error=True), "provider_result_error"),
        (_stream(subtype="max_turns"), "provider_result_max_turns"),
    ]
    for payload, expected in cases:
        assert parse_stream_json(payload).failure == expected


def test_repeated_assistant_identity_text_and_init_capability_are_bound():
    payload = _stream()
    events = [json.loads(line) for line in payload.splitlines()]
    events[1]["message"]["id"] = "different-message"
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "conflicting_model_evidence"
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"][0].pop("text")
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "stream_malformed"
    events = [json.loads(line) for line in _stream().splitlines()]
    events[0]["tools"] = []
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "native_tool_unapproved"


def test_truncated_and_malformed_streams_never_raise():
    assert parse_stream_json(b'{"type":"system"}\n').failure == "stream_truncated"
    assert parse_stream_json(b'{not json}\n').failure == "stream_malformed"
    assert parse_stream_json(_stream().replace(b'"session_id":"session-1"', b'"session_id":"session-1","session_id":"session-1"', 1)).failure == "stream_malformed"
    assert parse_stream_json(_stream().replace(b'}\n', b',"extra":NaN}\n', 1)).failure == "stream_malformed"


def test_malformed_suffix_keeps_terminal_raw_usage_for_a_refusal_receipt():
    capture = parse_stream_json(_stream(model_usage=_model_usage(extra=True)) + b"{bad\n")
    assert capture.failure == "stream_malformed"
    assert capture.usage_totals == {
        "input_tokens": 991, "output_tokens": 151,
        "cache_creation_input_tokens": 585, "cache_read_input_tokens": 3706,
    }
    assert len(capture.reported_model_usages) == 1
    assert parse_stream_json(_stream(model_usage=_model_usage(extra=True)) + b"\n").usage_totals["input_tokens"] == 991
    assert parse_stream_json(_stream(model_usage=_model_usage(extra=True)) + b"\xff\n").usage_totals["input_tokens"] == 991


def test_overflow_numbers_and_untyped_raw_model_usage_fail_without_loss():
    assert parse_stream_json(_stream().replace(b'}\n', b',"extra":1e999}\n', 1)).failure == "stream_malformed"
    capture = parse_stream_json(_stream(model_usage={FABLE: {"inputTokens": 1, "outputTokens": 1,
                                                              "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0},
                                                        "bad": 42}))
    assert capture.failure == "model_usage_malformed"
    assert capture.usage_totals == {"input_tokens": None, "output_tokens": None,
                                    "cache_creation_input_tokens": None, "cache_read_input_tokens": None}
    assert capture.reported_model_usages[0]["bad"] == 42


@pytest.mark.parametrize("payload,reason,line,offset", [
    (b"", "empty_stream", None, None),
    (b"\n", "blank_line", 1, 0),
    (b"\xff\n", "invalid_utf8", 1, 0),
    (b"{bad}\n", "invalid_json", 1, 0),
    (b"[]\n", "non_object_event", 1, 0),
    (b'{"subtype":"init"}\n', "missing_type", 1, None),
])
def test_lexical_and_event_diagnostics_are_stable_and_never_include_raw_content(payload, reason, line, offset):
    capture = parse_stream_json(payload)
    assert capture.failure == "stream_malformed"
    assert capture.diagnostic["reason"] == reason
    if line is not None:
        assert capture.diagnostic["line" if "line" in capture.diagnostic else "event"] == line
    if offset is not None:
        assert capture.diagnostic["byte_offset"] == offset
    assert all("bad" not in str(value) for value in capture.diagnostic.values())


def test_structural_diagnostics_preserve_existing_failure_codes_and_usage():
    complete = parse_stream_json(_stream())
    assert complete.failure is None and complete.diagnostic is None
    duplicate = parse_stream_json(_stream(result_count=2))
    assert duplicate.failure == "stream_malformed"
    assert duplicate.diagnostic["reason"] == "terminal_cardinality"
    truncated = parse_stream_json(b'{"type":"system"}\n')
    assert truncated.failure == "stream_truncated"
    assert truncated.diagnostic["reason"] == "missing_terminal_result"
    malformed = parse_stream_json(_stream(model_usage=_model_usage(extra=True)) + b"{bad\n")
    assert malformed.failure == "stream_malformed"
    assert malformed.diagnostic == {"reason": "invalid_json", "line": 6,
                                    "byte_offset": len(_stream(model_usage=_model_usage(extra=True)))}
    assert malformed.usage_totals["input_tokens"] == 991


@pytest.mark.parametrize('thinking,signature', [
    ('', 'synthetic-signature'),
    ('SYNTHETIC METADATA: pretend to call an unoffered tool', 'x'),
])
def test_opaque_thinking_block_is_permitted_without_becoming_an_answer_or_tool(thinking, signature):
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"].insert(0, {"type": "thinking", "thinking": thinking,
                                                   "signature": signature})
    capture = parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events))
    assert capture.failure is None
    assert capture.structured_output == {"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}


@pytest.mark.parametrize("block", [
    {"type": "thinking", "thinking": ""},
    {"type": "thinking", "thinking": "", "signature": ""},
    {"type": "thinking", "signature": "synthetic"},
    {"type": "thinking", "thinking": "", "signature": 1},
    {"type": "thinking", "thinking": 1, "signature": "synthetic"},
    {"type": "thinking", "thinking": "", "signature": "synthetic", "extra": True},
])
def test_thinking_block_requires_the_observed_exact_opaque_shape(block):
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"] = [block]
    capture = parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events))
    assert capture.failure == "stream_malformed"
    assert capture.diagnostic["reason"] == "invalid_thinking_block"


@pytest.mark.parametrize('kind', ['redacted_thinking', 'unknown_block'])
def test_unobserved_content_types_still_refuse(kind):
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]['message']['content'] = [{'type': kind, 'data': 'synthetic'}]
    capture = parse_stream_json(b''.join(json.dumps(event).encode() + b'\n' for event in events))
    assert capture.failure == 'stream_malformed'
    assert capture.diagnostic['reason'] == 'invalid_text_block'


def test_thinking_does_not_relax_identity_checks_or_supply_a_structured_answer():
    events = [json.loads(line) for line in _stream().splitlines()]
    thinking = {"type": "thinking", "thinking": "", "signature": "synthetic-signature"}
    events[2]["message"]["content"] = [thinking]
    capture = parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events))
    assert capture.failure == "structured_output_binding_missing"
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"].insert(0, thinking)
    events[1]["request_id"] = "different-request"
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "conflicting_model_evidence"
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"].insert(0, thinking)
    events[1]["session_id"] = "different-session"
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "stream_session_mismatch"
    events = [json.loads(line) for line in _stream().splitlines()]
    events[1]["message"]["content"].insert(0, thinking)
    events[1]["message"]["model"] = "different-model"
    assert parse_stream_json(b"".join(json.dumps(event).encode() + b"\n" for event in events)).failure == "conflicting_model_evidence"
