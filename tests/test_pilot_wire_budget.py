"""Offline wire/text budget regressions; synthetic SSE and no model access."""
from dataclasses import asdict
import io
import json
from pathlib import Path
import socket

import pytest

from scripts import pilot_qwen_stream as stream
from scripts import pilot_qwen_capture as capture
from scripts import pilot_evidence_review as legacy
from scripts import pilot_streaming_review as review
from scripts.pilot_contract import PilotRefusal
from tests.test_pilot_evidence_review import report, wire_request
from tests.test_pilot_qwen_stream import chunk, event, frames, fake_transport
from tests.test_pilot_streaming_review import stream_wire, prepared, execute, wire_factory


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("live network forbidden")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(review, "local_qwen_identity", forbidden)


def token_sized_stream():
    # Exercise framing overhead independently of small decoded text. Chunk
    # count is a synthetic stress dimension, not a claim about real tokens.
    pieces = [event(chunk({"reasoning": "r"}, system_fingerprint="x" * 256))] * 4095
    pieces += [event(chunk({"content": json.dumps(report())}, "stop")),
               event(chunk(usage={"prompt_tokens": 10, "completion_tokens": 4096,
                                  "total_tokens": 4106}, choices=False)), event("[DONE]")]
    return b"".join(pieces)


def test_framing_cannot_spend_the_decoded_text_allowance():
    body = token_sized_stream()
    assert 128000 < len(body) < 4 * 1024 * 1024
    result = stream.inspect_stream(body, capture_complete=True)
    assert result["review_received"] is True
    assert result["usage"]["output_tokens"] == 4096
    assert result["response_shape"]["reasoning_bytes"] == 4095
    assert result["semantic_acceptance"] is result["human_arbitrated"] is False


def test_fixed_limits_separate_wire_from_text_without_widening_legacy():
    assert asdict(stream.LIMITS) == asdict(legacy.LIMITS) | {"max_output_bytes": 4 * 1024 * 1024}
    assert legacy.LIMITS.max_output_bytes == stream.MAX_DECODED_TEXT_BYTES == 128000
    assert stream.LIMITS.timeout_s == 1200 and stream.LIMITS.max_output_tokens == 4096
    assert stream.LIMITS.max_calls == 1
    assert stream.POLICY["wire_max_bytes"] == 4 * 1024 * 1024
    assert stream.POLICY["decoded_text_max_bytes"] == 128000


def text_stream(answer, reasoning, *, field="reasoning", usage=True):
    body = event(chunk({field: reasoning})) + event(chunk({"content": answer}, "stop"))
    if usage:
        body += event(chunk(usage={"prompt_tokens": 10, "completion_tokens": 20,
                                   "total_tokens": 30}, choices=False))
    return body + event("[DONE]")


def test_exact_combined_utf8_text_boundary_accepts_without_returning_reasoning():
    answer = json.dumps(report(summary="Synthetic café review"), ensure_ascii=False)
    reason = "r" * (128000 - len(answer.encode()))
    result = stream.inspect_stream(text_stream(answer, reason), capture_complete=True)
    assert result["review_received"]
    assert sum(result["response_shape"].values()) == 128000
    assert len(json.dumps(result)) < 3000


@pytest.mark.parametrize("field", ["reasoning", "reasoning_content"])
def test_combined_text_overflow_refuses_and_keeps_final_usage(field):
    answer = json.dumps(report())
    reason = "🙂" * 32000
    result = stream.inspect_stream(text_stream(answer, reason, field=field), capture_complete=True)
    assert "decoded_output_limit_exceeded" in result["failures"]
    assert result["response_shape"]["reasoning_bytes"] == 128000
    assert not result["review_received"] and result["review"] is None
    assert result["usage"]["output_tokens"] == 20
    assert "🙂" not in json.dumps(result, ensure_ascii=False)


def test_content_overflow_refuses_even_valid_json_and_keeps_usage():
    answer = " " * 128000 + json.dumps(report())
    result = stream.inspect_stream(text_stream(answer, ""), capture_complete=True)
    assert "decoded_output_limit_exceeded" in result["failures"]
    assert not result["review_received"] and result["usage"]["output_tokens"] == 20


@pytest.mark.parametrize("field,other", [("reasoning", "reasoning_content"),
                                          ("reasoning_content", "reasoning")])
def test_null_alias_cannot_hide_reasoning_from_text_budget(field, other):
    body = event(chunk({field: "r" * 128001, other: None})) + frames()
    result = stream.inspect_stream(body, capture_complete=True)
    assert "decoded_output_limit_exceeded" in result["failures"]
    assert result["response_shape"]["reasoning_bytes"] >= 128001
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]


def at_wire_boundary():
    body = frames()
    padding = stream.LIMITS.max_output_bytes - len(body)
    return b":" + b"x" * (padding - 3) + b"\n\n" + body


def test_exact_wire_boundary_preserves_complete_capture_and_review(tmp_path, monkeypatch, wire_request):
    body = at_wire_boundary()
    assert len(body) == 4 * 1024 * 1024
    transport, request = fake_transport(tmp_path, monkeypatch, wire_request, body)
    raw = transport(request, stream.LIMITS)
    assert raw == body and transport.response_capture["capture_complete"]
    assert stream.inspect_stream(raw, capture_complete=True)["review_received"]
    with pytest.raises(PilotRefusal, match="output_limit_exceeded"):
        stream.inspect_stream(raw + b"x", capture_complete=True)


