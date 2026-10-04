"""Consume-once full-evidence timing probe, with no live services."""
from datetime import timedelta
import hashlib
import json
import socket

import pytest

from scripts import pilot_evidence_probe as probe
from scripts.pilot_contract import PilotRefusal, digest_json, QUESTION
from scripts.pilot_evidence_handoff import encode_request
from scripts.pilot_prepare import SOURCE_FILES, _identity
from tests.test_pilot_qwen import identity


@pytest.fixture
def original(monkeypatch):
    sources = [{"path": name, "content": "Synthetic evidence: " + name,
                **_identity(("Synthetic evidence: " + name).encode())} for name in SOURCE_FILES]
    raw = encode_request({"question": QUESTION, "category": "untrusted_evidence", "sources": sources})
    new = raw.replace(b'"max_tokens":4096,', b'"max_tokens":256,', 1)
    monkeypatch.setattr(probe, "ORIGINAL_REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(probe, "REQUEST_SHA256", hashlib.sha256(new).hexdigest())
    monkeypatch.setattr(probe, "REQUEST_BYTES", len(new))
    monkeypatch.setattr(probe, "local_qwen_identity", lambda *_: pytest.fail("live metadata"))
    return raw


def observed_identity():
    value = identity()
    value["harness_identity"] = probe.harness_identity()
    value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
    return value


def approved(tmp_path, original):
    root = tmp_path / "probe"
    now = probe.utc_now()
    proposal = probe.prepare(root, original, observed_identity(), now.isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers",
                "action": "execute_one_local_qwen_evidence_timing_probe", "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat()}
    return root, approval


def execute(root, approval, **kwargs):
    return probe.execute(root, approval, approval["proposal_sha256"],
                         identity_capture=kwargs.pop("identity_capture", observed_identity), **kwargs)


def response(*, content="PRIVATE incomplete report", reasoning="PRIVATE reasoning", finish="length",
             model="qwen3.8:latest", usage=None, message_extra=None):
    return json.dumps({"model": model, "choices": [{"finish_reason": finish, "message": {
        "role": "assistant", "content": content, "reasoning": reasoning, **(message_extra or {})}}],
        "usage": {"prompt_tokens": 48000, "completion_tokens": 256, "total_tokens": 48256}
        if usage is None else usage}).encode()


def test_prepare_changes_only_output_limit_and_is_private_offline(tmp_path, original):
    root, approval = approved(tmp_path, original)
    request = (root / "request.json").read_bytes()
    assert request == original.replace(b'"max_tokens":4096,', b'"max_tokens":256,', 1)
    before, after = json.loads(original), json.loads(request)
    before["max_tokens"] = 256
    assert before == after
    assert len(json.loads(after["messages"][1]["content"])["sources"]) == 17
    proposal = json.loads((root / "proposal.json").read_bytes())
    assert proposal["live_allowance"] == 0
    assert proposal["limits"] == {"max_calls": 1, "timeout_s": 300, "max_input_bytes": 256000,
        "max_evidence_bytes": 256000, "max_output_bytes": 128000, "max_output_tokens": 256}
    assert proposal["request_sha256"] == hashlib.sha256(request).hexdigest()
    assert proposal["declared_harness_identity"]["prompt_sha256"] == proposal["request_sha256"]
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    for args in [(None, None), (approval, None), (None, approval["proposal_sha256"])]:
        with pytest.raises(PilotRefusal, match="live_authority_required"):
            probe.execute(root, *args)
    assert not (root / "attempt").exists()


def test_prepare_never_uses_network(tmp_path, original, monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("network access")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    approved(tmp_path, original)


def test_wrong_original_rejected_before_artifacts(tmp_path, original):
    for raw in (b"{}", original + b" "):
        with pytest.raises(PilotRefusal, match="request_drift"):
            probe.prepare(tmp_path / "probe", raw, observed_identity(), probe.utc_now().isoformat())
    assert not (tmp_path / "probe").exists()


@pytest.mark.parametrize("content,reasoning,finish", [("", "PRIVATE reasoning only", "length"),
    (None, "PRIVATE reasoning only", "length"), ("not json", "", "stop"),
    ('{"stance":"abstain"}', "", "stop")])
def test_direct_response_measurement_retained_never_review_acceptance(tmp_path, original, content, reasoning, finish, capsys):
    root, approval = approved(tmp_path, original)
    raw = response(content=content, reasoning=reasoning, finish=finish)
    calls = []
    def transport(request, limits):
        assert request == (root / "request.json").read_bytes()
        assert limits == probe.LIMITS
        assert (root / "attempt/guard.json").exists()
        assert (root / "attempt/identity-before.json").exists()
        calls.append(request)
        return raw
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == "response_received"
    assert result["usage"]["input_tokens"] == 48000
    assert result["usage"]["output_tokens"] == 256
    assert result["response_shape"]["finish_reason"] == finish
    assert result["response_shape"]["content_bytes"] == len((content or "").encode())
    assert result["response_shape"]["reasoning_bytes"] == len(reasoning.encode())
    assert result["review_accepted"] is False
    assert result["evidence_ingestion"] == "unknown"
    assert result["semantic_acceptance"] is False
    assert result["delivered"] is True
    assert result["executed_tools"] == result["retries"] == 0
    assert "PRIVATE" not in json.dumps(result)
    assert (root / "attempt/responses/attempt-0001/stdout.bin").read_bytes() == raw
    assert result["response_capture"]["capture_complete"] is True
    assert (root / "attempt/identity-after.json").exists()
    assert capsys.readouterr().out == ""
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize("change,reason", [("request", "request_drift"),
    ("limits", "invalid_proposal"), ("implementation", "implementation_drift"),
    ("stale", "qwen_identity_stale"), ("runway", "insufficient_runway"),
    ("expired", "live_authority_expired"), ("action", "invalid_live_authority"),
    ("extra", "invalid_proposal"), ("mode", "unsafe_evidence_file"), ("symlink", "unsafe_evidence_file")])
def test_prelaunch_gates_refuse_without_attempt(tmp_path, original, change, reason):
    root, approval = approved(tmp_path, original)
    path = root / "proposal.json"
    proposal = json.loads(path.read_bytes())
    if change == "request":
        (root / "request.json").write_bytes(b"{}")
    elif change == "limits":
        proposal["limits"]["max_calls"] = 2
    elif change == "implementation":
        proposal["implementation_sha256"] = {}
    elif change == "stale":
        proposal["identity_checked_at"] = (probe.utc_now() - timedelta(minutes=16)).isoformat()
    elif change in {"runway", "expired"}:
        approval["expires_at"] = (probe.utc_now() + timedelta(seconds=329 if change == "runway" else -1)).isoformat()
    elif change == "action":
        approval["action"] = "execute_one_local_qwen_probe"
    elif change == "extra":
        proposal["extra"] = True
    elif change == "mode":
        (root / "request.json").chmod(0o644)
    elif change == "symlink":
        (root / "request.json").unlink()
        (root / "request.json").symlink_to(path)
    path.write_text(json.dumps(proposal))
    approval["proposal_sha256"] = digest_json(proposal)
    with pytest.raises(PilotRefusal, match=reason):
        execute(root, approval, identity_capture=lambda: pytest.fail("metadata"),
                transport=lambda *_: pytest.fail("dispatch"))
    assert not (root / "attempt").exists()


@pytest.mark.parametrize("failure", ["process_timeout", "transport_failed"])
def test_network_failure_and_timeout_are_unknown_not_zero_consumed(tmp_path, original, failure):
    root, approval = approved(tmp_path, original)
    captures = []
    def capture():
        captures.append(1)
        return observed_identity()
    def transport(*_):
        raise PilotRefusal(failure)
    result = execute(root, approval, identity_capture=capture, transport=transport)
    assert result["outcome"] == failure
    assert result["usage"]["input_tokens"] is None and result["usage"]["output_tokens"] is None
    assert result["transport_dispatched"] is True and result["delivered"] is None
    assert result["review_accepted"] is False
    assert len(captures) == 2
    assert (root / "attempt/outcome.json").exists()
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=transport)


@pytest.mark.parametrize("raw,reason", [(None, "malformed_response"), (b"broken json", "malformed_response"),
    (response(model="wrong"), "model_identity_mismatch"),
    (response(message_extra={"tool_calls": [{"name": "read_file"}]}), "native_tool_calls_denied"),
    (response(usage={"prompt_tokens": 3, "completion_tokens": 257, "total_tokens": 260}), "output_tokens_exceeded")])
def test_failed_validation_keeps_usage_when_available(tmp_path, original, raw, reason):
    root, approval = approved(tmp_path, original)
    result = execute(root, approval, transport=lambda *_: raw)
    assert result["outcome"] == reason
    assert result["usage"]["output_tokens"] == (None if raw in (None, b"broken json") else 257 if reason == "output_tokens_exceeded" else 256)
    assert result["review_accepted"] is False
    if raw is not None:
        assert (root / "attempt/responses/attempt-0001/stdout.bin").read_bytes() == raw


def test_post_identity_drift_keeps_usage(tmp_path, original):
    root, approval = approved(tmp_path, original)
    count = 0
    def capture():
        nonlocal count
        count += 1
        return observed_identity() if count == 1 else identity("d" * 64)
    result = execute(root, approval, identity_capture=capture, transport=lambda *_: response())
    assert result["outcome"] == "identity_drift"
    assert result["usage"]["output_tokens"] == 256


def test_pre_identity_mismatch_does_not_dispatch(tmp_path, original):
    root, approval = approved(tmp_path, original)
    result = execute(root, approval, identity_capture=lambda: identity("d" * 64),
                     transport=lambda *_: pytest.fail("dispatch"))
    assert result["outcome"] == "identity_before_invalid"
    assert result["transport_dispatched"] is False and result["delivered"] is False


@pytest.mark.parametrize("body,failed,known", [(response(), False, True),
    (response(), True, True), (b'{"usage":', True, False)])
def test_default_capture_transport_path_parses_retained_usage_before_answer_acceptance(tmp_path, original, monkeypatch, body, failed, known):
    root, approval = approved(tmp_path, original)
    calls = []
    class FakeCapturedTransport:
        capture_failure = None
        response_capture = None
        diagnostics = {"injected": True}
        def __init__(self, reservation, *, timeout_ceiling_s):
            assert timeout_ceiling_s == 300
            self.reservation = reservation
        def __call__(self, raw, limits):
            assert raw == (root / "request.json").read_bytes()
            assert limits == probe.LIMITS
            calls.append(1)
            self.response_capture = self.reservation.save(body, returncode=1 if failed else 0,
                process_failure="process_timeout" if failed else None)
            if failed:
                raise PilotRefusal("process_timeout")
            return body
    monkeypatch.setattr(probe, "CapturedQwenTransport", FakeCapturedTransport)
    original_parse = probe._strict_json
    def parse(raw):
        if raw == body:
            assert (root / "attempt/responses/attempt-0001/stdout.bin").read_bytes() == body
        return original_parse(raw)
    monkeypatch.setattr(probe, "_strict_json", parse)
    result = execute(root, approval)
    assert calls == [1]
    assert result["outcome"] == ("process_timeout" if failed else "response_received")
    assert result["usage"]["output_tokens"] == (256 if known else None)
    assert result["review_accepted"] is False


def test_capture_failure_keeps_usage(tmp_path, original, monkeypatch):
    from scripts.pilot_capture import ResponseCaptureReservation
    root, approval = approved(tmp_path, original)
    def fail(*_a, **_k):
        raise PilotRefusal("response_capture_failed")
    monkeypatch.setattr(ResponseCaptureReservation, "save", fail)
    result = execute(root, approval, transport=lambda *_: response())
    assert result["outcome"] == "response_capture_failed"
    assert result["usage"]["output_tokens"] == 256


def test_prewire_runway_rechecked_after_metadata(tmp_path, original, monkeypatch):
    root, approval = approved(tmp_path, original)
    before = probe.utc_now()
    def capture():
        monkeypatch.setattr(probe, "utc_now", lambda: before + timedelta(seconds=280))
        return observed_identity()
    result = execute(root, approval, identity_capture=capture, transport=lambda *_: pytest.fail("dispatch"))
    assert result["outcome"] == "insufficient_runway"
    assert result["transport_dispatched"] is False


def test_prewire_tampering_rechecked_after_metadata(tmp_path, original):
    root, approval = approved(tmp_path, original)
    def capture():
        (root / "request.json").write_bytes(b"{}")
        return observed_identity()
    result = execute(root, approval, identity_capture=capture, transport=lambda *_: pytest.fail("dispatch"))
    assert result["outcome"] == "request_drift"
    assert result["transport_dispatched"] is False


@pytest.mark.parametrize("elapsed,expected", [(300, "response_received"), (601, "live_authority_expired")])
def test_postwire_does_not_require_new_runway(tmp_path, original, monkeypatch, elapsed, expected):
    root, approval = approved(tmp_path, original)
    before = probe.utc_now()
    def transport(*_):
        monkeypatch.setattr(probe, "utc_now", lambda: before + timedelta(seconds=elapsed))
        return response()
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == expected
    assert result["usage"]["output_tokens"] == 256


@pytest.mark.parametrize("filename", ["guard.json", "outcome.json"])
def test_persistence_failure_never_retries(tmp_path, original, monkeypatch, filename):
    root, approval = approved(tmp_path, original)
    save = probe._save
    def fail(directory, name, data):
        if name == filename:
            raise OSError("disk full")
        save(directory, name, data)
    monkeypatch.setattr(probe, "_save", fail)
    calls = []
    with pytest.raises(PilotRefusal, match="evidence_persistence_failed"):
        execute(root, approval, transport=lambda *_: calls.append(1) or response())
    assert len(calls) == (0 if filename == "guard.json" else 1)
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=lambda *_: pytest.fail("retry"))
