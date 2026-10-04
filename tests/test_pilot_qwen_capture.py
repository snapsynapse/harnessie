from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_contract import PilotLimits, PilotRefusal
from scripts.pilot_qwen_capture import (
    CapturedQwenTransport,
    EvidenceReviewQwenTransport,
    _evidence_review_request_child,
    _request_child,
    _validate_config,
    _validate_evidence_review_config,
)
import scripts.pilot_qwen_capture as capture
from test_pilot_qwen import complete, pilot, response


def transport(tmp_path, monkeypatch, body=b"not-json", code=None):
    actual = subprocess.Popen
    seen = []
    def fixture(argv, **kwargs):
        seen.append(argv)
        script = code or f"import sys; sys.stdout.buffer.write({body!r})"
        return actual([sys.executable, "-c", script], **kwargs)
    monkeypatch.setattr(capture.subprocess, "Popen", fixture)
    store = ResponseCaptureStore(tmp_path / "responses", 128000)
    value = CapturedQwenTransport(store.reserve(1), timeout_ceiling_s=300)
    return value, seen


def test_raw_retained_before_malformed_parse_with_private_modes(tmp_path, monkeypatch):
    value, seen = transport(tmp_path, monkeypatch)
    item = pilot(transport=value, limits=PilotLimits(max_calls=1, timeout_s=300))
    assert complete(item).content == "pilot_refusal: malformed_response"
    receipt = value.response_capture
    assert Path(receipt["path"]).read_bytes() == b"not-json"
    assert receipt["capture_complete"] is True
    assert os.stat(receipt["path"]).st_mode & 0o777 == 0o600
    assert os.stat(Path(receipt["path"]).parent).st_mode & 0o777 == 0o700
    assert json.loads(seen[0][-1])["timeout_s"] == 300
    assert value.diagnostics["supervisor_timeout_s"] == 300
    assert complete(item).content == "pilot_refusal: transport_latched"
    assert len(seen) == 1


def test_complete_response_capture_includes_reasoning_and_preserves_usage(tmp_path, monkeypatch):
    data = json.loads(response())
    data["choices"][0]["message"]["reasoning"] = "private reasoning fixture"
    raw = json.dumps(data).encode()
    value, _ = transport(tmp_path, monkeypatch, raw)
    item = pilot(transport=value, limits=PilotLimits(max_calls=1))
    assert complete(item).content == "ok"
    assert Path(value.response_capture["path"]).read_bytes() == raw
    assert item.receipts[-1].usage["output_tokens"] == 3


def test_capture_failure_refuses_but_complete_usage_survives(tmp_path, monkeypatch):
    value, _ = transport(tmp_path, monkeypatch, response())
    def fail(*args, **kwargs):
        raise PilotRefusal("response_capture_failed")
    monkeypatch.setattr(value.reservation, "save", fail)
    item = pilot(transport=value, limits=PilotLimits(max_calls=1))
    assert complete(item).content == "pilot_refusal: response_capture_failed"
    assert item.receipts[-1].raw_provider_usage["total_tokens"] == 5
    assert complete(item).content == "pilot_refusal: transport_latched"


def test_timeout_retains_partial_without_inventing_usage(tmp_path, monkeypatch):
    value, seen = transport(tmp_path, monkeypatch, code="import sys,time; sys.stdout.buffer.write(b'partial'); sys.stdout.flush(); time.sleep(10)")
    item = pilot(transport=value, limits=PilotLimits(max_calls=2, timeout_s=0.1))
    assert complete(item).content == "pilot_refusal: process_timeout"
    assert Path(value.response_capture["path"]).read_bytes() == b"partial"
    assert value.response_capture["capture_complete"] is False
    assert value.diagnostics["timeout_source"] == "supervisor"
    assert value.diagnostics["cleanup_attempted"] is True
    assert value.diagnostics["server_cancellation_confirmed"] is False
    assert all(v is None for v in item.receipts[-1].usage.values())
    assert complete(item).content == "pilot_refusal: transport_latched"
    assert len(seen) == 1


def test_overflow_capture_is_bounded_plus_one_sentinel(tmp_path, monkeypatch):
    value, _ = transport(tmp_path, monkeypatch, body=b"x" * 150000)
    with pytest.raises(PilotRefusal, match="output_limit_exceeded"):
        value(b"{}", PilotLimits(timeout_s=2))
    assert Path(value.response_capture["path"]).stat().st_size == 128001
    assert value.response_capture["overflow_detected"] is True
    assert value.response_capture["capture_complete"] is False


@pytest.mark.parametrize("timeout", [True, 301, 0, float("nan"), float("inf"), "300"])
def test_invalid_timeout_configuration_refused(tmp_path, timeout):
    reservation = ResponseCaptureStore(tmp_path / "responses", 128000).reserve(1)
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        CapturedQwenTransport(reservation, timeout_ceiling_s=timeout)


def test_unknown_child_configuration_fields_rejected():
    with pytest.raises(PilotRefusal):
        _validate_config({"timeout_s": 300, "max_output_bytes": 128000, "future": True})


