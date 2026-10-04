"""Consume-once full-evidence local review, never human arbitration.

Only the exact approved original request is eligible. Fresh identity is required
at dispatch, then re-observed after the bounded twenty-minute call. This trusted
operator API records an approval; it does not authenticate the approving human.
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
from scripts.pilot_contract import PilotLimits, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_evidence_handoff import validate_review
from scripts.pilot_execution import implementation_hashes, require, timestamp, utc_now
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_preflight import local_qwen_identity
from scripts.pilot_prepare import _read
from scripts.pilot_qwen import _strict_json, _unknown_usage, _usage
from scripts.pilot_qwen_capture import EvidenceReviewQwenTransport
from scripts.pilot_qwen_smoke import _save

ENDPOINT = "http://127.0.0.1:11434/v1"
REQUEST_SHA256 = "a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c"
REQUEST_BYTES = 212224
LIMITS = PilotLimits(max_calls=1, timeout_s=1200, max_input_bytes=256000,
                     max_evidence_bytes=256000, max_output_bytes=128000, max_output_tokens=4096)
RUNWAY_S = 1320
ACTION = "execute_one_local_qwen_evidence_review"
TIMING_POLICY = {"schema": "harnessie-evidence-review-fresh-at-start/1",
                 "identity_max_age_s_at_start": 900,
                 "identity_checks": ["initial_authority", "immediately_before_dispatch", "after_response"],
                 "postflight": "fresh matching identity and unexpired authority; no original-observation age or new runway"}


def harness_identity() -> dict:
    return {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": ENDPOINT,
            "prompt_sha256": REQUEST_SHA256, "parser_version": PARSER_VERSION,
            "sampling": {"temperature": 0.0}}


def _request(raw: bytes) -> None:
    # This approved exact hash binds all 17 full sources, schema and system text.
    require(type(raw) is bytes and len(raw) == REQUEST_BYTES <= LIMITS.max_input_bytes
            and hashlib.sha256(raw).hexdigest() == REQUEST_SHA256, "request_drift")


def _fixed(root: Path) -> dict:
    return {"schema": "harnessie-evidence-review/1", "status": "proposal_not_authorization",
            "live_allowance": 0, "root": str(root), "endpoint": ENDPOINT, "model": QWEN_MODEL,
            "limits": asdict(LIMITS), "request_sha256": REQUEST_SHA256, "request_bytes": REQUEST_BYTES,
            "execute_tools": False, "retries": 0, "minimum_runway_s": RUNWAY_S,
            "timing_policy": deepcopy(TIMING_POLICY), "purpose": "independent_full_evidence_review",
            "semantic_acceptance": False, "human_arbitrated": False,
            "declared_harness_identity": harness_identity(), "implementation_sha256": implementation_hashes()}


def prepare(root: Path, request: bytes, expected_identity: dict,
            identity_checked_at: str) -> dict:
    """Preserve the exact request privately, with zero calls and no metadata I/O."""
    root = root.absolute()
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


def _authority(root: Path, approval: dict | None, confirmation: str | None, *, before_dispatch: bool = True) -> dict:
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
    if before_dispatch:
        require(timedelta(0) <= now - timestamp(proposal["identity_checked_at"])
                <= timedelta(seconds=TIMING_POLICY["identity_max_age_s_at_start"]), "qwen_identity_stale")
        deadline = min(timestamp(approval["expires_at"]), timestamp(proposal["expires_at"]))
        require(deadline - now >= timedelta(seconds=RUNWAY_S), "insufficient_runway")
    return proposal


def execute(root: Path, approval: dict | None = None, confirmation: str | None = None, *,
            identity_capture: Callable[[], dict] | None = None,
            transport: Callable[[bytes, PilotLimits], bytes] | None = None) -> dict:
    """Capture one native response, independently retain usage, then gate receipt.

    review_received means complete structure and allowed citation paths, not
    truthful findings, semantic grounding, panel completion or human arbitration.
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
    wire = EvidenceReviewQwenTransport(reservation)
    failures: list[str] = []
    dispatched = False
    delivered = False
    raw = None
    response_capture = None
    usage = _unknown_usage()
    raw_usage = None
    parsed_review = None
    validation = None
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
        _authority(root, approval, confirmation)
        request = _read(root, "request.json", LIMITS.max_input_bytes)
        _request(request)
        dispatched = True
        delivered = None  # Dispatch alone proves neither arrival nor ingestion.
        transport_failure = None
        try:
            raw = wire(request, LIMITS) if transport is None else transport(request, LIMITS)
        except Exception as exc:
            transport_failure = exc.code if isinstance(exc, PilotRefusal) else "transport_failed"
            failures.append(transport_failure)
        finally:
            if transport is not None:  # The injected test seam still captures before parsing.
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
                delivered = True
                shape = {"finish_reason": choice["finish_reason"], "content_bytes": len((content or "").encode()),
                         "reasoning_bytes": len(reasoning.encode()) if reasoning is not None else None}
                require(not message.get("tool_calls"), "native_tool_calls_denied")
                require(choice["finish_reason"] == "stop", "incomplete_review")
            except PilotRefusal:
                raise
            except (ValueError, TypeError, KeyError):
                raise PilotRefusal("malformed_response") from None
            try:
                candidate = _strict_json(content) if isinstance(content, str) else None
                validation = validate_review(candidate)
                parsed_review = candidate
            except PilotRefusal:
                raise
            except (ValueError, TypeError):
                raise PilotRefusal("invalid_review") from None
            try:
                _save(attempt, "parsed-review.json", parsed_review)
            except (OSError, PilotRefusal):
                raise PilotRefusal("evidence_persistence_failed") from None
    except Exception as exc:
        failures.append(exc.code if isinstance(exc, PilotRefusal) else "review_failed")
    finally:
        if dispatched:
            for check in (lambda: observe("identity-after.json", "identity_drift"),
                          lambda: _authority(root, approval, confirmation, before_dispatch=False)):
                try:
                    check()
                except Exception as exc:
                    failures.append(exc.code if isinstance(exc, PilotRefusal) else "invalid_proposal")
    if usage["output_tokens"] is not None and usage["output_tokens"] > LIMITS.max_output_tokens:
        failures.append("output_tokens_exceeded")
    if not failures and (not response_capture or response_capture.get("status") != "retained"
                         or response_capture.get("capture_complete") is not True):
        failures.append("response_capture_incomplete")
    received = not failures and parsed_review is not None
    result = {"schema": "harnessie-evidence-review-result/1", "outcome": failures[0] if failures else "review_received",
              "failures": failures, "proposal_sha256": confirmation, "request_sha256": REQUEST_SHA256,
              "elapsed_s": time.monotonic() - started, "transport_dispatched": dispatched,
              "delivered": delivered, "evidence_ingestion": "unknown", "response_shape": shape,
              "usage": usage, "raw_provider_usage": raw_usage, "actual_dollar_cost": None,
              "response_capture": response_capture, "diagnostics": wire.diagnostics,
              "review_received": received, "structural_validation": validation,
              "stance": parsed_review["stance"] if parsed_review is not None else None,
              "semantic_acceptance": False, "human_arbitrated": False, "executed_tools": 0, "retries": 0}
    try:
        _save(attempt, "outcome.json", result)
    except OSError as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc
    return result
