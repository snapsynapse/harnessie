"""Fresh streaming authority, using synthetic identities and responses only."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts import pilot_qwen_capture as capture
from scripts import pilot_streaming_review as review
from scripts.pilot_contract import PilotRefusal, digest_json
from scripts.pilot_qwen_stream import streaming_request
from tests.test_pilot_evidence_review import wire_request
from tests.test_pilot_qwen import identity
from tests.test_pilot_qwen_stream import chunk, event, frames


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("live I/O forbidden")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(review, "local_qwen_identity", forbidden)


@pytest.fixture
def stream_wire(wire_request, monkeypatch):
    raw = streaming_request(wire_request)
    monkeypatch.setattr(review, "REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(review, "REQUEST_BYTES", len(raw))
    monkeypatch.setattr(review, "MODEL_DIGEST", "sha256:" + "b" * 64)
    return raw


def observed(**changes):
    value = identity()
    value["harness_identity"] = review.harness_identity()
    value.update(changes)
    value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
    return value


def prepared(tmp_path, stream_wire, *, age=0, runway=1800):
    root = tmp_path / "streaming"
    now = review.utc_now()
    proposal = review.prepare(root, stream_wire, observed(), (now - timedelta(seconds=age)).isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers", "action": review.ACTION,
                "approved_at": review.utc_now().isoformat(), "expires_at": (now + timedelta(seconds=runway)).isoformat()}
    return root, approval


def wire_factory(body=None, *, failure=None, callback=None, seen=None):
    body = frames() if body is None else body
    class Wire:
        def __init__(self, reservation):
            self.reservation = reservation
            self.response_capture = None
            self.capture_failure = None
            self.captured_stdout = None
            self.diagnostics = {"synthetic": True}

        def __call__(self, payload, limits):
            if seen is not None:
                seen.append(payload)
            assert (self.reservation.directory.parents[1] / "guard.json").is_file()
            assert limits == review.LIMITS
            if callback:
                callback()
            self.captured_stdout = body
            try:
                self.response_capture = self.reservation.save(body, returncode=0 if failure is None else None,
                                                             process_failure=failure)
            except (PilotRefusal, OSError):
                self.capture_failure = "response_capture_failed"
                self.response_capture = {"status": "failed"}
            if failure:
                raise PilotRefusal(failure)
            return body
    return Wire


def execute(root, approval, *, factory=None, identity_capture=observed):
    return review.execute(root, approval, approval["proposal_sha256"], identity_capture=identity_capture,
                          transport_factory=factory or wire_factory())


def test_prepare_is_private_offline_deeply_sealed_and_grants_no_call(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    proposal = json.loads((root / "proposal.json").read_bytes())
    assert (root / "request.json").read_bytes() == stream_wire
    assert proposal["live_allowance"] == 0
    assert proposal["schema"] == "harnessie-streaming-review/1"
    assert proposal["approval_action"] == "execute_one_local_qwen_streaming_review"
    assert proposal["limits"]["timeout_s"] == 1200 and proposal["limits"]["max_output_tokens"] == 4096
    assert proposal["minimum_runway_s"] == 1320
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    for args in [(None, None), (approval, None), (None, approval["proposal_sha256"])]:
        with pytest.raises(PilotRefusal, match="live_authority_required"):
            review.execute(root, *args)
    assert not (root / "attempt").exists()
    with pytest.raises(PilotRefusal):
        review.prepare(root, stream_wire, observed(), review.utc_now().isoformat())


def test_complete_review_stored_privately_never_returned_or_arbitrated(tmp_path, stream_wire, capsys):
    root, approval = prepared(tmp_path, stream_wire)
    seen = []
    result = execute(root, approval, factory=wire_factory(seen=seen))
    assert result["outcome"] == "review_received" and result["review_received"]
    assert result["stance"] == "abstain"
    assert result["usage"]["output_tokens"] == 20
    assert result["reported_usage_count"] == 1
    assert result["semantic_acceptance"] is result["human_arbitrated"] is False
    assert result["evidence_ingestion"] == "unknown"
    assert result["executed_tools"] == result["retries"] == 0
    assert result["outcome_persisted"] is True
    assert "PRIVATE" not in json.dumps(result) and "café" not in json.dumps(result)
    assert json.loads((root / "attempt/parsed-review.json").read_bytes())["stance"] == "abstain"
    assert (root / "attempt/parsed-review.json").stat().st_mode & 0o777 == 0o600
    assert json.loads((root / "attempt/outcome.json").read_bytes()) == result
    assert seen == [stream_wire] and capsys.readouterr().out == ""
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, factory=wire_factory(seen=seen))
    assert seen == [stream_wire]


@pytest.mark.parametrize("case", ["action", "request", "limits", "implementation", "policy", "mode", "symlink", "root"])
def test_drift_and_legacy_approval_refuse_before_any_observation(tmp_path, stream_wire, case):
    root, approval = prepared(tmp_path, stream_wire)
    proposal_path = root / "proposal.json"
    proposal = json.loads(proposal_path.read_text())
    if case == "action":
        approval["action"] = "execute_one_local_qwen_evidence_review"
    elif case == "request":
        (root / "request.json").write_bytes(b"{}")
    elif case == "mode":
        (root / "request.json").chmod(0o644)
    elif case == "symlink":
        content = (root / "request.json").read_bytes()
        (root / "request.json").unlink()
        (tmp_path / "other").write_bytes(content)
        (root / "request.json").symlink_to(tmp_path / "other")
    else:
        if case == "limits": proposal["limits"]["timeout_s"] = 1800
        if case == "implementation": proposal["implementation_sha256"] = {}
        if case == "policy": proposal["stream_policy"]["missing_usage"] = "accept"
        if case == "root": proposal["root"] = str(tmp_path / "other")
        proposal_path.write_text(json.dumps(proposal))
        approval["proposal_sha256"] = digest_json(proposal)
    with pytest.raises(PilotRefusal):
        execute(root, approval, identity_capture=lambda: pytest.fail("observation"))
    assert not (root / "attempt").exists()


@pytest.mark.parametrize("age,runway,reason", [(899, 1800, None), (901, 1800, "qwen_identity_stale"),
    (-1, 1800, "qwen_identity_stale"), (0, 1319, "insufficient_runway"), (900, 1320, None)])
def test_freshness_and_runway_edges(tmp_path, stream_wire, monkeypatch, age, runway, reason):
    now = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    if age > 900 or age < 0:
        with pytest.raises(PilotRefusal, match=reason):
            prepared(tmp_path, stream_wire, age=age, runway=runway)
        assert not (tmp_path / "streaming").exists()
    elif reason:
        root, approval = prepared(tmp_path, stream_wire, age=age, runway=runway)
        with pytest.raises(PilotRefusal, match=reason):
            execute(root, approval)
        assert not (root / "attempt").exists()
    else:
        root, approval = prepared(tmp_path, stream_wire, age=age, runway=runway)
        assert execute(root, approval)["review_received"] is True


@pytest.mark.parametrize("phase", ["identity", "factory"])
@pytest.mark.parametrize("case", ["request", "clock", "implementation"])
def test_last_moment_drift_consumes_guard_but_cannot_dispatch(tmp_path, stream_wire, monkeypatch, phase, case):
    now = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    root, approval = prepared(tmp_path, stream_wire, age=899)
    def change():
        if case == "request": (root / "request.json").write_bytes(b"{}")
        if case == "clock": monkeypatch.setattr(review, "utc_now", lambda: now + timedelta(seconds=2))
        if case == "implementation": monkeypatch.setattr(review, "implementation_hashes", lambda: {})
    def observe():
        if phase == "identity": change()
        return observed()
    def factory(reservation):
        if phase == "factory": change()
        return wire_factory(seen=[])(reservation)
    result = execute(root, approval, identity_capture=observe, factory=factory)
    assert not result["transport_dispatched"] and not result["review_received"]
    assert (root / "attempt/guard.json").exists()
    with pytest.raises(PilotRefusal):
        execute(root, approval)


@pytest.mark.parametrize("elapsed,expected", [(1200, "review_received"), (1801, "live_authority_expired")])
def test_postflight_keeps_usage_and_does_not_expire_start_identity_midcall(tmp_path, stream_wire, monkeypatch, elapsed, expected):
    now = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(review, "utc_now", lambda: now)
    root, approval = prepared(tmp_path, stream_wire, age=899)
    result = execute(root, approval, factory=wire_factory(callback=lambda: monkeypatch.setattr(
        review, "utc_now", lambda: now + timedelta(seconds=elapsed))))
    assert result["outcome"] == expected and result["usage"]["output_tokens"] == 20
    assert result["review_received"] == (elapsed == 1200)


@pytest.mark.parametrize("before", [True, False])
def test_physical_identity_drift_and_model_substitution(tmp_path, stream_wire, before):
    root, approval = prepared(tmp_path, stream_wire)
    count = 0
    def capture():
        nonlocal count
        count += 1
        return observed(server_version="changed") if before or count == 2 else observed()
    result = execute(root, approval, identity_capture=capture)
    assert result["outcome"] == ("identity_before_invalid" if before else "identity_drift")
    assert result["transport_dispatched"] is not before
    assert result["usage"]["output_tokens"] == (None if before else 20)
    assert not result["review_received"] and result["stance"] is None
    assert (root / "attempt" / ("identity-before.json" if before else "identity-after.json")).exists()


@pytest.mark.parametrize("body,reason", [(frames(usage=False), "model_usage_missing"),
    (frames(answer='{"stance":'), "invalid_review"), (frames(finish="length"), "incomplete_review"),
    (frames() + event("[DONE]"), "duplicate_stream_completion")])
def test_bad_stream_cannot_become_review(tmp_path, stream_wire, body, reason):
    root, approval = prepared(tmp_path, stream_wire)
    result = execute(root, approval, factory=wire_factory(body))
    assert reason in result["failures"] and not result["review_received"]
    assert not (root / "attempt/parsed-review.json").exists()


@pytest.mark.parametrize("failure", ["process_timeout", "transport_failed", "output_limit_exceeded"])
def test_failed_stream_keeps_observed_usage_and_refuses_retry(tmp_path, stream_wire, failure):
    root, approval = prepared(tmp_path, stream_wire)
    body = frames() + (b"x" * 130000 if failure == "output_limit_exceeded" else b"")
    result = execute(root, approval, factory=wire_factory(body, failure=failure))
    assert result["outcome"] == failure
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval)


@pytest.mark.parametrize("file", ["accounting.json", "parsed-review.json", "outcome.json"])
def test_storage_failures_preserve_usage_without_acceptance(tmp_path, stream_wire, monkeypatch, file):
    root, approval = prepared(tmp_path, stream_wire)
    save = review._save
    def fail(root, name, value):
        if name == file: raise OSError("PRIVATE disk failure")
        return save(root, name, value)
    monkeypatch.setattr(review, "_save", fail)
    result = execute(root, approval)
    assert "evidence_persistence_failed" in result["failures"]
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]
    assert result["outcome_persisted"] == (file != "outcome.json")
    assert "PRIVATE" not in json.dumps(result)


def test_timeout_and_receipt_write_failure_keep_in_memory_accounting(tmp_path, stream_wire, monkeypatch):
    root, approval = prepared(tmp_path, stream_wire)
    from scripts import pilot_capture
    write = pilot_capture._write_exclusive
    def fail(path, data):
        if path.name == "receipt.json": raise OSError("synthetic metadata failure")
        return write(path, data)
    monkeypatch.setattr(pilot_capture, "_write_exclusive", fail)
    result = execute(root, approval, factory=wire_factory(failure="process_timeout"))
    assert result["usage"]["output_tokens"] == 20
    assert "response_capture_failed" in result["failures"] and not result["review_received"]


def test_provider_usage_extensions_stay_private(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "reasoning": "PRIVATE injected text"}
    body = frames(usage=False, done=False) + event(chunk(usage=usage, choices=False)) + event("[DONE]")
    result = execute(root, approval, factory=wire_factory(body))
    assert result["review_received"] is True and "PRIVATE" not in json.dumps(result)
    private = json.loads((root / "attempt/accounting.json").read_text())
    assert private["raw_provider_usage"][0]["reasoning"] == usage["reasoning"]


def test_capture_receipt_hash_mismatch_refuses_but_preserves_usage(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    Base = wire_factory()
    class Tampered(Base):
        def __call__(self, payload, limits):
            raw = super().__call__(payload, limits)
            self.response_capture["sha256"] = "0" * 64
            return raw
    result = execute(root, approval, factory=Tampered)
    assert "response_capture_mismatch" in result["failures"]
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]


@pytest.mark.parametrize("field", ["content", "reasoning", "reasoning_content"])
def test_lone_surrogate_refuses_without_losing_later_usage(tmp_path, stream_wire, field):
    root, approval = prepared(tmp_path, stream_wire)
    invalid = b"data: " + json.dumps(chunk({field: chr(0xD800)})).encode() + b"\n\n"
    result = execute(root, approval, factory=wire_factory(invalid + frames()))
    assert "invalid_stream_frame" in result["failures"]
    assert result["usage"]["output_tokens"] == 20 and not result["review_received"]


def test_duplicate_numeric_receipts_survive_even_total_storage_failure(tmp_path, stream_wire, monkeypatch):
    root, approval = prepared(tmp_path, stream_wire)
    extra = event(chunk(usage={"prompt_tokens": 11, "completion_tokens": 21, "total_tokens": 32}, choices=False))
    body = frames(done=False) + extra + event("[DONE]")
    save = review._save
    def fail(root, name, value):
        if name in {"accounting.json", "outcome.json"}: raise OSError("synthetic disk failure")
        return save(root, name, value)
    monkeypatch.setattr(review, "_save", fail)
    from scripts import pilot_capture
    monkeypatch.setattr(pilot_capture, "_write_exclusive", lambda *_a: (_ for _ in ()).throw(OSError("disk")))
    result = execute(root, approval, factory=wire_factory(body))
    assert result["reported_usage"] == [{"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                                         {"prompt_tokens": 11, "completion_tokens": 21, "total_tokens": 32}]
    assert not result["review_received"] and not result["outcome_persisted"]


def test_concurrent_attempts_dispatch_at_most_once(tmp_path, stream_wire):
    root, approval = prepared(tmp_path, stream_wire)
    seen = []
    def run():
        try:
            return execute(root, approval, factory=wire_factory(seen=seen))["outcome"]
        except PilotRefusal as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: run(), range(2)))
    assert sorted(outcomes) == ["attempt_consumed", "review_received"]
    assert seen == [stream_wire]


def test_real_capture_transport_is_wired_without_network(tmp_path, stream_wire, monkeypatch):
    root, approval = prepared(tmp_path, stream_wire)
    original = subprocess.Popen
    body = tmp_path / "synthetic.sse"
    body.write_bytes(frames())
    def fixture(argv, **kwargs):
        assert argv[2] == "--evidence-review-request-child"
        return original([sys.executable, "-c", "import sys;sys.stdout.buffer.write(open(sys.argv[1],'rb').read())", str(body)], **kwargs)
    monkeypatch.setattr(capture.subprocess, "Popen", fixture)
    result = review.execute(root, approval, approval["proposal_sha256"], identity_capture=observed)
    assert result["review_received"] is True and result["usage"]["output_tokens"] == 20
    assert result["diagnostics"]["supervisor_timeout_s"] == 1200


@pytest.mark.parametrize("failure", ["stdout.bin", "receipt.json", "fsync"])
def test_real_transport_timeout_plus_disk_failure_preserves_usage(tmp_path, stream_wire, monkeypatch, failure):
    root, approval = prepared(tmp_path, stream_wire)
    from scripts import pilot_capture
    original = subprocess.Popen
    write = pilot_capture._write_exclusive
    sync = pilot_capture._fsync_directory
    body = tmp_path / "synthetic.sse"
    body.write_bytes(frames())
    def fixture(argv, **kwargs):
        def failed_write(path, data):
            if path.name == failure: raise OSError("synthetic disk failure")
            return write(path, data)
        def failed_sync(path):
            if failure == "fsync" and path.name == "attempt-0001": raise OSError("synthetic fsync failure")
            return sync(path)
        monkeypatch.setattr(pilot_capture, "_write_exclusive", failed_write)
        monkeypatch.setattr(pilot_capture, "_fsync_directory", failed_sync)
        return original([sys.executable, "-c", "import sys,time;sys.stdout.buffer.write(open(sys.argv[1],'rb').read());sys.stdout.flush();time.sleep(10)", str(body)], **kwargs)
    monkeypatch.setattr(capture.subprocess, "Popen", fixture)
    monkeypatch.setattr(capture.EvidenceReviewQwenTransport, "_transport_config",
                        lambda *_: {"timeout_s": .3, "max_output_bytes": 128000})
    result = review.execute(root, approval, approval["proposal_sha256"], identity_capture=observed)
    assert result["usage"]["output_tokens"] == 20
    assert "response_capture_failed" in result["failures"] and not result["review_received"]
    assert result["diagnostics"]["failure"] == "process_timeout"