def test_empty_timeout_capture_and_direct_callable_cannot_retry(tmp_path, monkeypatch):
    value, seen = transport(tmp_path, monkeypatch, code="import time; time.sleep(10)")
    with pytest.raises(PilotRefusal, match="process_timeout"):
        value(b"{}", PilotLimits(timeout_s=0.05))
    assert Path(value.response_capture["path"]).read_bytes() == b""
    assert value.diagnostics["first_body_byte_s"] is None
    assert value.diagnostics["cleanup_child_exited"] is True
    with pytest.raises(PilotRefusal, match="transport_latched"):
        value(b"{}", PilotLimits(timeout_s=300))
    assert len(seen) == 1


def test_successful_transport_itself_is_consume_once(tmp_path, monkeypatch):
    value, seen = transport(tmp_path, monkeypatch, response())
    assert value(b"{}", PilotLimits()) == response()
    with pytest.raises(PilotRefusal, match="transport_latched"):
        value(b"{}", PilotLimits())
    assert len(seen) == 1
    assert value.diagnostics["supervisor_timeout_s"] == 120
    assert json.loads(seen[0][-1])["timeout_s"] == 120


def test_process_start_failure_retains_empty_incomplete_capture(tmp_path, monkeypatch):
    value, _ = transport(tmp_path, monkeypatch)
    def fail(*args, **kwargs): raise OSError("private process start fixture")
    monkeypatch.setattr(capture.subprocess, "Popen", fail)
    with pytest.raises(PilotRefusal, match="process_start_failed"):
        value(b"{}", PilotLimits())
    assert Path(value.response_capture["path"]).read_bytes() == b""
    assert value.response_capture["capture_complete"] is False
    assert value.diagnostics["returncode"] is None


def test_child_timeout_retains_prefix_and_reports_distinct_source(tmp_path, monkeypatch):
    value, _ = transport(tmp_path, monkeypatch, code=(
        "import sys; sys.stdout.buffer.write(b'prefix'); "
        "sys.stderr.write('{\"failure\":\"http_timeout\",\"http_status\":200}'); sys.exit(2)"))
    with pytest.raises(PilotRefusal, match="process_timeout"):
        value(b"{}", PilotLimits())
    assert Path(value.response_capture["path"]).read_bytes() == b"prefix"
    assert value.diagnostics["timeout_source"] == "http_child"
    assert value.diagnostics["http_status"] == 200
    assert value.response_capture["capture_complete"] is False


def test_legacy_ceiling_is_120_while_optin_can_use_300():
    import scripts.pilot_qwen as legacy
    assert legacy._CHILD_TIMEOUT_S == 120


@pytest.mark.parametrize("config", [
    {"timeout_s": 300, "max_output_bytes": True},
    {"timeout_s": 300, "max_output_bytes": 128001},
    {"timeout_s": True, "max_output_bytes": 128000},
    {"timeout_s": 301, "max_output_bytes": 128000},
])
def test_child_rejects_invalid_caps(config):
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        _validate_config(config)


@pytest.mark.parametrize("child, timeout_s", [
    (_request_child, 300), (_evidence_review_request_child, 1200),
])
def test_child_passes_http_timeout_and_flushes_partial_before_error(monkeypatch, child, timeout_s):
    calls = []
    class Stream:
        def __init__(self): self.buffer = io.BytesIO(b"{}")
    stdin, stdout, stderr = Stream(), Stream(), Stream()
    stdout.buffer = io.BytesIO()
    stderr.buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    class Body:
        calls = 0
        def read1(self, size):
            self.calls += 1
            if self.calls == 1: return b"partial"
            raise TimeoutError()
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Opener:
        def open(self, request, *, timeout):
            calls.append((request.full_url, timeout))
            return Body()
    monkeypatch.setattr(capture, "build_opener", lambda *args: Opener())
    assert child({"timeout_s": timeout_s, "max_output_bytes": 128000}) == 2
    assert calls == [("http://127.0.0.1:11434/v1/chat/completions", timeout_s)]
    assert stdout.buffer.getvalue() == b"partial"
    assert json.loads(stderr.buffer.getvalue())["failure"] == "http_timeout"


def test_evidence_review_uses_separate_child_and_preserves_capture(tmp_path, monkeypatch):
    legacy, seen = transport(tmp_path, monkeypatch, response())
    value = EvidenceReviewQwenTransport(legacy.reservation)
    assert value(b"{}", PilotLimits(max_calls=1, timeout_s=1200)) == response()
    assert seen[0][2] == "--evidence-review-request-child"
    assert json.loads(seen[0][-1]) == {"timeout_s": 1200, "max_output_bytes": 128000}
    assert value.diagnostics["supervisor_timeout_s"] == 1200
    assert value.diagnostics["child_http_timeout_s"] == 1200
    assert Path(value.response_capture["path"]).read_bytes() == response()
    assert value.response_capture["capture_complete"] is True
    assert os.stat(value.response_capture["path"]).st_mode & 0o777 == 0o600
    with pytest.raises(PilotRefusal, match="transport_latched"):
        value(b"{}", PilotLimits(timeout_s=1200))
    assert len(seen) == 1


