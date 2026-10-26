"""Fresh, consume-once authority for the experimental local streaming review.

Preparation performs no metadata or inference I/O. This trusted operator API
records explicit human approval; it does not authenticate the approving human.
There is no CLI, automatic approval, retry, or extension of a consumed attempt.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import hashlib
import os
from pathlib import Path
import stat
import time
from typing import Callable

from harness.verify import PARSER_VERSION
from scripts.pilot_capture import ResponseCaptureStore, _fsync_directory
from scripts.pilot_contract import PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_evidence_handoff import _encode, validate_review
from scripts.pilot_evidence_review import ENDPOINT, LIMITS, RUNWAY_S, TIMING_POLICY
from scripts.pilot_execution import implementation_hashes, require, timestamp, utc_now
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_preflight import local_qwen_identity
from scripts.pilot_prepare import _read
from scripts.pilot_qwen import _strict_json, _unknown_usage
from scripts.pilot_qwen_smoke import _save
from scripts.pilot_qwen_stream import POLICY, StreamingEvidenceReviewQwenTransport, inspect_stream, streaming_request

REQUEST_SHA256 = "86d9e69ec9d93568b389fdf0f10ab57ebb4f2efdfd06a2dee2bb09d53ce0425e"
REQUEST_BYTES = 212263
MODEL_DIGEST = "sha256:22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643"
ACTION = "execute_one_local_qwen_streaming_review"


def harness_identity() -> dict:
    return {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": ENDPOINT,
            "prompt_sha256": REQUEST_SHA256, "parser_version": PARSER_VERSION,
            "sampling": {"temperature": 0.0}}


def _request(raw: bytes) -> None:
    require(type(raw) is bytes and len(raw) == REQUEST_BYTES <= LIMITS.max_input_bytes
            and hashlib.sha256(raw).hexdigest() == REQUEST_SHA256, "request_drift")
    data = _strict_json(raw)
    require(type(data) is dict and data.get("stream") is True
            and data.get("stream_options") == {"include_usage": True}, "request_drift")
    original = dict(data)
    original["stream"] = False
    del original["stream_options"]
    require(streaming_request(_encode(original)) == raw, "request_drift")


def _identity(value: dict) -> None:
    assert_same_identity(value, value)
    require(value["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    require(value["model"]["digest"] == MODEL_DIGEST, "qwen_model_pin_drift")


def _reported_usage(receipts: list) -> list[dict]:
    """Keep distinct numeric receipts public; arbitrary provider text stays private."""
    fields = {"prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens", "reasoning_tokens",
              "audio_tokens", "accepted_prediction_tokens", "rejected_prediction_tokens"}
    details = {"prompt_tokens_details", "completion_tokens_details"}
    def counters(raw):
        if type(raw) is not dict:
            return {}
        result = {k: v for k, v in raw.items() if k in fields and type(v) is int and v >= 0}
        result.update({k: counters(v) for k, v in raw.items() if k in details and type(v) is dict})
        return result
    return [counters(receipt) for receipt in receipts]


def _fixed(root: Path) -> dict:
    return {"schema": "harnessie-streaming-review/1", "status": "proposal_not_authorization",
            "live_allowance": 0, "root": str(root), "endpoint": ENDPOINT, "model": QWEN_MODEL,
            "model_digest": MODEL_DIGEST, "limits": asdict(LIMITS), "request_sha256": REQUEST_SHA256,
            "request_bytes": REQUEST_BYTES, "execute_tools": False, "retries": 0,
            "approval_action": ACTION, "minimum_runway_s": RUNWAY_S,
            "timing_policy": deepcopy(TIMING_POLICY), "stream_policy": deepcopy(POLICY),
            "semantic_acceptance": False, "human_arbitrated": False,
            "declared_harness_identity": harness_identity(), "implementation_sha256": implementation_hashes()}


def prepare(root: Path, request: bytes, expected_identity: dict, identity_checked_at: str) -> dict:
    """Seal fresh request/identity/implementation bytes, without granting a call."""
    root = root.absolute()
    _request(request)
    _identity(expected_identity)
    now = utc_now()
    require(timedelta(0) <= now - timestamp(identity_checked_at)
            <= timedelta(seconds=TIMING_POLICY["identity_max_age_s_at_start"]), "qwen_identity_stale")
    proposal = _fixed(root) | {"created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "expected_identity": deepcopy(expected_identity), "identity_checked_at": identity_checked_at}
    ResponseCaptureStore(root, LIMITS.max_output_bytes)
    _save(root, "request.json", request)
    _save(root, "proposal.json", proposal)
    return proposal


def _authority(root: Path, approval: dict | None, confirmation: str | None, *, before_dispatch=True) -> dict:
    require(type(approval) is dict and type(confirmation) is str, "live_authority_required")
    require(not root.is_symlink() and all(not p.is_symlink() for p in root.parents)
            and stat.S_ISDIR(root.stat().st_mode) and root.stat().st_mode & 0o077 == 0,
            "unsafe_evidence_directory")
    for name in ("proposal.json", "request.json"):
        info = (root / name).lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_mode & 0o077 == 0, "unsafe_evidence_file")
    proposal = _strict_json(_read(root, "proposal.json", 1_500_000))
    require(type(proposal) is dict and digest_json(proposal) == confirmation, "proposal_drift")
    fixed = _fixed(root)
    require(set(proposal) == set(fixed) | {"created_at", "expires_at", "expected_identity", "identity_checked_at"},
            "invalid_proposal")
    require(proposal["implementation_sha256"] == fixed["implementation_sha256"], "implementation_drift")
    require(digest_json({k: proposal[k] for k in fixed}) == digest_json(fixed), "invalid_proposal")
    _request(_read(root, "request.json", LIMITS.max_input_bytes))
    _identity(proposal["expected_identity"])
    require(set(approval) == {"proposal_sha256", "approved_by", "action", "approved_at", "expires_at"}
            and approval["proposal_sha256"] == confirmation and approval["approved_by"] == "Sam Rogers"
            and approval["action"] == ACTION, "invalid_live_authority")
    now = utc_now()
    created, expires = timestamp(proposal["created_at"]), timestamp(proposal["expires_at"])
    require(created <= timestamp(approval["approved_at"]) <= now
            < timestamp(approval["expires_at"]) <= expires
            and expires == created + timedelta(hours=24), "live_authority_expired")
    if before_dispatch:
        require(timedelta(0) <= now - timestamp(proposal["identity_checked_at"])
                <= timedelta(seconds=TIMING_POLICY["identity_max_age_s_at_start"]), "qwen_identity_stale")
        require(timestamp(approval["expires_at"]) - now >= timedelta(seconds=RUNWAY_S), "insufficient_runway")
    return proposal


def execute(root: Path, approval: dict | None = None, confirmation: str | None = None, *,
            identity_capture: Callable[[], dict] | None = None,
            transport_factory: Callable | None = None) -> dict:
    """Dispatch at most once, capture before parsing, then assess independent gates.

    Injectable identity/transport seams are trusted test/operator code. They do
    not bypass authority, the exclusive attempt guard, request or postflight gates.
    """
    root = root.absolute()
    try:
        proposal = _authority(root, approval, confirmation)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, PilotRefusal):
            raise
        raise PilotRefusal("invalid_proposal") from None
    attempt = root / "attempt"
    try:
        os.mkdir(attempt, 0o700)
    except OSError:
        raise PilotRefusal("attempt_consumed") from None
    try:
        _fsync_directory(root)
        _save(attempt, "guard.json", {"status": "consumed", "proposal_sha256": confirmation,
             "request_sha256": REQUEST_SHA256, "reserved_at": utc_now().isoformat(), "approval": approval})
        reservation = ResponseCaptureStore(attempt / "responses", LIMITS.max_output_bytes).reserve(1)
    except (OSError, PilotRefusal):
        raise PilotRefusal("evidence_persistence_failed") from None

    started = time.monotonic()
    expected = proposal["expected_identity"]
    capture = identity_capture or (lambda: local_qwen_identity(harness_identity(), expected["client_version"]))
    failures = []
    wire = None
    raw = None
    dispatched = False
    inspection = {"usage": _unknown_usage(), "raw_provider_usage": [], "response_shape": None,
                  "review": None, "failures": [], "review_received": False}

    def fail(code):
        if code not in failures:
            failures.append(code)

    def observe(name, code):
        try:
            observed = capture()
            _save(attempt, name, observed)
            _identity(observed)
            assert_same_identity(expected, observed)
        except OSError:
            raise PilotRefusal("evidence_persistence_failed") from None
        except Exception:
            raise PilotRefusal(code) from None

    try:
        observe("identity-before.json", "identity_before_invalid")
        _authority(root, approval, confirmation)
        request = _read(root, "request.json", LIMITS.max_input_bytes)
        _request(request)
        wire = (transport_factory or StreamingEvidenceReviewQwenTransport)(reservation)
        # Construction is still before dispatch; recheck authority and bytes
        # after this trusted extension point as well as after identity I/O.
        _authority(root, approval, confirmation)
        require(_read(root, "request.json", LIMITS.max_input_bytes) == request, "request_drift")
        dispatched = True
        try:
            raw = wire(request, LIMITS)
        except Exception as exc:
            fail(exc.code if isinstance(exc, PilotRefusal) else "transport_failed")
        receipt = wire.response_capture
        if wire.capture_failure:
            fail("response_capture_failed")
        if raw is None:
            raw = getattr(wire, "captured_stdout", None)
        if receipt and receipt.get("status") == "retained":
            try:
                stored = _read(reservation.directory, "stdout.bin", LIMITS.max_output_bytes + 1)
                if raw is None:
                    raw = stored
                require(raw == stored and type(receipt.get("bytes")) is int
                        and receipt["bytes"] == len(stored)
                        and receipt.get("sha256") == hashlib.sha256(stored).hexdigest(),
                        "response_capture_mismatch")
            except PilotRefusal as exc:
                fail(exc.code)
            except (OSError, ValueError):
                fail("response_capture_failed")
        complete = (not failures and receipt is not None and receipt.get("status") == "retained"
                    and receipt.get("capture_complete") is True)
        if raw is not None:
            require(type(raw) is bytes, "malformed_response")
            if len(raw) > LIMITS.max_output_bytes:
                fail("output_limit_exceeded")
                complete = False
            inspection = inspect_stream(raw[:LIMITS.max_output_bytes], capture_complete=complete)
            for code in inspection["failures"]:
                fail(code)
            try:
                _save(attempt, "accounting.json", {"usage": inspection["usage"],
                      "raw_provider_usage": inspection["raw_provider_usage"]})
            except (OSError, PilotRefusal):
                fail("evidence_persistence_failed")
        else:
            fail("response_capture_incomplete")
    except Exception as exc:
        fail(exc.code if isinstance(exc, PilotRefusal) else "review_failed")
    finally:
        if dispatched:
            for check in (lambda: observe("identity-after.json", "identity_drift"),
                          lambda: _authority(root, approval, confirmation, before_dispatch=False)):
                try:
                    check()
                except Exception as exc:
                    fail(exc.code if isinstance(exc, PilotRefusal) else "invalid_proposal")
    candidate = inspection["review"]
    validation = validate_review(candidate) if candidate is not None else None
    if not failures and candidate is not None:
        try:
            _save(attempt, "parsed-review.json", candidate)
        except (OSError, PilotRefusal):
            fail("evidence_persistence_failed")
    received = not failures and candidate is not None
    result = {"schema": "harnessie-streaming-review-result/1", "outcome": failures[0] if failures else "review_received",
              "failures": failures, "proposal_sha256": confirmation, "request_sha256": REQUEST_SHA256,
              "elapsed_s": time.monotonic() - started, "transport_dispatched": dispatched,
              "usage": inspection["usage"], "reported_usage_count": len(inspection["raw_provider_usage"]),
              "reported_usage": _reported_usage(inspection["raw_provider_usage"]),
              "response_shape": inspection["response_shape"], "evidence_ingestion": "unknown",
              "actual_dollar_cost": None, "response_capture": wire.response_capture if wire else None,
              "diagnostics": wire.diagnostics if wire else {}, "review_received": received,
              "structural_validation": validation, "stance": candidate["stance"] if received else None,
              "semantic_acceptance": False, "human_arbitrated": False, "executed_tools": 0, "retries": 0,
              "outcome_persisted": True}
    try:
        _save(attempt, "outcome.json", result)
    except (OSError, PilotRefusal):
        fail("evidence_persistence_failed")
        result.update(outcome=failures[0], review_received=False, stance=None, outcome_persisted=False)
    return result
