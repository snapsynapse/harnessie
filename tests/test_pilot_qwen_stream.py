"""Synthetic streaming fixtures only; never contact a model endpoint."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from scripts import pilot_evidence_review as legacy
from scripts import pilot_qwen_capture as capture
from scripts import pilot_qwen_stream as stream
from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_contract import PilotRefusal, QWEN_MODEL
from scripts.pilot_evidence_handoff import _encode
from tests.test_pilot_evidence_review import report, wire_request


def chunk(delta=None, finish=None, *, usage=None, choices=True, **extra):
    return {"id": "fixture-1", "model": QWEN_MODEL, "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}] if choices else [],
            "usage": usage, **extra}


def event(value):
    return b"data: " + (value.encode() if type(value) is str else
                         json.dumps(value, ensure_ascii=False).encode()) + b"\n\n"


def frames(*, usage=True, finish="stop", done=True, answer=None):
    text = json.dumps(report(summary="Synthetic café review"), ensure_ascii=False) if answer is None else answer
    values = [event(chunk({"role": "assistant", "reasoning": "PRIVATE REASONING"})),
              event(chunk({"content": text[:12]})), event(chunk({"content": text[12:]}, finish))]
    if usage:
        values.append(event(chunk(usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}, choices=False)))
    if done:
        values.append(event("[DONE]"))
    return b"".join(values)


def inspect(raw, complete=True):
    return stream.inspect_stream(raw, capture_complete=complete)


def test_request_only_changes_streaming_fields_and_offline_seal(tmp_path, wire_request, monkeypatch):
    monkeypatch.setattr(stream, "REQUEST_SHA256", hashlib.sha256(wire_request).hexdigest())
    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: pytest.fail("live socket"))
    raw = stream.streaming_request(wire_request)
    actual, original = json.loads(raw), json.loads(wire_request)
    assert actual.pop("stream_options") == {"include_usage": True}
    assert actual["stream"] is True
    actual["stream"] = False
    assert actual == original
    root = tmp_path / "offline"
    proposal = stream.prepare(root, wire_request)
    assert proposal["live_allowance"] == 0
    assert proposal["request_sha256"] == hashlib.sha256(raw).hexdigest()
    assert proposal["limits"] == json.loads((root / "proposal.json").read_text())["limits"]
    assert proposal["limits"]["max_output_tokens"] == 4096
    assert proposal["limits"]["timeout_s"] == 1200
    assert (root / "request.json").read_bytes() == raw
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    with pytest.raises(PilotRefusal):
        stream.prepare(root, wire_request)
    with pytest.raises(PilotRefusal, match="request_drift"):
        stream.streaming_request(wire_request + b" ")


def test_complete_stream_keeps_reasoning_private_and_usage_exact(capsys):
    result = inspect(frames())
    assert result["review_received"] is True
    assert result["review"]["stance"] == "abstain"
    assert result["usage"]["input_tokens"] == 10
    assert result["usage"]["output_tokens"] == 20
    assert result["response_shape"]["reasoning_bytes"] == len("PRIVATE REASONING")
    assert "PRIVATE REASONING" not in json.dumps(result)
    assert result["semantic_acceptance"] is result["human_arbitrated"] is False
    assert not capsys.readouterr().out


@pytest.mark.parametrize("width", [1, 2, 7, 61, 4096])
def test_split_utf8_and_frames_reassemble_under_capture(tmp_path, monkeypatch, wire_request, width):
    body = frames().replace(b"\n", b"\r\n")
    value, request = fake_transport(tmp_path, monkeypatch, wire_request, body, width=width)
    raw = value(request, legacy.LIMITS)
    assert Path(value.response_capture["path"]).read_bytes() == body
    assert inspect(raw)["review_received"] is True


@pytest.mark.parametrize("raw,complete,code", [
    (frames(done=False), True, "incomplete_review"),
    (frames(), False, "response_capture_incomplete"),
    (frames(finish="length"), True, "incomplete_review"),
    (frames(usage=False), True, "model_usage_missing"),
    (frames(answer='{"stance":'), True, "invalid_review"),
    (frames()[:-1], True, "incomplete_stream_frame"),
    (frames() + event("[DONE]"), True, "duplicate_stream_completion"),
    (event(chunk({"content": "x"}, "stop")) + event(chunk({}, "stop")) + event("[DONE]"), True, "duplicate_stream_completion"),
    (b"data: \xff\n\n" + frames(), True, "invalid_stream_frame"),
    (b"data: {broken}\n\n" + frames(), True, "invalid_stream_frame"),
    (b"event: unexpected\n\n" + frames(), True, "invalid_stream_frame"),
    (event(chunk({"tool_calls": [{"function": {"name": "run_shell"}}]})) + frames(), True, "native_tool_calls_denied"),
    (event(chunk({"reasoning": "a", "reasoning_content": "b"})) + frames(), True, "ambiguous_reasoning"),
    (event(chunk(model="other")) + frames(), True, "model_identity_mismatch"),
    (event(chunk(id="other")) + frames(), True, "stream_identity_drift"),
])
def test_refusals_preserve_final_usage_but_never_accept_partial(raw, complete, code):
    result = inspect(raw, complete)
    assert code in result["failures"]
    assert result["review_received"] is False and result["review"] is None
    if code == "model_usage_missing":
        assert all(v is None for v in result["usage"].values())
    elif b'"prompt_tokens": 10' in raw:
        assert result["usage"]["input_tokens"] == 10


@pytest.mark.parametrize("usage,code", [
    ({"prompt_tokens": 10, "completion_tokens": 4097, "total_tokens": 4107}, "output_tokens_exceeded"),
    ({"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 31}, "model_usage_inconsistent"),
    ({"prompt_tokens": True, "completion_tokens": 20, "total_tokens": 21}, "model_usage_incomplete"),
])
def test_accounting_refusals_keep_raw_receipt(usage, code):
    raw = frames(usage=False, done=False) + event(chunk(usage=usage, choices=False)) + event("[DONE]")
    result = inspect(raw)
    assert code in result["failures"] and not result["review_received"]
    assert result["raw_provider_usage"] == [usage]


def test_multiple_receipts_remain_visible_and_cannot_be_deduplicated():
    extra = event(chunk(usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}, choices=False))
    result = inspect(frames(done=False) + extra + event("[DONE]"))
    assert "model_usage_ambiguous" in result["failures"]
    assert len(result["raw_provider_usage"]) == 2
    assert all(v is None for v in result["usage"].values())


def test_early_usage_cannot_substitute_for_final_usage():
    early = event(chunk(usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}))
    result = inspect(early + frames(usage=False))
    assert "invalid_usage_frame" in result["failures"]
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]


def test_exact_output_ceiling_and_usage_on_terminal_chunk():
    terminal = chunk({"content": json.dumps(report())}, "stop",
                     usage={"prompt_tokens": 10, "completion_tokens": 4096, "total_tokens": 4106})
    result = inspect(event(terminal) + event("[DONE]"))
    assert result["review_received"] is True
    assert result["usage"]["output_tokens"] == 4096


def fake_transport(tmp_path, monkeypatch, wire_request, body, *, timeout=False, width=None):
    actual = subprocess.Popen
    body_file = tmp_path / "fixture.sse"
    body_file.write_bytes(body)
    def launch(argv, **kwargs):
        code = "import sys,time\nbody=open(sys.argv[1],'rb').read()\n"
        code += (f"for i in range(0,len(body),{width or max(1,len(body))}):\n"
                 f" sys.stdout.buffer.write(body[i:i+{width or max(1,len(body))}]);sys.stdout.flush()\n")
        if width:
            code += " time.sleep(.001)\n"
        if timeout:
            code += "time.sleep(10)\n"
        return actual([sys.executable, "-c", code, str(body_file)], **kwargs)
    monkeypatch.setattr(capture.subprocess, "Popen", launch)
    value = stream.StreamingEvidenceReviewQwenTransport(ResponseCaptureStore(tmp_path / "responses", 128000).reserve(1))
    if timeout:
        monkeypatch.setattr(value, "_transport_config", lambda _limits: {"timeout_s": .3, "max_output_bytes": 128000})
    return value, stream.streaming_request(wire_request)


def test_transport_captures_wire_before_parser_and_is_consumed(tmp_path, monkeypatch, wire_request):
    value, request = fake_transport(tmp_path, monkeypatch, wire_request, frames())
    raw = value(request, legacy.LIMITS)
    assert Path(value.response_capture["path"]).read_bytes() == frames()
    assert inspect(raw)["review_received"] is True
    with pytest.raises(PilotRefusal, match="transport_latched"):
        value(request, legacy.LIMITS)


def test_unicode_evidence_roundtrips_the_exact_original_wire(tmp_path, monkeypatch, wire_request):
    original = json.loads(wire_request)
    original["messages"][0]["content"] += " café"
    raw = _encode(original)
    monkeypatch.setattr(legacy, "REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(legacy, "REQUEST_BYTES", len(raw))
    value, request = fake_transport(tmp_path, monkeypatch, raw, frames())
    reconstructed = json.loads(request)
    reconstructed["stream"] = False
    del reconstructed["stream_options"]
    assert _encode(reconstructed) == raw
    assert inspect(value(request, legacy.LIMITS))["review_received"] is True


def test_timeout_retains_emitted_prefix_without_inventing_usage(tmp_path, monkeypatch, wire_request):
    raw = frames(usage=False, done=False)
    value, request = fake_transport(tmp_path, monkeypatch, wire_request, raw, timeout=True)
    with pytest.raises(PilotRefusal, match="process_timeout"):
        value(request, legacy.LIMITS)
    assert Path(value.response_capture["path"]).read_bytes() == raw
    result = inspect(raw, value.response_capture["capture_complete"])
    assert not result["review_received"]
    assert all(v is None for v in result["usage"].values())
    assert value.diagnostics["server_cancellation_confirmed"] is False


def test_storage_failure_refuses_but_in_memory_final_usage_survives(tmp_path, monkeypatch, wire_request):
    value, request = fake_transport(tmp_path, monkeypatch, wire_request, frames())
    def fail(*_a, **_k):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(value.reservation, "save", fail)
    raw = value(request, legacy.LIMITS)
    assert value.capture_failure == "response_capture_failed"
    result = inspect(raw, False)
    assert result["usage"]["output_tokens"] == 20
    assert not result["review_received"]


def test_overflow_is_retained_at_bound_plus_sentinel(tmp_path, monkeypatch, wire_request):
    value, request = fake_transport(tmp_path, monkeypatch, wire_request, b"x" * 150000)
    with pytest.raises(PilotRefusal, match="output_limit_exceeded"):
        value(request, legacy.LIMITS)
    raw = Path(value.response_capture["path"]).read_bytes()
    assert len(raw) == 128001
    with pytest.raises(PilotRefusal, match="output_limit_exceeded"):
        inspect(raw, False)
