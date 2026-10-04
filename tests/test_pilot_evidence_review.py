"""Single-use substantive review with fresh-at-start twenty-minute authority."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import socket

import pytest

from scripts import pilot_evidence_review as review
from scripts.pilot_contract import PilotRefusal, QUESTION, digest_json
from scripts.pilot_evidence_handoff import encode_request
from scripts.pilot_prepare import SOURCE_FILES, _identity
from tests.test_pilot_qwen import identity


@pytest.fixture
def wire_request(monkeypatch):
    sources = [{"path": name, "content": "Synthetic evidence " + name,
                **_identity(("Synthetic evidence " + name).encode())} for name in SOURCE_FILES]
    raw = encode_request({"question": QUESTION, "category": "untrusted_evidence", "sources": sources})
    monkeypatch.setattr(review, "REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(review, "REQUEST_BYTES", len(raw))
    monkeypatch.setattr(review, "local_qwen_identity", lambda *_: pytest.fail("live metadata"))
    return raw


def observed_identity():
    value = identity()
    value["harness_identity"] = review.harness_identity()
    value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
    return value


def approved(tmp_path, wire_request, *, identity_age_s=0, duration_s=1800):
    root = tmp_path / "review"
    now = review.utc_now()
    proposal = review.prepare(root, wire_request, observed_identity(),
                              (now - timedelta(seconds=identity_age_s)).isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers",
        "action": "execute_one_local_qwen_evidence_review", "approved_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=duration_s)).isoformat()}
    return root, approval


def execute(root, approval, **kwargs):
    return review.execute(root, approval, approval["proposal_sha256"],
                          identity_capture=kwargs.pop("identity_capture", observed_identity), **kwargs)


def report(**changes):
    return {"stance": "abstain", "summary": "PRIVATE substantive report",
            "findings": ["The proposed gate needs further evidence."], "citations": ["INTENT.md"],
            "uncertainties": ["Final acceptance remains unknown."]} | changes


def response(*, content=None, finish="stop", model="qwen3.8:latest", usage=None, message_extra=None):
    return json.dumps({"model": model, "choices": [{"finish_reason": finish, "message": {
        "role": "assistant", "content": json.dumps(report()) if content is None else content,
        "reasoning": "PRIVATE reasoning", **(message_extra or {})}}],
        "usage": {"prompt_tokens": 49808, "completion_tokens": 4000, "total_tokens": 53808}
        if usage is None else usage}).encode()


def test_prepare_exact_full_request_private_no_authority_or_network(tmp_path, wire_request, monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("network")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    root, approval = approved(tmp_path, wire_request)
    proposal = json.loads((root / "proposal.json").read_bytes())
    assert (root / "request.json").read_bytes() == wire_request
    assert proposal["limits"] == {"max_calls": 1, "timeout_s": 1200, "max_input_bytes": 256000,
        "max_evidence_bytes": 256000, "max_output_bytes": 128000, "max_output_tokens": 4096}
    assert proposal["live_allowance"] == 0
    assert proposal["timing_policy"]["identity_max_age_s_at_start"] == 900
    assert proposal["minimum_runway_s"] == 1320
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    for args in [(None, None), (None, approval["proposal_sha256"]), (approval, None)]:
        with pytest.raises(PilotRefusal, match="live_authority_required"):
            review.execute(root, *args)
    assert not (root / "attempt").exists()


def test_wrong_request_refuses_before_writes(tmp_path, wire_request):
    with pytest.raises(PilotRefusal, match="request_drift"):
        review.prepare(tmp_path / "review", wire_request + b" ", observed_identity(), review.utc_now().isoformat())
    assert not (tmp_path / "review").exists()


def test_returned_proposal_cannot_mutate_timing_policy(tmp_path, wire_request):
    proposal = review.prepare(tmp_path / "review", wire_request, observed_identity(), review.utc_now().isoformat())
    proposal["timing_policy"]["identity_max_age_s_at_start"] = 2000
    proposal["timing_policy"]["identity_checks"].clear()
    assert review.TIMING_POLICY["identity_max_age_s_at_start"] == 900
    assert len(review.TIMING_POLICY["identity_checks"]) == 3


@pytest.mark.parametrize("value", [report(), report(stance="recommend"), report(citations=[])])
def test_valid_native_review_saved_privately_never_semantic_acceptance(tmp_path, wire_request, value, capsys):
    root, approval = approved(tmp_path, wire_request)
    calls = []
    raw = response(content=json.dumps(value))
    def transport(actual, limits):
        assert actual == wire_request and limits == review.LIMITS
        assert (root / "attempt/guard.json").exists()
        assert (root / "attempt/identity-before.json").exists()
        calls.append(actual)
        return raw
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == "review_received"
    assert result["stance"] == value["stance"]
    assert result["usage"]["input_tokens"] == 49808
    assert result["usage"]["output_tokens"] == 4000
    assert result["semantic_acceptance"] is False and result["human_arbitrated"] is False
    assert result["structural_validation"]["schema_valid"] is True
    assert result["structural_validation"]["semantic_citation_validity"] == (
        "requires_human_review" if value["citations"] else "unknown")
    assert result["evidence_ingestion"] == "unknown" and result["delivered"] is True
    assert result["executed_tools"] == result["retries"] == 0
    assert json.loads((root / "attempt/parsed-review.json").read_bytes()) == value
    assert (root / "attempt/parsed-review.json").stat().st_mode & 0o777 == 0o600
    assert (root / "attempt/responses/attempt-0001/stdout.bin").read_bytes() == raw
    assert (root / "attempt/identity-after.json").exists()
    assert "PRIVATE" not in json.dumps(result)
    assert capsys.readouterr().out == ""
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize("content,finish,reason", [("incomplete", "length", "incomplete_review"),
    ("", "length", "incomplete_review"), (json.dumps(report()), "length", "incomplete_review"),
    ("not json", "stop", "invalid_review"), (json.dumps(report(citations=["wrong"])), "stop", "invalid_review"),
    (json.dumps(report(stance="recommend", citations=[])), "stop", "missing_citations")])
def test_incomplete_or_invalid_review_keeps_usage_without_acceptance(tmp_path, wire_request, content, finish, reason):
    root, approval = approved(tmp_path, wire_request)
    result = execute(root, approval, transport=lambda *_: response(content=content, finish=finish))
    assert result["outcome"] == reason
    assert result["usage"]["output_tokens"] == 4000
    assert result["review_received"] is False
    assert not (root / "attempt/parsed-review.json").exists()


@pytest.mark.parametrize("elapsed,expected", [(1200, "review_received"), (1801, "live_authority_expired")])
def test_twenty_minutes_may_exceed_original_identity_age_but_not_approval(tmp_path, wire_request, monkeypatch, elapsed, expected):
    now = datetime(2026, 10, 4, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    root, approval = approved(tmp_path, wire_request, identity_age_s=899)
    def transport(*_):
        monkeypatch.setattr(review, "utc_now", lambda: now + timedelta(seconds=elapsed))
        return response()
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == expected
    assert result["usage"]["output_tokens"] == 4000


@pytest.mark.parametrize("age,runway,reason", [(900, 1320, None), (901, 1800, "qwen_identity_stale"),
    (0, 1319, "insufficient_runway"), (0, 1320, None)])
def test_exact_start_freshness_and_runway_boundaries(tmp_path, wire_request, monkeypatch, age, runway, reason):
    now = datetime(2026, 10, 4, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    root, approval = approved(tmp_path, wire_request, identity_age_s=age, duration_s=runway)
    if reason:
        with pytest.raises(PilotRefusal, match=reason):
            execute(root, approval, transport=lambda *_: pytest.fail("dispatch"))
        assert not (root / "attempt").exists()
    else:
        assert execute(root, approval, transport=lambda *_: response())["outcome"] == "review_received"


@pytest.mark.parametrize("case,reason", [("age", "qwen_identity_stale"), ("runway", "insufficient_runway"),
    ("tamper", "request_drift")])
def test_prewire_rechecks_after_metadata(tmp_path, wire_request, monkeypatch, case, reason):
    now = datetime(2026, 10, 4, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    root, approval = approved(tmp_path, wire_request, identity_age_s=899 if case == "age" else 0)
    def capture():
        if case == "tamper":
            (root / "request.json").write_bytes(b"{}")
        else:
            monkeypatch.setattr(review, "utc_now", lambda: now + timedelta(seconds=2 if case == "age" else 481))
        return observed_identity()
    result = execute(root, approval, identity_capture=capture, transport=lambda *_: pytest.fail("dispatch"))
    assert result["outcome"] == reason and result["transport_dispatched"] is False


@pytest.mark.parametrize("change,reason", [("limits", "invalid_proposal"), ("implementation", "implementation_drift"),
    ("policy", "invalid_proposal"), ("wire_request", "request_drift"), ("expired", "live_authority_expired"),
    ("action", "invalid_live_authority"), ("mode", "unsafe_evidence_file"), ("symlink", "unsafe_evidence_file")])
def test_authority_and_tamper_refusals_before_attempt(tmp_path, wire_request, change, reason):
    root, approval = approved(tmp_path, wire_request)
    path = root / "proposal.json"
    proposal = json.loads(path.read_bytes())
    if change == "limits":
        proposal["limits"]["timeout_s"] = 1201
    elif change == "implementation":
        proposal["implementation_sha256"] = {}
    elif change == "policy":
        proposal["timing_policy"]["identity_max_age_s_at_start"] = 1800
    elif change == "wire_request":
        (root / "request.json").write_bytes(b"{}")
    elif change == "expired":
        approval["expires_at"] = (review.utc_now() - timedelta(seconds=1)).isoformat()
    elif change == "action":
        approval["action"] = "execute_one_local_qwen_evidence_timing_probe"
    elif change == "mode":
        (root / "request.json").chmod(0o644)
    elif change == "symlink":
        (root / "request.json").unlink()
        (root / "request.json").symlink_to(path)
    path.write_text(json.dumps(proposal))
    approval["proposal_sha256"] = digest_json(proposal)
    with pytest.raises(PilotRefusal, match=reason):
        execute(root, approval, transport=lambda *_: pytest.fail("dispatch"))
    assert not (root / "attempt").exists()


@pytest.mark.parametrize("case,reason", [("model", "model_identity_mismatch"), ("cap", "output_tokens_exceeded"),
    ("identity", "identity_drift"), ("capture", "response_capture_failed")])
def test_postcall_failures_keep_known_usage(tmp_path, wire_request, monkeypatch, case, reason):
    from scripts.pilot_capture import ResponseCaptureReservation
    root, approval = approved(tmp_path, wire_request)
    if case == "capture":
        def fail(*_a, **_k):
            raise PilotRefusal("response_capture_failed")
        monkeypatch.setattr(ResponseCaptureReservation, "save", fail)
    captures = []
    def capture():
        captures.append(1)
        return identity("d" * 64) if len(captures) == 2 and case == "identity" else observed_identity()
    raw = response(model="wrong") if case == "model" else response(usage={
        "prompt_tokens": 1, "completion_tokens": 4097, "total_tokens": 4098}) if case == "cap" else response()
    result = execute(root, approval, identity_capture=capture, transport=lambda *_: raw)
    assert result["outcome"] == reason
    assert result["usage"]["output_tokens"] == (4097 if case == "cap" else 4000)
    assert result["review_received"] is False
    assert len(captures) == 2


def test_timeout_unknown_usage_is_not_zero_and_no_retry(tmp_path, wire_request):
    root, approval = approved(tmp_path, wire_request)
    def timeout(*_):
        raise PilotRefusal("process_timeout")
    result = execute(root, approval, transport=timeout)
    assert result["outcome"] == "process_timeout"
    assert result["usage"]["input_tokens"] is None and result["usage"]["output_tokens"] is None
    assert result["delivered"] is None and result["review_received"] is False
    assert (root / "attempt/identity-after.json").exists()
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=lambda *_: pytest.fail("retry"))


def test_response_byte_cap_preserves_bounded_capture(tmp_path, wire_request):
    root, approval = approved(tmp_path, wire_request)
    raw = response(content="x" * 128001)
    result = execute(root, approval, transport=lambda *_: raw)
    assert result["outcome"] == "output_limit_exceeded"
    assert result["usage"]["output_tokens"] is None
    assert result["response_capture"]["overflow_detected"] is True
    assert result["response_capture"]["bytes"] == 128001
    assert result["review_received"] is False


def test_incomplete_capture_cannot_yield_accepted_receipt(tmp_path, wire_request, monkeypatch):
    from scripts.pilot_capture import ResponseCaptureReservation
    root, approval = approved(tmp_path, wire_request)
    save = ResponseCaptureReservation.save
    def incomplete(self, *args, **kwargs):
        result = save(self, *args, **kwargs)
        result["capture_complete"] = False
        return result
    monkeypatch.setattr(ResponseCaptureReservation, "save", incomplete)
    result = execute(root, approval, transport=lambda *_: response())
    assert result["outcome"] == "response_capture_incomplete"
    assert result["usage"]["output_tokens"] == 4000
    assert result["review_received"] is False


@pytest.mark.parametrize("raw", [response(), b'{"usage":'])
def test_new_transport_default_path_captures_before_parse_and_preserves_timeout_usage(tmp_path, wire_request, monkeypatch, raw):
    root, approval = approved(tmp_path, wire_request)
    class FakeTransport:
        capture_failure = None
        response_capture = None
        diagnostics = {"supervisor_timeout_s": 1200, "child_http_timeout_s": 1200}
        def __init__(self, reservation):
            self.reservation = reservation
        def __call__(self, actual, limits):
            assert actual == wire_request and limits.timeout_s == 1200
            self.response_capture = self.reservation.save(raw, returncode=1, process_failure="process_timeout")
            raise PilotRefusal("process_timeout")
    monkeypatch.setattr(review, "EvidenceReviewQwenTransport", FakeTransport)
    result = execute(root, approval)
    assert result["outcome"] == "process_timeout"
    assert result["usage"]["output_tokens"] == (4000 if raw == response() else None)
    assert result["review_received"] is False
    assert result["diagnostics"]["supervisor_timeout_s"] == 1200


@pytest.mark.parametrize("filename", ["guard.json", "parsed-review.json", "outcome.json"])
def test_persistence_failure_consumes_attempt(tmp_path, wire_request, monkeypatch, filename):
    root, approval = approved(tmp_path, wire_request)
    save = review._save
    def fail(directory, name, value):
        if name == filename:
            raise OSError("disk full")
        save(directory, name, value)
    monkeypatch.setattr(review, "_save", fail)
    calls = []
    if filename == "parsed-review.json":
        result = execute(root, approval, transport=lambda *_: calls.append(1) or response())
        assert result["outcome"] == "evidence_persistence_failed"
        assert result["usage"]["output_tokens"] == 4000
    else:
        with pytest.raises(PilotRefusal, match="evidence_persistence_failed"):
            execute(root, approval, transport=lambda *_: calls.append(1) or response())
    assert len(calls) == (0 if filename == "guard.json" else 1)
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=lambda *_: pytest.fail("retry"))
