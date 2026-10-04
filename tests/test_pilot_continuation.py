"""Offline admission boundaries, using only invented responses and identifiers."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_claude_code import ClaudeCodePilot, _RunResult
from scripts.pilot_contract import CLAUDE_MODEL, CallAllowance, PilotLimits
from scripts.pilot_policy import CLAUDE_MAX_HAIKU_CONTEXT, EXACT_MODEL_ONLY, HAIKU_MODEL
from scripts.pilot_stream import parse_stream_json


def _usage(output):
    return {"inputTokens": 2, "outputTokens": output, "cacheCreationInputTokens": 3,
            "cacheReadInputTokens": 5, "provider": "firstParty", "webSearchRequests": 0,
            "costUSD": 0.125}


def _events(output=4096, overhead=None):
    answer = {"content": "SYNTHETIC ONLY", "tool_calls": [], "stop_reason": "end_turn"}
    usage = {CLAUDE_MODEL: _usage(output)}
    if overhead is not None:
        usage[HAIKU_MODEL] = _usage(overhead)
    return [
        {"type": "system", "subtype": "init", "session_id": "synthetic-session",
         "tools": ["StructuredOutput"], "mcp_servers": [], "model": CLAUDE_MODEL},
        {"type": "assistant", "session_id": "synthetic-session", "parent_tool_use_id": None,
         "request_id": "synthetic-request", "message": {"role": "assistant",
         "model": CLAUDE_MODEL, "id": "synthetic-message", "content": [
             {"type": "tool_use", "id": "synthetic-formatter", "name": "StructuredOutput",
              "input": answer}]}},
        {"type": "user", "session_id": "synthetic-session", "parent_tool_use_id": None,
         "tool_use_result": "Structured output provided successfully", "message": {
             "role": "user", "content": [{"type": "tool_result", "tool_use_id": "synthetic-formatter",
             "content": "Structured output provided successfully"}]}},
        {"type": "result", "session_id": "synthetic-session", "is_error": False,
         "subtype": "success", "terminal_reason": "completed", "modelUsage": usage,
         "structured_output": answer, "result": json.dumps(answer)},
    ]


def _encode(events):
    return b"".join(json.dumps(event).encode() + b"\n" for event in events)


class _InjectedClaude(ClaudeCodePilot):
    def __init__(self, root, events, *, limit=4096, policy=EXACT_MODEL_ONLY):
        limits = PilotLimits(max_calls=1, max_output_tokens=limit)
        super().__init__(ModelSpec("synthetic", "pilot", CLAUDE_MODEL),
                         Path(sys.executable).resolve(), root, CallAllowance(limits),
                         policy=policy,
                         capture_store=ResponseCaptureStore(root / "captures", limits.max_output_bytes))
        self.response = _encode(events)
        self.process_calls = []

    def _run(self, argv, stdin):
        self.process_calls.append(argv)
        if argv[1:] == ["auth", "status", "--json"]:
            return _RunResult(b'{"loggedIn":true,"authMethod":"oauth_token","apiProvider":"firstParty"}', 0, None)
        return _RunResult(self.response, 0, None)


@pytest.mark.parametrize("limit,output", [(4096, 4096), (7, 7), (4096, 0)])
def test_output_at_or_below_configured_limit_is_admitted(tmp_path, limit, output):
    adapter = _InjectedClaude(tmp_path.resolve(), _events(output), limit=limit)
    turn = adapter.complete([Message(role="user", content="SYNTHETIC ONLY")])
    assert turn.stop_reason == "end_turn"
    assert turn.output_tokens == output
    assert adapter.receipts[-1].status == "completed"


@pytest.mark.parametrize("limit,output", [(4096, 4097), (4096, 6740), (7, 8)])
def test_over_limit_retains_capture_and_usage_then_latches_without_retry(tmp_path, limit, output):
    events = _events(output)
    adapter = _InjectedClaude(tmp_path.resolve(), events, limit=limit)
    turn = adapter.complete([Message(role="user", content="SYNTHETIC ONLY")])
    assert turn.stop_reason == "error"
    receipt = adapter.receipts[-1]
    assert receipt.status == "refused"
    assert receipt.failure == "output_token_limit_exceeded"
    assert receipt.usage == {"input_tokens": 2, "output_tokens": output,
                             "cache_creation_input_tokens": 3, "cache_read_input_tokens": 5}
    assert receipt.reported_model_usages == (events[-1]["modelUsage"],)
    assert receipt.model_usage[CLAUDE_MODEL]["output_tokens"] == output
    assert receipt.response_capture["capture_complete"] is True
    assert Path(receipt.response_capture["path"]).read_bytes() == adapter.response
    assert receipt.inference_started is True
    assert receipt.dollar_cost is None
    adapter.complete([Message(role="user", content="TRY AGAIN")])
    assert adapter.receipts[-1].failure == "transport_latched"
    assert len(adapter.process_calls) == 2  # Injected auth and inference, no subprocesses.
    assert adapter.allowance.used == 1


@pytest.mark.parametrize("answer,overhead,expected", [
    (4095, 1, None), (4096, 1, "output_token_limit_exceeded"),
])
def test_output_limit_counts_all_reported_models(tmp_path, answer, overhead, expected):
    events = _events(answer, overhead)
    adapter = _InjectedClaude(tmp_path.resolve(), events, policy=CLAUDE_MAX_HAIKU_CONTEXT)
    turn = adapter.complete([Message(role="user", content="SYNTHETIC ONLY")])
    receipt = adapter.receipts[-1]
    assert receipt.failure == expected
    assert receipt.policy_disposition == "unclassified"
    assert receipt.usage["output_tokens"] == answer + overhead
    assert receipt.reported_model_usages == (events[-1]["modelUsage"],)
    assert set(receipt.model_usage) == {CLAUDE_MODEL, HAIKU_MODEL}
    assert turn.stop_reason == ("error" if expected else "end_turn")


def test_structural_refusal_precedes_token_cap_and_retains_usage(tmp_path):
    events = _events(6740)
    preliminary = copy.deepcopy(events[1])
    preliminary["request_id"] = "different-request"
    preliminary["message"]["id"] = "different-message"
    preliminary["message"]["content"] = [{"type": "text", "text": "SYNTHETIC ONLY"}]
    events.insert(1, preliminary)
    adapter = _InjectedClaude(tmp_path.resolve(), events)
    adapter.complete([Message(role="user", content="SYNTHETIC ONLY")])
    receipt = adapter.receipts[-1]
    assert receipt.failure == "conflicting_model_evidence"
    assert receipt.reported_model is None
    assert receipt.usage["output_tokens"] == 6740
    assert receipt.reported_model_usages == (events[-1]["modelUsage"],)


@pytest.mark.parametrize("mutation,expected", [
    ("changed_model", "conflicting_model_evidence"),
    ("synthetic_intermediary", "tool_result_binding_invalid"),
    ("unknown_intermediary", "tool_result_binding_invalid"),
    ("ambiguous_group", "structured_output_binding_missing"),
    ("duplicate_result", "stream_malformed"),
    ("mismatched_payload", "structured_output_binding_conflict"),
    ("missing_usage", "model_usage_incomplete"),
    ("native_tool", "native_tool_unapproved"),
])
def test_continuation_markers_never_relax_binding(mutation, expected):
    events = _events()
    if mutation == "changed_model":
        events[1]["message"]["model"] = "different-model"
    elif mutation in {"synthetic_intermediary", "unknown_intermediary"}:
        events.insert(1, {"type": "user", "session_id": "synthetic-session",
                         "parent_tool_use_id": None,
                         "isSynthetic": mutation == "synthetic_intermediary",
                         "message": {"role": "user", "content": [
                             {"type": "text", "text": "Output limit hit. Resume."}]}})
    elif mutation == "ambiguous_group":
        group = copy.deepcopy(events[1])
        group["request_id"] = "different-request"
        group["message"]["id"] = "different-message"
        events.insert(2, group)
    elif mutation == "duplicate_result":
        events.append(copy.deepcopy(events[-1]))
    elif mutation == "mismatched_payload":
        events[-1]["structured_output"] = {"content": "CHANGED"}
    elif mutation == "missing_usage":
        del events[-1]["modelUsage"][CLAUDE_MODEL]["outputTokens"]
    elif mutation == "native_tool":
        events[1]["message"]["content"][0]["name"] = "Bash"
    capture = parse_stream_json(_encode(events))
    assert capture.failure == expected
    assert capture.structured_output is None
    assert capture.reported_model_usages == tuple(
        event["modelUsage"] for event in events if event["type"] == "result")
