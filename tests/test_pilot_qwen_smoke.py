"""Offline tests only: synthetic identity and injected transport."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_contract import CallAllowance, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_qwen import QwenPilot
from scripts import pilot_qwen_smoke as smoke
from tests.test_pilot_qwen import identity, response


def sealed_identity():
    value = identity()
    value["harness_identity"] = smoke.harness_identity()
    value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
    return value


def approved(tmp_path, monkeypatch):
    root = tmp_path / "candidate"
    now = datetime.now(timezone.utc)
    proposal = smoke.prepare(root, expected_identity=sealed_identity(), identity_checked_at=now.isoformat())
    seal = digest_json(proposal)
    approval = {"proposal_sha256": seal, "approved_by": "Sam Rogers",
                "action": "execute_one_local_qwen_smoke",
                "approved_at": (now - timedelta(seconds=1)).isoformat(),
                "expires_at": (now + timedelta(minutes=5)).isoformat()}
    return root, approval


def execute(root, approval, **kwargs):
    return smoke.execute(root, approval, approval.get("proposal_sha256"), **kwargs)


def ok_response(tokens=3, content="PILOT_SMOKE_OK"):
    return response(usage={"prompt_tokens": 2, "completion_tokens": tokens, "total_tokens": 2 + tokens},
                    envelope={"content": content, "tool_calls": [], "stop_reason": "end_turn"})


def test_preparation_has_zero_authority_and_no_identity_access(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke, "local_qwen_identity", lambda *_: pytest.fail("metadata accessed"))
    proposal = smoke.prepare(tmp_path / "candidate")
    assert proposal["live_allowance"] == 0
    assert proposal["expected_identity"] is None
    assert proposal["limits"]["max_calls"] == 1
    assert (tmp_path / "candidate" / "request.json").read_bytes() == smoke.request_bytes()
    with pytest.raises(PilotRefusal, match="live_authority_required"):
        smoke.execute(tmp_path / "candidate", {})


def test_wire_request_matches_existing_adapter():
    adapter = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, smoke.ENDPOINT),
                        sealed_identity(), sealed_identity, CallAllowance(smoke.LIMITS))
    assert smoke.request_bytes() == adapter.prepare_request([Message("user", smoke.PROMPT)], []).request


@pytest.mark.parametrize("tokens,expected", [(1024, "completed"), (1025, "output_tokens_exceeded")])
def test_one_call_durable_guard_usage_boundaries_and_no_reuse(tmp_path, monkeypatch, tokens, expected):
    root, approval = approved(tmp_path, monkeypatch)
    calls = []
    def transport(request, limits):
        assert (root / "attempt" / "guard.json").is_file()
        assert (root / "attempt" / "identity-before.json").is_file()
        assert request == (root / "request.json").read_bytes()
        assert limits == smoke.LIMITS
        calls.append("transport")
        return ok_response(tokens)
    result = execute(root, approval, identity_capture=sealed_identity, transport=transport)
    assert result["outcome"] == expected
    assert result["receipt"]["raw_provider_usage"]["completion_tokens"] == tokens
    assert result["receipt"]["usage"]["output_tokens"] == tokens
    assert result["elapsed_s"] >= 0
    assert len(calls) == 1
    assert json.loads((root / "attempt" / "outcome.json").read_text()) == result
    assert (root.stat().st_mode & 0o777) == 0o700
    for path in (root / "attempt").iterdir():
        assert (path.stat().st_mode & 0o777) == 0o600
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, identity_capture=sealed_identity, transport=transport)
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["wrong_sentinel", "malformed", "timeout", "missing_usage", "drift"])
def test_response_refusals_preserve_attempt(tmp_path, monkeypatch, kind):
    root, approval = approved(tmp_path, monkeypatch)
    captures = 0
    def capture():
        nonlocal captures
        captures += 1
        value = sealed_identity()
        if kind == "drift" and captures == 2:
            value["server_version"] = "changed"
            value["fingerprint"] = digest_json({k: v for k, v in value.items() if k != "fingerprint"})
        return value
    def transport(*_):
        if kind == "timeout":
            raise PilotRefusal("process_timeout")
        if kind == "malformed":
            return b"bad json"
        if kind == "missing_usage":
            return response(usage={})
        return ok_response(content="wrong" if kind == "wrong_sentinel" else "PILOT_SMOKE_OK")
    result = execute(root, approval, identity_capture=capture, transport=transport)
    assert result["outcome"] != "completed"
    assert captures == 2
    assert (root / "attempt" / "guard.json").is_file()


def test_approval_without_external_confirmation_cannot_grant_authority(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    with pytest.raises(PilotRefusal, match="live_authority_required"):
        smoke.execute(root, approval, identity_capture=lambda: pytest.fail("metadata accessed"))
    assert not (root / "attempt").exists()


@pytest.mark.parametrize("change", ["request", "proposal", "expiry", "identity", "symlink"])
def test_pre_dispatch_drift_or_invalid_authority_refuses(tmp_path, monkeypatch, change):
    root, approval = approved(tmp_path, monkeypatch)
    if change == "request":
        (root / "request.json").write_bytes(b"{}")
    elif change == "proposal":
        value = json.loads((root / "proposal.json").read_text())
        value["live_allowance"] = 1
        (root / "proposal.json").write_text(json.dumps(value))
    elif change == "expiry":
        approval["expires_at"] = approval["approved_at"]
    elif change == "identity":
        value = json.loads((root / "proposal.json").read_text())
        value["expected_identity"] = None
        (root / "proposal.json").write_text(json.dumps(value))
    else:
        (root / "request.json").unlink()
        (root / "request.json").symlink_to(root / "proposal.json")
    with pytest.raises(PilotRefusal):
        execute(root, approval, identity_capture=lambda: pytest.fail("metadata accessed"))


def test_final_persistence_failure_consumes_attempt(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    original = smoke._save
    def fail_outcome(directory, name, data):
        if name == "outcome.json":
            raise OSError("disk full")
        original(directory, name, data)
    monkeypatch.setattr(smoke, "_save", fail_outcome)
    with pytest.raises(PilotRefusal, match="evidence_persistence_failed"):
        execute(root, approval, identity_capture=sealed_identity, transport=lambda *_: ok_response())
    assert (root / "attempt" / "response.bin").is_file()
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, identity_capture=lambda: pytest.fail("metadata accessed"))


def test_preparation_refuses_existing_or_symlink_root(tmp_path):
    root = tmp_path / "candidate"
    smoke.prepare(root)
    with pytest.raises(PilotRefusal):
        smoke.prepare(root)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(PilotRefusal):
        smoke.prepare(alias / "new")


def test_stale_identity_is_refused_before_attempt(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    proposal = json.loads((root / "proposal.json").read_text())
    proposal["identity_checked_at"] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
    (root / "proposal.json").write_text(json.dumps(proposal))
    approval["proposal_sha256"] = digest_json(proposal)
    with pytest.raises(PilotRefusal, match="qwen_identity_stale"):
        execute(root, approval, identity_capture=lambda: pytest.fail("metadata accessed"))
    assert not (root / "attempt").exists()


def test_implementation_drift_is_refused_before_attempt(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    monkeypatch.setattr(smoke, "implementation_hashes", lambda: {})
    with pytest.raises(PilotRefusal, match="implementation_drift"):
        execute(root, approval, identity_capture=lambda: pytest.fail("metadata accessed"))


@pytest.mark.parametrize("name", ["guard.json", "identity-before.json", "response.bin"])
def test_persistence_errors_never_release_attempt(tmp_path, monkeypatch, name):
    root, approval = approved(tmp_path, monkeypatch)
    original = smoke._save
    calls = []
    def fail_selected(directory, filename, data):
        if filename == name:
            raise OSError("disk full")
        original(directory, filename, data)
    monkeypatch.setattr(smoke, "_save", fail_selected)
    kwargs = {"identity_capture": sealed_identity,
              "transport": lambda *_: calls.append("transport") or ok_response()}
    if name == "guard.json":
        with pytest.raises(PilotRefusal, match="evidence_persistence_failed"):
            execute(root, approval, **kwargs)
    else:
        result = execute(root, approval, **kwargs)
        assert result["outcome"] == "evidence_persistence_failed"
        if name == "response.bin":
            assert result["receipt"]["usage"]["output_tokens"] == 3
    assert len(calls) == (1 if name == "response.bin" else 0)
    with pytest.raises(PilotRefusal, match="attempt_consumed"):
        execute(root, approval, **kwargs)


def test_oversized_response_refuses_and_retains_bounded_capture(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    result = execute(root, approval, identity_capture=sealed_identity,
                     transport=lambda *_: b"x" * (smoke.LIMITS.max_output_bytes + 20))
    assert result["outcome"] == "output_limit_exceeded"
    assert (root / "attempt" / "response.bin").stat().st_size == smoke.LIMITS.max_output_bytes + 1


def test_default_identity_uses_strict_local_residency_checker(tmp_path, monkeypatch):
    root, approval = approved(tmp_path, monkeypatch)
    calls = []
    def strict_local(configuration, client_version):
        assert configuration == smoke.harness_identity()
        assert client_version == sealed_identity()["client_version"]
        calls.append("strict_local")
        return sealed_identity()
    monkeypatch.setattr(smoke, "local_qwen_identity", strict_local)
    result = execute(root, approval, transport=lambda *_: calls.append("transport") or ok_response())
    assert result["outcome"] == "completed"
    assert calls == ["strict_local", "transport", "strict_local"]


@pytest.mark.parametrize("failure", ["qwen_remote_model", "qwen_local_blobs_unavailable"])
def test_default_identity_residency_refusal_prevents_dispatch(tmp_path, monkeypatch, failure):
    root, approval = approved(tmp_path, monkeypatch)
    def unsafe_identity(*_):
        raise PilotRefusal(failure)
    monkeypatch.setattr(smoke, "local_qwen_identity", unsafe_identity)
    result = execute(root, approval, transport=lambda *_: pytest.fail("inference attempted"))
    assert result["outcome"] == "identity_before_invalid"
    assert result["receipt"]["inference_started"] is False
    assert (root / "attempt" / "guard.json").is_file()
