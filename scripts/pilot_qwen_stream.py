"""Offline preparation and interpretation of a separate Qwen streaming review.

No dispatch command or live approval is provided here. The existing private
capture transport bounds and retains wire bytes before this parser sees them.
Consumed non-streaming proposals and their request hashes remain unchanged.
"""
from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
import hashlib
from pathlib import Path

from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_contract import PilotRefusal, QWEN_MODEL
from scripts.pilot_evidence_handoff import _encode, validate_review
from scripts.pilot_evidence_review import LIMITS, REQUEST_SHA256, RUNWAY_S, TIMING_POLICY, _request
from scripts.pilot_execution import implementation_hashes, require
from scripts.pilot_qwen import _strict_json, _unknown_usage, _usage
from scripts.pilot_qwen_capture import EvidenceReviewQwenTransport
from scripts.pilot_qwen_smoke import _save


POLICY = {"schema": "harnessie-qwen-stream-review/1", "framing": "SSE",
          "terminal": "[DONE] after one stop and one final usage receipt",
          "missing_usage": "unknown and refuse", "incomplete_answer": "refuse",
          "reasoning": "private raw capture only", "retries": 0}


def streaming_request(original: bytes) -> bytes:
    """Change only streaming fields on the exact 17-source original request."""
    _request(original)
    data = _strict_json(original)
    require(data["stream"] is False and "stream_options" not in data, "request_drift")
    data["stream"] = True
    data["stream_options"] = {"include_usage": True}
    raw = _encode(data)
    require(len(raw) <= LIMITS.max_input_bytes, "input_limit_exceeded")
    return raw


def prepare(root: Path, original: bytes) -> dict:
    """Seal a private offline candidate, with no identity I/O or live authority."""
    raw = streaming_request(original)
    proposal = {"schema": "harnessie-qwen-stream-preparation/1",
                "status": "offline_preparation_not_authorization", "live_allowance": 0,
                "original_request_sha256": REQUEST_SHA256,
                "request_sha256": hashlib.sha256(raw).hexdigest(), "request_bytes": len(raw),
                "limits": asdict(LIMITS), "policy": POLICY.copy(),
                "timing_policy": deepcopy(TIMING_POLICY), "minimum_runway_s": RUNWAY_S,
                "implementation_sha256": implementation_hashes(),
                "next_boundary": "fresh physical identity, approval policy and sealed consume-once execution",
                "semantic_acceptance": False, "human_arbitrated": False}
    ResponseCaptureStore(root, LIMITS.max_output_bytes)
    _save(root, "request.json", raw)
    _save(root, "proposal.json", proposal)
    return proposal


class StreamingEvidenceReviewQwenTransport(EvidenceReviewQwenTransport):
    """Reuse bounded private capture with an explicitly different wire request.

    This low-level transport is not an approval gateway. A future live runner
    must seal and consume fresh authority before using it. There is no CLI.
    """

    def __call__(self, payload, limits):
        require(type(payload) is bytes and len(payload) <= LIMITS.max_input_bytes, "request_drift")
        require(limits == LIMITS, "invalid_qwen_capture_config")
        data = _strict_json(payload)
        require(type(data) is dict and data.get("stream") is True
                and data.get("stream_options") == {"include_usage": True}, "request_drift")
        original = dict(data)
        original["stream"] = False
        del original["stream_options"]
        _request(_encode(original))
        return super().__call__(payload, limits)