def test_legacy_transport_still_caps_large_limits_at_300(tmp_path, monkeypatch):
    value, seen = transport(tmp_path, monkeypatch, response())
    assert value(b"{}", PilotLimits(timeout_s=1200)) == response()
    assert seen[0][2] == "--captured-request-child"
    assert json.loads(seen[0][-1])["timeout_s"] == 300


@pytest.mark.parametrize("timeout_s", [120, 300, 1199, 1201, 2000])
def test_review_transport_refuses_other_timeouts_without_starting(tmp_path, monkeypatch, timeout_s):
    legacy, seen = transport(tmp_path, monkeypatch)
    value = EvidenceReviewQwenTransport(legacy.reservation)
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        value(b"{}", PilotLimits(timeout_s=timeout_s))
    assert seen == []
    with pytest.raises(PilotRefusal, match="transport_latched"):
        value(b"{}", PilotLimits(timeout_s=1200))


def test_review_transport_has_no_caller_selected_ceiling(tmp_path):
    slot = ResponseCaptureStore(tmp_path / "responses", 128000).reserve(1)
    with pytest.raises(TypeError):
        EvidenceReviewQwenTransport(slot, timeout_ceiling_s=2000)


@pytest.mark.parametrize("timeout_s", [True, 0, 300, 301, 1199, 1201, 2000,
                                      float("nan"), float("inf"), "1200"])
def test_review_validator_rejects_anything_but_fixed_profile(timeout_s):
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        _validate_evidence_review_config({"timeout_s": timeout_s, "max_output_bytes": 128000})


@pytest.mark.parametrize("config", [
    {"timeout_s": 1200, "max_output_bytes": 128001},
    {"timeout_s": 1200, "max_output_bytes": True},
    {"timeout_s": 1200, "max_output_bytes": 0},
    {"timeout_s": 1200, "max_output_bytes": 128000, "future": True},
])
def test_review_validator_preserves_exact_fields_and_byte_bounds(config):
    with pytest.raises(PilotRefusal, match="invalid_qwen_capture_config"):
        _validate_evidence_review_config(config)


@pytest.mark.parametrize("marker, timeout_s, accepted", [
    ("--captured-request-child", 300, True),
    ("--captured-request-child", 301, False),
    ("--captured-request-child", 1200, False),
    ("--evidence-review-request-child", 300, False),
    ("--evidence-review-request-child", 1200, True),
    ("--evidence-review-request-child", 1201, False),
    ("--evidence-review-request-child", 2000, False),
    ("--unknown-child", 1200, False),
])
def test_child_markers_have_disjoint_validation(monkeypatch, marker, timeout_s, accepted):
    seen = []
    def no_io(config):
        seen.append(config)
        return 0
    monkeypatch.setattr(capture, "_request_child_io", no_io)
    config = {"timeout_s": timeout_s, "max_output_bytes": 128000}
    assert capture._child_main(["script", marker, json.dumps(config)]) == (0 if accepted else 2)
    assert seen == ([config] if accepted else [])


def test_review_supervisor_expires_at_1200_without_real_wait(tmp_path, monkeypatch):
    clock = [10.0]
    selected = []
    arguments = []
    class Process:
        stdout = io.BytesIO()
        stderr = io.BytesIO()
        returncode = None
        def poll(self): return self.returncode
    process = Process()
    class Selector:
        def register(self, *args): pass
        def get_map(self): return {"pending": True}
        def select(self, timeout):
            selected.append(timeout)
            clock[0] += timeout
            return []
        def close(self): pass
    def start(argv, **kwargs):
        arguments.append((argv, kwargs))
        return process
    def kill(child):
        assert child is process
        child.returncode = -9
    monkeypatch.setattr(capture.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(capture.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(capture.subprocess, "Popen", start)
    monkeypatch.setattr(capture, "_kill_child_group", kill)
    slot = ResponseCaptureStore(tmp_path / "responses", 128000).reserve(1)
    value = EvidenceReviewQwenTransport(slot)
    with pytest.raises(PilotRefusal, match="process_timeout"):
        value(b"{}", PilotLimits(max_calls=1, timeout_s=1200))
    assert selected == [1200]
    assert json.loads(arguments[0][0][-1])["timeout_s"] == 1200
    assert arguments[0][1]["env"] == {"PYTHONPATH": str(Path(capture.__file__).resolve().parents[1])}
    assert arguments[0][1]["start_new_session"] is True
    assert value.diagnostics["elapsed_s"] == 1200
    assert value.diagnostics["timeout_source"] == "supervisor"
    assert value.diagnostics["cleanup_attempted"] is True
    assert value.diagnostics["cleanup_child_exited"] is True
    assert value.diagnostics["server_cancellation_confirmed"] is False
    assert Path(value.response_capture["path"]).read_bytes() == b""
    assert value.response_capture["capture_complete"] is False