def test_expanded_capture_preserves_prefix_usage_on_wire_overflow(tmp_path, monkeypatch, wire_request):
    body = frames() + b"x" * stream.LIMITS.max_output_bytes
    transport, request = fake_transport(tmp_path, monkeypatch, wire_request, body)
    with pytest.raises(PilotRefusal, match="output_limit_exceeded"):
        transport(request, stream.LIMITS)
    receipt = transport.response_capture
    raw = Path(receipt["path"]).read_bytes()
    assert len(raw) == stream.LIMITS.max_output_bytes + 1
    assert receipt["overflow_detected"] and not receipt["capture_complete"]
    result = stream.inspect_stream(raw[:-1], capture_complete=False)
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]


def test_large_complete_wire_traverses_sealed_wrapper_and_private_receipt(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    result = execute(root, approval, factory=wire_factory(token_sized_stream()))
    assert result["review_received"] and result["usage"]["output_tokens"] == 4096
    assert result["response_capture"]["bytes"] > 128000
    assert result["response_capture"]["capture_complete"]
    assert "reasoning" not in json.dumps(result["reported_usage"])
    assert result["retries"] == result["executed_tools"] == 0


def test_original_stream_action_refuses_before_consuming_or_observing(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    approval["action"] = "execute_one_local_qwen_streaming_review"
    with pytest.raises(PilotRefusal, match="invalid_live_authority"):
        execute(root, approval, identity_capture=lambda: pytest.fail("identity observed"))
    assert not (root / "attempt").exists()


def test_text_policy_drift_invalidates_sealed_proposal_before_attempt(tmp_path, stream_wire, monkeypatch):
    root, approval = prepared(tmp_path, stream_wire)
    monkeypatch.setitem(review.POLICY, "decoded_text_max_bytes", 128001)
    with pytest.raises(PilotRefusal, match="invalid_proposal"):
        execute(root, approval)
    assert not (root / "attempt").exists()


def test_expanded_wire_does_not_accept_missing_usage_or_incomplete_capture():
    body = token_sized_stream()
    result = stream.inspect_stream(body, capture_complete=False)
    assert not result["review_received"] and result["usage"]["output_tokens"] == 4096
    blocks = body.split(b"\n\n")
    no_usage = b"\n\n".join(b for b in blocks if b'"prompt_tokens"' not in b)
    result = stream.inspect_stream(no_usage, capture_complete=True)
    assert "model_usage_missing" in result["failures"]
    assert all(v is None for v in result["usage"].values())


@pytest.mark.parametrize("config", [
    {"timeout_s": 1201, "max_output_bytes": 4194304},
    {"timeout_s": 1199, "max_output_bytes": 4194304},
    {"timeout_s": True, "max_output_bytes": 4194304},
    {"timeout_s": 1200, "max_output_bytes": 4194305},
    {"timeout_s": 1200, "max_output_bytes": 128000},
    {"timeout_s": 1200, "max_output_bytes": True},
    {"timeout_s": 1200, "max_output_bytes": 4194304.0},
    {"timeout_s": 1200, "max_output_bytes": 4194304, "extra": True},
])
def test_stream_child_rejects_any_other_profile(config):
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        capture._validate_streaming_review_config(config)


def test_separate_child_marker_and_legacy_children_remain_bounded(monkeypatch):
    config = {"timeout_s": 1200, "max_output_bytes": 4194304}
    seen = []
    monkeypatch.setattr(capture, "_request_child_io", lambda value: seen.append(value) or 0)
    assert capture._child_main(["fixture", "--streaming-review-request-child", json.dumps(config)]) == 0
    assert seen == [config]
    for validator in (capture._validate_config, capture._validate_evidence_review_config):
        with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
            validator(config)


def test_streaming_http_child_flushes_large_prefix_with_fixed_timeout(monkeypatch):
    class IO:
        def __init__(self, raw=b""): self.buffer = io.BytesIO(raw)
    stdin, stdout, stderr = IO(b"{}"), IO(), IO()
    monkeypatch.setattr(capture.sys, "stdin", stdin)
    monkeypatch.setattr(capture.sys, "stdout", stdout)
    monkeypatch.setattr(capture.sys, "stderr", stderr)
    body = io.BytesIO(b"x" * 200000)
    class Body:
        status = 200
        def read1(self, size):
            block = body.read(min(size, 65536))
            if not block: raise TimeoutError()
            return block
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Opener:
        def open(self, request, *, timeout):
            assert timeout == 1200
            assert request.full_url == "http://127.0.0.1:11434/v1/chat/completions"
            return Body()
    monkeypatch.setattr(capture, "build_opener", lambda *_: Opener())
    assert capture._streaming_review_request_child({"timeout_s": 1200, "max_output_bytes": 4194304}) == 2
    assert len(stdout.buffer.getvalue()) == 200000
    assert json.loads(stderr.buffer.getvalue())["failure"] == "http_timeout"