def inspect_stream(raw: bytes, *, capture_complete: bool) -> dict:
    """Interpret retained bytes; never promote partial output to a review.

    Reasoning text stays in the private wire capture. Every usage object is
    retained even when another frame, identity, or answer fails validation.
    """
    failures = []
    reported_usage = []
    usage = _unknown_usage()
    content = []
    reasoning_bytes = 0
    finished = False
    done = False
    stream_id = None
    review = None

    def fail(code):
        if code not in failures:
            failures.append(code)

    if type(raw) is not bytes or len(raw) > LIMITS.max_output_bytes:
        raise PilotRefusal("output_limit_exceeded")
    if capture_complete is not True:
        fail("response_capture_incomplete")
    # A split network read, even inside UTF-8, is reconstructed before parsing.
    # An unterminated final SSE frame remains incomplete.
    blocks = raw.replace(b"\r\n", b"\n").split(b"\n\n")
    if blocks[-1].strip():
        fail("incomplete_stream_frame")
    for block in blocks[:-1]:
        if not block.strip():
            continue
        try:
            lines = block.decode("utf-8").split("\n")
            require(all(line.startswith("data:") or line.startswith(":") for line in lines),
                    "invalid_stream_frame")
            payload = "\n".join(line[5:].lstrip(" ") for line in lines if line.startswith("data:"))
            if not payload:
                continue
            if payload == "[DONE]":
                require(not done, "duplicate_stream_completion")
                done = True
                require(finished, "incomplete_review")
                continue
            data = _strict_json(payload)
            require(type(data) is dict, "invalid_stream_frame")
            if data.get("usage") is not None:
                reported_usage.append(data["usage"])
            require(not done, "duplicate_stream_completion")
            require(data.get("model") == QWEN_MODEL, "model_identity_mismatch")
            require(data.get("object") == "chat.completion.chunk"
                    and type(data.get("id")) is str and bool(data["id"]), "invalid_stream_frame")
            stream_id = stream_id or data["id"]
            require(data["id"] == stream_id, "stream_identity_drift")
            choices = data.get("choices")
            require(type(choices) is list, "choices_invalid")
            if data.get("usage") is not None and choices:
                require(len(choices) == 1 and type(choices[0]) is dict
                        and choices[0].get("finish_reason") is not None, "invalid_usage_frame")
            if not choices:
                require(finished and data.get("usage") is not None, "invalid_usage_frame")
                continue
            require(len(choices) == 1 and type(choices[0]) is dict
                    and type(choices[0].get("index")) is int and choices[0]["index"] == 0,
                    "choices_invalid")
            require(not finished, "duplicate_stream_completion")
            choice = choices[0]
            delta = choice.get("delta")
            require(type(delta) is dict, "invalid_stream_frame")
            require(not delta.get("tool_calls") and not delta.get("function_call"), "native_tool_calls_denied")
            require(set(delta) <= {"role", "content", "reasoning", "reasoning_content", "tool_calls", "function_call"},
                    "invalid_stream_delta")
            require(delta.get("role", "assistant") == "assistant", "invalid_stream_delta")
            for field in ("content", "reasoning", "reasoning_content"):
                value = delta.get(field)
                require(value is None or type(value) is str, "invalid_stream_delta")
                if value is not None:
                    value.encode("utf-8")
            require(not (delta.get("reasoning") is not None and delta.get("reasoning_content") is not None),
                    "ambiguous_reasoning")
            content.append(delta.get("content") or "")
            reasoning_bytes += len((delta.get("reasoning", delta.get("reasoning_content")) or "").encode())
            finish = choice.get("finish_reason")
            if finish is not None:
                finished = True
                require(finish == "stop", "incomplete_review")
        except PilotRefusal as exc:
            fail(exc.code)
        except (ValueError, TypeError, KeyError, UnicodeError):
            fail("invalid_stream_frame")
    if not done or not finished:
        fail("incomplete_review")
    if len(reported_usage) != 1:
        fail("model_usage_missing" if not reported_usage else "model_usage_ambiguous")
    else:
        try:
            usage = _usage(reported_usage[0])
            if usage["output_tokens"] > LIMITS.max_output_tokens:
                fail("output_tokens_exceeded")
        except PilotRefusal as exc:
            fail(exc.code)
    answer = "".join(content)
    if not failures:
        try:
            review = _strict_json(answer)
            validate_review(review)
        except (PilotRefusal, ValueError, TypeError):
            fail("invalid_review")
            review = None
    return {"schema": "harnessie-qwen-stream-inspection/1",
            "outcome": failures[0] if failures else "review_received", "failures": failures,
            "usage": usage, "raw_provider_usage": reported_usage,
            "response_shape": {"content_bytes": len(answer.encode()), "reasoning_bytes": reasoning_bytes},
            "review_received": not failures, "review": review,
            "semantic_acceptance": False, "human_arbitrated": False, "retries": 0}
