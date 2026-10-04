"""Probe authority, persistence and exact-wire tests. No live services."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from harness.models.base import Message, ModelSpec
from scripts import pilot_qwen_probe as probe
from scripts.pilot_contract import CallAllowance, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_qwen import QwenPilot
from tests.test_pilot_qwen import identity, response


@pytest.fixture
def wire(monkeypatch):
    tools = [{"name": name, "parameters": {"type": "object"}} for name in sorted(probe.TOOL_NAMES)]
    adapter = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, probe.ENDPOINT),
                        identity(), identity, CallAllowance(probe.LIMITS))
    raw = adapter.prepare_request([Message("user", "synthetic diagnostic")], tools).request
    monkeypatch.setattr(probe, "REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(probe, "REQUEST_BYTES", len(raw))
    monkeypatch.setattr(probe, "local_qwen_identity", lambda *_: pytest.fail("live metadata"))
    return raw


def sealed_identity():
    value = identity()
    value["harness_identity"] = probe.harness_identity()
    value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
    return value


def approved(tmp_path, wire):
    root = tmp_path / "candidate"
    now = datetime.now(timezone.utc)
    proposal = probe.prepare(root, wire, sealed_identity(), now.isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers",
                "action": "execute_one_local_qwen_probe", "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat()}
    return root, approval


def execute(root, approval, **kwargs):
    return probe.execute(root, approval, approval["proposal_sha256"],
                         identity_capture=kwargs.pop("identity_capture", sealed_identity), **kwargs)


def test_prepare_private_zero_authority_no_metadata(tmp_path, wire):
    root, approval = approved(tmp_path, wire)
    proposal = json.loads((root / "proposal.json").read_text())
    assert proposal["live_allowance"] == 0
    assert proposal["limits"] == {"max_calls": 1, "timeout_s": 300, "max_input_bytes": 256000,
                                   "max_evidence_bytes": 256000, "max_output_bytes": 128000,
                                   "max_output_tokens": 4096}
    assert (root / "request.json").read_bytes() == wire
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
    for args in [(None, None), (approval, None), (None, approval["proposal_sha256"])]:
        with pytest.raises(PilotRefusal, match="live_authority_required"):
            probe.execute(root, *args)
    assert not (root / "attempt").exists()


def test_wrong_or_one_byte_changed_request_refused(tmp_path, wire):
    for raw in [b"{}", wire[:-1] + b" "]:
        with pytest.raises(PilotRefusal, match="request_drift"):
            probe.prepare(tmp_path / "candidate", raw, sealed_identity(), datetime.now(timezone.utc).isoformat())
    assert not (tmp_path / "candidate").exists()


def test_exact_once_no_reencoding_no_tool_execution_private_content(tmp_path, wire, monkeypatch, capsys):
    root, approval = approved(tmp_path, wire)
    monkeypatch.setattr(QwenPilot, "complete", lambda *_: pytest.fail("reencoded"))
    calls = []
    def transport(request, limits):
        assert request == wire
        assert limits == probe.LIMITS
        assert (root / "attempt" / "guard.json").is_file()
        assert (root / "attempt" / "identity-before.json").is_file()
        calls.append(request)
        return response(envelope={"content": "PRIVATE CONTENT", "tool_calls": [
            {"id": "one", "name": "read_file", "arguments": {"path": "PRIVATE PATH"}}],
            "stop_reason": "tool_use"})
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == "completed"
    assert result["turn_shape"] == {"content_bytes": 15, "tool_names": ["read_file"], "stop_reason": "tool_use"}
    assert result["executed_tools"] == result["retries"] == 0
    assert "PRIVATE" not in json.dumps(result)
    assert "PRIVATE CONTENT" in (root / "attempt" / "parsed-turn.json").read_text()
    assert "PRIVATE CONTENT" in (root / "attempt" / "responses" / "attempt-0001" / "stdout.bin").read_text()
    assert capsys.readouterr().out == ""
    assert result["receipt"]["usage"]["output_tokens"] == 3
    assert result["response_capture"]["capture_complete"] is True
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize("change,reason", [
    ("extra", "invalid_proposal"), ("limits", "invalid_proposal"),
    ("request", "request_drift"), ("implementation", "implementation_drift"),
    ("identity", "qwen_identity_stale"), ("runway", "insufficient_runway"),
    ("action", "invalid_live_authority"), ("extra_approval", "invalid_live_authority"),
    ("symlink", "unsafe_evidence_file"), ("mode", "unsafe_evidence_file"),
])
def test_authority_refusals_before_attempt(tmp_path, wire, change, reason):
    root, approval = approved(tmp_path, wire)
    path = root / "proposal.json"
    value = json.loads(path.read_text())
    if change == "extra":
        value["arbitrary"] = True
    elif change == "limits":
        value["limits"]["max_calls"] = 2
    elif change == "implementation":
        value["implementation_sha256"] = {}
    elif change == "identity":
        value["identity_checked_at"] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
    elif change == "runway":
        approval["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=329)).isoformat()
    elif change == "action":
        approval["action"] = "execute_one_local_qwen_smoke"
    elif change == "extra_approval":
        approval["retry"] = True
    elif change == "request":
        (root / "request.json").write_bytes(b"{}")
    elif change == "symlink":
        (root / "request.json").unlink()
        (root / "request.json").symlink_to(path)
    elif change == "mode":
        (root / "request.json").chmod(0o644)
    path.write_text(json.dumps(value))
    approval["proposal_sha256"] = digest_json(value)
    with pytest.raises(PilotRefusal, match=reason):
        execute(root, approval, identity_capture=lambda: pytest.fail("identity accessed"),
                transport=lambda *_: pytest.fail("transport accessed"))
    assert not (root / "attempt").exists()


def test_recheck_after_identity_and_before_transport(tmp_path, wire):
    root, approval = approved(tmp_path, wire)
    def capture():
        (root / "request.json").write_bytes(b"{}")
        return sealed_identity()
    result = execute(root, approval, identity_capture=capture,
                     transport=lambda *_: pytest.fail("transport accessed"))
    assert result["outcome"] == "request_drift"
    assert (root / "attempt" / "guard.json").exists()


@pytest.mark.parametrize("case,expected", [("timeout", "process_timeout"), ("drift", "identity_drift"),
                                         ("malformed", "malformed_response"), ("cap", "output_tokens_exceeded")])
def test_failed_response_retained_no_retry_unknown_is_not_zero(tmp_path, wire, case, expected):
    root, approval = approved(tmp_path, wire)
    captures = []
    def capture():
        value = sealed_identity()
        if captures and case == "drift":
            value["server_version"] = "changed"
            value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
        captures.append(value)
        return value
    def transport(*_):
        if case == "timeout":
            raise PilotRefusal("process_timeout")
        if case == "malformed":
            return b"bad json"
        return response(usage={"prompt_tokens": 2, "completion_tokens": 4097, "total_tokens": 4099}) if case == "cap" else response()
    result = execute(root, approval, identity_capture=capture, transport=transport)
    assert result["outcome"] == expected
    assert len(captures) == 2
    assert result["receipt"]["usage"]["output_tokens"] == (None if case in {"timeout", "malformed"} else 4097 if case == "cap" else 3)
    assert (root / "attempt" / "outcome.json").is_file()
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=transport)


def test_capture_failure_preserves_known_usage(tmp_path, wire, monkeypatch):
    from scripts.pilot_capture import ResponseCaptureReservation
    root, approval = approved(tmp_path, wire)
    monkeypatch.setattr(ResponseCaptureReservation, "save", lambda *_a, **_k: (_ for _ in ()).throw(PilotRefusal("response_capture_failed")))
    result = execute(root, approval, transport=lambda *_: response())
    assert result["outcome"] == "response_capture_failed"
    assert result["receipt"]["usage"]["output_tokens"] == 3


@pytest.mark.parametrize("name", ["guard.json", "parsed-turn.json", "outcome.json"])
def test_persistence_failure_consumes_attempt(tmp_path, wire, monkeypatch, name):
    root, approval = approved(tmp_path, wire)
    original = probe._save
    def save(directory, filename, data):
        if filename == name:
            raise OSError("disk full")
        original(directory, filename, data)
    monkeypatch.setattr(probe, "_save", save)
    calls = []
    if name == "parsed-turn.json":
        result = execute(root, approval, transport=lambda *_: calls.append(1) or response())
        assert result["outcome"] == "evidence_persistence_failed"
        assert result["receipt"]["usage"]["output_tokens"] == 3
    else:
        with pytest.raises(PilotRefusal, match="evidence_persistence_failed"):
            execute(root, approval, transport=lambda *_: calls.append(1) or response())
    assert len(calls) == (0 if name == "guard.json" else 1)
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, transport=lambda *_: pytest.fail("retry"))


def test_exclusive_preparation(tmp_path, wire):
    root, _ = approved(tmp_path, wire)
    with pytest.raises(PilotRefusal):
        probe.prepare(root, wire, sealed_identity(), datetime.now(timezone.utc).isoformat())


@pytest.mark.parametrize("field,value", [("live_allowance", False), ("retries", False),
                                        ("execute_tools", 0), ("minimum_runway_s", 330.0),
                                        ("max_calls", True), ("timeout_s", 300.0)])
def test_proposal_strict_scalar_types(tmp_path, wire, field, value):
    root, approval = approved(tmp_path, wire)
    path = root / "proposal.json"
    proposal = json.loads(path.read_text())
    target = proposal["limits"] if field in {"max_calls", "timeout_s"} else proposal
    target[field] = value
    path.write_text(json.dumps(proposal))
    approval["proposal_sha256"] = digest_json(proposal)
    with pytest.raises(PilotRefusal, match="invalid_proposal"):
        execute(root, approval, transport=lambda *_: pytest.fail("transport"))


def test_metadata_consumes_runway_before_dispatch(tmp_path, wire, monkeypatch):
    root, approval = approved(tmp_path, wire)
    before = probe.utc_now()
    def capture():
        monkeypatch.setattr(probe, "utc_now", lambda: before + timedelta(minutes=5))
        return sealed_identity()
    result = execute(root, approval, identity_capture=capture,
                     transport=lambda *_: pytest.fail("transport"))
    assert result["outcome"] == "insufficient_runway"
    assert result["transport_dispatched"] is False
    assert result["receipt"]["usage"]["output_tokens"] is None


@pytest.mark.parametrize("elapsed,expected", [(300, "completed"), (601, "live_authority_expired")])
def test_postreturn_authority_preserves_usage_without_new_runway(tmp_path, wire, monkeypatch, elapsed, expected):
    root, approval = approved(tmp_path, wire)
    before = probe.utc_now()
    def transport(*_):
        monkeypatch.setattr(probe, "utc_now", lambda: before + timedelta(seconds=elapsed))
        return response()
    result = execute(root, approval, transport=transport)
    assert result["outcome"] == expected
    assert result["transport_dispatched"] is True
    assert result["receipt"]["usage"]["output_tokens"] == 3


@pytest.mark.parametrize("age,accepted", [(570, True), (571, False)])
def test_identity_runway_exact_boundary(tmp_path, wire, monkeypatch, age, accepted):
    now = datetime(2026, 10, 4, 4, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(probe, "utc_now", lambda: now)
    root = tmp_path / "candidate"
    proposal = probe.prepare(root, wire, sealed_identity(), (now - timedelta(seconds=age)).isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers",
                "action": "execute_one_local_qwen_probe", "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat()}
    if accepted:
        result = execute(root, approval, transport=lambda *_: response())
        assert result["outcome"] == "completed"
        assert result["transport_dispatched"] is True
    else:
        with pytest.raises(PilotRefusal, match="insufficient_runway"):
            execute(root, approval, transport=lambda *_: pytest.fail("transport"))
        assert not (root / "attempt").exists()


def test_identity_runway_expires_during_metadata_no_dispatch(tmp_path, wire, monkeypatch):
    now = datetime(2026, 10, 4, 4, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(probe, "utc_now", lambda: now)
    root = tmp_path / "candidate"
    proposal = probe.prepare(root, wire, sealed_identity(), (now - timedelta(seconds=570)).isoformat())
    approval = {"proposal_sha256": digest_json(proposal), "approved_by": "Sam Rogers",
                "action": "execute_one_local_qwen_probe", "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat()}
    def capture():
        monkeypatch.setattr(probe, "utc_now", lambda: now + timedelta(seconds=1))
        return sealed_identity()
    result = execute(root, approval, identity_capture=capture,
                     transport=lambda *_: pytest.fail("transport"))
    assert result["outcome"] == "insufficient_runway"
    assert result["transport_dispatched"] is False
    assert result["receipt"]["usage"]["output_tokens"] is None
