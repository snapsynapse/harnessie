"""One consume-once local timing measurement, never an accepted review.

Only the approved full-evidence request with its output cap reduced to 256 is
eligible. This operator API records authority; it does not authenticate a human.
"""
from __future__ import annotations

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
from scripts.pilot_contract import PilotLimits, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_execution import implementation_hashes, require, timestamp, utc_now
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_preflight import local_qwen_identity
from scripts.pilot_prepare import _read
from scripts.pilot_qwen import _strict_json, _unknown_usage, _usage
from scripts.pilot_qwen_capture import CapturedQwenTransport
from scripts.pilot_qwen_smoke import _save

ENDPOINT = "http://127.0.0.1:11434/v1"
ORIGINAL_REQUEST_SHA256 = "a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c"
REQUEST_SHA256 = "1da982f1c89ded4c983680f7a114dd453208baef31b5a4ce01a9ceaf06ea86fe"
REQUEST_BYTES = 212223
LIMITS = PilotLimits(max_calls=1, timeout_s=300, max_input_bytes=256000,
                     max_evidence_bytes=256000, max_output_bytes=128000, max_output_tokens=256)
RUNWAY_S = 330
ACTION = "execute_one_local_qwen_evidence_timing_probe"


def harness_identity() -> dict:
    return {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": ENDPOINT,
            "prompt_sha256": REQUEST_SHA256, "parser_version": PARSER_VERSION,
            "sampling": {"temperature": 0.0}}


def _request(raw: bytes) -> None:
    require(type(raw) is bytes and len(raw) == REQUEST_BYTES <= LIMITS.max_input_bytes
            and hashlib.sha256(raw).hexdigest() == REQUEST_SHA256, "request_drift")
    # The pinned original hash binds all 17 source bodies, system and schema.
    # The derived pinned hash permits exactly one changed scalar, not omission.


def _fixed(root: Path) -> dict:
    return {"schema": "harnessie-evidence-timing-probe/1", "status": "proposal_not_authorization",
            "live_allowance": 0, "root": str(root), "endpoint": ENDPOINT, "model": QWEN_MODEL,
            "limits": asdict(LIMITS), "original_request_sha256": ORIGINAL_REQUEST_SHA256,
            "request_sha256": REQUEST_SHA256, "request_bytes": REQUEST_BYTES,
            "execute_tools": False, "retries": 0, "minimum_runway_s": RUNWAY_S,
            "review_accepted": False, "purpose": "local_timing_feasibility_only",
            "declared_harness_identity": harness_identity(), "implementation_sha256": implementation_hashes()}


def prepare(root: Path, original_request: bytes, expected_identity: dict,
            identity_checked_at: str) -> dict:
    """Prepare without metadata I/O, inference or inferred authorization."""
    root = root.absolute()
    require(type(original_request) is bytes
            and hashlib.sha256(original_request).hexdigest() == ORIGINAL_REQUEST_SHA256, "request_drift")
    request = original_request.replace(b'"max_tokens":4096,', b'"max_tokens":256,', 1)
    _request(request)
    assert_same_identity(expected_identity, expected_identity)
    require(expected_identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    timestamp(identity_checked_at)
    now = utc_now()
    proposal = _fixed(root) | {"created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "expected_identity": expected_identity, "identity_checked_at": identity_checked_at}
    ResponseCaptureStore(root, LIMITS.max_output_bytes)
    _save(root, "request.json", request)
    _save(root, "proposal.json", proposal)
    return proposal


def _authority(root: Path, approval: dict | None, confirmation: str | None, *, runway: bool = True) -> dict:
    require(type(approval) is dict and isinstance(confirmation, str), "live_authority_required")
    require(not root.is_symlink() and all(not p.is_symlink() for p in root.parents)
            and stat.S_ISDIR(root.stat().st_mode) and root.stat().st_mode & 0o077 == 0,
            "unsafe_evidence_directory")
    for name in ("proposal.json", "request.json"):
        info = (root / name).lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_mode & 0o077 == 0, "unsafe_evidence_file")
    proposal = _strict_json(_read(root, "proposal.json", 1_500_000))
    require(type(proposal) is dict and digest_json(proposal) == confirmation, "proposal_drift")
    require(set(approval) == {"proposal_sha256", "approved_by", "action", "approved_at", "expires_at"}
            and approval["proposal_sha256"] == confirmation and approval["approved_by"] == "Sam Rogers"
            and approval["action"] == ACTION, "invalid_live_authority")
    now = utc_now()
    require(timestamp(approval["approved_at"]) <= now < timestamp(approval["expires_at"])
            <= timestamp(proposal["expires_at"]), "live_authority_expired")
    _request(_read(root, "request.json", LIMITS.max_input_bytes))
    fixed = _fixed(root)
    require(set(proposal) == set(fixed) | {"created_at", "expires_at", "expected_identity", "identity_checked_at"},
            "invalid_proposal")
    require(proposal["implementation_sha256"] == fixed["implementation_sha256"], "implementation_drift")
    require(digest_json({k: proposal[k] for k in fixed}) == digest_json(fixed), "invalid_proposal")
    require(timestamp(proposal["created_at"]) <= now, "invalid_proposal")
    identity = proposal["expected_identity"]
    assert_same_identity(identity, identity)
    require(identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    require(timedelta(0) <= now - timestamp(proposal["identity_checked_at"]) <= timedelta(minutes=15),
            "qwen_identity_stale")
    if runway:
        deadline = min(timestamp(approval["expires_at"]), timestamp(proposal["expires_at"]),
                       timestamp(proposal["identity_checked_at"]) + timedelta(minutes=15))
        require(deadline - now >= timedelta(seconds=RUNWAY_S), "insufficient_runway")
    return proposal


def execute(root: Path, approval: dict | None = None, confirmation: str | None = None, *,
            identity_capture: Callable[[], dict] | None = None,
            transport: Callable[[bytes, PilotLimits], bytes] | None = None) -> dict:
    """Measure one exact native request, capture first, retain usage independently.

    A length-limited or non-JSON assistant answer is useful timing evidence.
    It cannot become an accepted review. Provider usage is parsed before answer
    checks and retained even if later identity, authority or capture checks fail.
    """
    root = root.absolute()
    try:
        proposal = _authority(root, approval, confirmation)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, PilotRefusal):
            raise
        raise PilotRefusal("invalid_proposal") from exc
    attempt = root / "attempt"
    try:
        os.mkdir(attempt, 0o700)
    except OSError as exc:
        raise PilotRefusal("attempt_consumed") from exc
    started = time.monotonic()
    try:
        _fsync_directory(root)
        _save(attempt, "guard.json", {"status": "consumed", "proposal_sha256": confirmation,
             "request_sha256": REQUEST_SHA256, "reserved_at": utc_now().isoformat(), "approval": approval})
        reservation = ResponseCaptureStore(attempt / "responses", LIMITS.max_output_bytes).reserve(1)
    except (OSError, PilotRefusal) as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc

    expected = proposal["expected_identity"]
    capture = identity_capture or (lambda: local_qwen_identity(harness_identity(), expected["client_version"]))
    wire = CapturedQwenTransport(reservation, timeout_ceiling_s=300)
    failures: list[str] = []
    dispatched = False
    delivered = False
    raw = None
    response_capture = None
    usage = _unknown_usage()
    raw_usage = None
    shape = {"finish_reason": None, "content_bytes": None, "reasoning_bytes": None}

    def observe(name: str, failure: str) -> None:
        try:
            observed = capture()
            _save(attempt, name, observed)
            assert_same_identity(expected, observed)
        except OSError:
            raise PilotRefusal("evidence_persistence_failed") from None
        except Exception:
            raise PilotRefusal(failure) from None

    try:
        observe("identity-before.json", "identity_before_invalid")
        _authority(root, approval, confirmation)  # Runway rechecked immediately before wire.
        request = _read(root, "request.json", LIMITS.max_input_bytes)
        _request(request)
        dispatched = True
        delivered = None  # Attempted dispatch is not proof of arrival or ingestion.
        transport_failure = None
        try:
            raw = wire(request, LIMITS) if transport is None else transport(request, LIMITS)
        except Exception as exc:
            transport_failure = exc.code if isinstance(exc, PilotRefusal) else "transport_failed"
            failures.append(transport_failure)
        finally:
            if transport is not None:  # Test seam still captures before any parse.
                try:
                    response_capture = reservation.save(raw, returncode=0 if transport_failure is None else None,
                                                        process_failure=transport_failure)
                except (OSError, PilotRefusal):
                    failures.append("response_capture_failed")
            else:
                response_capture = wire.response_capture
                if wire.capture_failure:
                    failures.append("response_capture_failed")
                if raw is None and response_capture and response_capture.get("path"):
                    # A failed HTTP process can still have captured a complete
                    # accounting envelope. Partial JSON remains unknown usage.
                    raw = _read(reservation.directory, "stdout.bin", LIMITS.max_output_bytes + 1)
        require(raw is not None or bool(failures), "malformed_response")
        if raw is not None:
            require(type(raw) is bytes and len(raw) <= LIMITS.max_output_bytes, "output_limit_exceeded")
            try:
                data = _strict_json(raw)
                require(type(data) is dict, "malformed_response")
                raw_usage = data.get("usage") if type(data.get("usage")) is dict else None
                usage = _usage(raw_usage)
                require(data.get("model") == QWEN_MODEL, "model_identity_mismatch")
                choices = data.get("choices")
                require(type(choices) is list and len(choices) == 1 and type(choices[0]) is dict, "choices_invalid")
                choice = choices[0]
                message = choice.get("message")
                require(type(message) is dict and message.get("role") == "assistant", "malformed_response")
                require(choice.get("finish_reason") in {"stop", "length"}, "provider_finish_invalid")
                content = message.get("content")
                reasoning = message.get("reasoning", message.get("reasoning_content"))
                require(content is None or isinstance(content, str), "malformed_response")
                require(reasoning is None or isinstance(reasoning, str), "malformed_response")
                delivered = True  # Response observed, NOT proof all evidence was processed.
                shape = {"finish_reason": choice["finish_reason"], "content_bytes": len((content or "").encode()),
                         "reasoning_bytes": len(reasoning.encode()) if reasoning is not None else None}
                require(not message.get("tool_calls"), "native_tool_calls_denied")
            except PilotRefusal:
                raise
            except (ValueError, TypeError, KeyError):
                raise PilotRefusal("malformed_response") from None
    except Exception as exc:
        failures.append(exc.code if isinstance(exc, PilotRefusal) else "probe_failed")
    finally:
        if dispatched:
            for check in (lambda: observe("identity-after.json", "identity_drift"),
                          lambda: _authority(root, approval, confirmation, runway=False)):
                try:
                    check()
                except Exception as exc:
                    failures.append(exc.code if isinstance(exc, PilotRefusal) else "invalid_proposal")
    if usage["output_tokens"] is not None and usage["output_tokens"] > LIMITS.max_output_tokens:
        failures.append("output_tokens_exceeded")
    result = {"schema": "harnessie-evidence-timing-result/1", "outcome": failures[0] if failures else "response_received",
              "failures": failures, "proposal_sha256": confirmation, "request_sha256": REQUEST_SHA256,
              "elapsed_s": time.monotonic() - started, "transport_dispatched": dispatched,
              "delivered": delivered, "evidence_ingestion": "unknown", "response_shape": shape,
              "usage": usage, "raw_provider_usage": raw_usage, "actual_dollar_cost": None,
              "response_capture": response_capture, "diagnostics": wire.diagnostics,
              "review_accepted": False, "semantic_acceptance": False, "human_arbitrated": False,
              "executed_tools": 0, "retries": 0}
    try:
        _save(attempt, "outcome.json", result)
    except OSError as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc
    return result
