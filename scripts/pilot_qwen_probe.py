"""Consume-once local Qwen diagnostic. Preparation never grants live authority.

Only the sealed first v8 request is eligible. Tool requests are parsed and saved,
never executed. This trusted operator API does not authenticate human approval.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from typing import Callable

from harness.models.base import ModelSpec
from harness.verify import PARSER_VERSION
from scripts.pilot_capture import ResponseCaptureStore, _fsync_directory
from scripts.pilot_contract import CallAllowance, PilotLimits, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_execution import implementation_hashes, require, timestamp, utc_now
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_preflight import local_qwen_identity
from scripts.pilot_prepare import _read
from scripts.pilot_qwen import QwenPilot, _strict_json
from scripts.pilot_qwen_smoke import _save
from scripts.pilot_request_metrics import PreparedPilotRequest

ENDPOINT = "http://127.0.0.1:11434/v1"
REQUEST_SHA256 = "d7d2f89f843d51db3a1beabf83cd8595b8bbf9ea86a0dbfd42b79b645b503be6"
REQUEST_BYTES = 6568
TOOL_NAMES = {"read_file", "list_files", "task_complete"}
LIMITS = PilotLimits(max_calls=1, timeout_s=300, max_input_bytes=256000,
                     max_evidence_bytes=256000, max_output_bytes=128000,
                     max_output_tokens=4096)
RUNWAY_S = 330


def harness_identity() -> dict:
    return {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": ENDPOINT,
            "prompt_sha256": REQUEST_SHA256, "parser_version": PARSER_VERSION,
            "sampling": {"temperature": 0.0}}


def _request(request: bytes) -> tuple[list[dict], int]:
    require(type(request) is bytes and len(request) == REQUEST_BYTES
            and hashlib.sha256(request).hexdigest() == REQUEST_SHA256, "request_drift")
    data = _strict_json(request)
    require(type(data) is dict and data.get("model") == QWEN_MODEL
            and data.get("max_tokens") == LIMITS.max_output_tokens
            and data.get("temperature") == 0.0 and data.get("stream") is False,
            "invalid_request")
    prompt = data["messages"][1]["content"]
    inner = _strict_json(prompt)
    tools = inner["tools"]
    require(type(tools) is list and len(tools) == 3
            and {tool["name"] for tool in tools} == TOOL_NAMES
            and all(type(tool.get("parameters")) is dict for tool in tools), "invalid_tools")
    require(len(request) <= LIMITS.max_input_bytes
            and sum(len(m["content"].encode()) for m in inner["messages"]
                    if m["role"] == "tool") <= LIMITS.max_evidence_bytes, "input_limit_exceeded")
    return tools, len(prompt.encode())


def prepare(root: Path, request: bytes, expected_identity: dict,
            identity_checked_at: str) -> dict:
    """Create private immutable proposal files with zero calls and no metadata I/O."""
    root = root.absolute()
    tools, _ = _request(request)
    assert_same_identity(expected_identity, expected_identity)
    require(expected_identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    timestamp(identity_checked_at)
    now = utc_now()
    proposal = {
        "schema": "harnessie-qwen-probe/v1", "status": "proposal_not_authorization",
        "live_allowance": 0, "root": str(root), "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "endpoint": ENDPOINT, "model": QWEN_MODEL, "limits": asdict(LIMITS),
        "request_sha256": REQUEST_SHA256, "request_bytes": REQUEST_BYTES,
        "tools": tools, "execute_tools": False, "retries": 0, "minimum_runway_s": RUNWAY_S,
        "expected_identity": expected_identity, "identity_checked_at": identity_checked_at,
        "declared_harness_identity": harness_identity(),
        "implementation_sha256": implementation_hashes(),
    }
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
            and approval["action"] == "execute_one_local_qwen_probe", "invalid_live_authority")
    now = utc_now()
    require(timestamp(approval["approved_at"]) <= now < timestamp(approval["expires_at"])
            <= timestamp(proposal["expires_at"]), "live_authority_expired")
    tools, _ = _request(_read(root, "request.json", LIMITS.max_input_bytes))
    fixed = {"schema": "harnessie-qwen-probe/v1", "status": "proposal_not_authorization",
             "live_allowance": 0, "root": str(root), "endpoint": ENDPOINT, "model": QWEN_MODEL,
             "limits": asdict(LIMITS), "request_sha256": REQUEST_SHA256, "request_bytes": REQUEST_BYTES,
             "tools": tools, "execute_tools": False, "retries": 0, "minimum_runway_s": RUNWAY_S,
             "declared_harness_identity": harness_identity(), "implementation_sha256": implementation_hashes()}
    require(set(proposal) == set(fixed) | {"created_at", "expires_at", "expected_identity", "identity_checked_at"},
            "invalid_proposal")
    require(proposal["implementation_sha256"] == fixed["implementation_sha256"], "implementation_drift")
    # Canonical comparison distinguishes booleans and floats from integer limits.
    require(digest_json({key: proposal[key] for key in fixed}) == digest_json(fixed), "invalid_proposal")
    require(timestamp(proposal["created_at"]) <= now, "invalid_proposal")
    identity = proposal["expected_identity"]
    assert_same_identity(identity, identity)
    require(identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    require(timedelta(0) <= now - timestamp(proposal["identity_checked_at"]) <= timedelta(minutes=15),
            "qwen_identity_stale")
    if runway:
        earliest_deadline = min(timestamp(approval["expires_at"]), timestamp(proposal["expires_at"]),
                                timestamp(proposal["identity_checked_at"]) + timedelta(minutes=15))
        require(earliest_deadline - now >= timedelta(seconds=RUNWAY_S),
                "insufficient_runway")
    return proposal


def execute(root: Path, approval: dict | None = None, confirmation: str | None = None, *,
            identity_capture: Callable[[], dict] | None = None,
            transport: Callable[[bytes, PilotLimits], bytes] | None = None) -> dict:
    """Run exactly one approved request, returning only content-free diagnostics."""
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
                                     "request_sha256": REQUEST_SHA256,
                                     "reserved_at": utc_now().isoformat(), "approval": approval})
        reservation = ResponseCaptureStore(attempt / "responses", LIMITS.max_output_bytes).reserve(1)
    except (OSError, PilotRefusal) as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc

    failures: list[str] = []
    captures = 0
    expected = proposal["expected_identity"]
    capture = identity_capture or (lambda: local_qwen_identity(harness_identity(), expected["client_version"]))
    def observed_identity() -> dict:
        nonlocal captures
        value = capture()
        name = "identity-before.json" if captures == 0 else "identity-after.json"
        captures += 1
        try:
            _save(attempt, name, value)
        except OSError:
            failures.append("evidence_persistence_failed")
            raise
        return value

    if transport is None:
        from scripts.pilot_qwen_capture import CapturedQwenTransport
        wire = CapturedQwenTransport(reservation, timeout_ceiling_s=300)
    else:
        # Test seam: retain injected bytes with the same private reservation.
        class InjectedTransport:
            response_capture = None
            diagnostics = None
            capture_failure = None

            def __call__(self, request, limits):
                raw = None
                failure = None
                try:
                    raw = transport(request, limits)
                    return raw
                except Exception as exc:
                    failure = exc.code if isinstance(exc, PilotRefusal) else "process_failed"
                    raise
                finally:
                    try:
                        self.response_capture = reservation.save(raw, returncode=0 if failure is None else None,
                                                                 process_failure=failure)
                    except (OSError, PilotRefusal):
                        self.capture_failure = "response_capture_failed"
        wire = InjectedTransport()

    transport_dispatched = False

    def observed_transport(request: bytes, limits: PilotLimits) -> bytes:
        nonlocal transport_dispatched
        # This last gate runs after metadata capture, immediately before dispatch.
        _authority(root, approval, confirmation)
        require(request == _read(root, "request.json", LIMITS.max_input_bytes), "request_drift")
        transport_dispatched = True
        return wire(request, limits)

    request = _read(root, "request.json", LIMITS.max_input_bytes)
    tools, inner_size = _request(request)
    adapter = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, ENDPOINT), expected,
                        observed_identity, CallAllowance(LIMITS), observed_transport)
    turn = adapter.complete_prepared(PreparedPilotRequest(
        request, "ollama-loopback-openai-compat", "openai-compatible-json-with-neutral-json-string", inner_size), tools)
    receipt = adapter.receipts[-1].as_dict()
    outcome = receipt["failure"] or "completed"
    # There is no second dispatch, so do not demand another full call's runway.
    # Expired authority still refuses acceptance while preserving known usage.
    if transport_dispatched:
        try:
            _authority(root, approval, confirmation, runway=False)
        except (OSError, KeyError, TypeError, ValueError, PilotRefusal) as exc:
            outcome = exc.code if isinstance(exc, PilotRefusal) else "invalid_proposal"
    if receipt["usage"]["output_tokens"] is not None and receipt["usage"]["output_tokens"] > LIMITS.max_output_tokens:
        outcome = "output_tokens_exceeded"
    try:
        _save(attempt, "parsed-turn.json", asdict(turn))
    except (OSError, TypeError, ValueError):
        failures.append("evidence_persistence_failed")
    if wire.capture_failure:
        failures.append("response_capture_failed")
    if failures:
        outcome = failures[0]
    result = {"schema": "harnessie-qwen-probe-result/v1", "outcome": outcome,
              "proposal_sha256": confirmation, "request_sha256": REQUEST_SHA256,
              "elapsed_s": time.monotonic() - started, "receipt": receipt,
              "transport_dispatched": transport_dispatched,
              "response_capture": wire.response_capture, "diagnostics": wire.diagnostics,
              "turn_shape": {"content_bytes": len(turn.content.encode()),
                             "tool_names": [call.name for call in turn.tool_calls],
                             "stop_reason": turn.stop_reason}, "executed_tools": 0, "retries": 0}
    try:
        _save(attempt, "outcome.json", result)
    except OSError as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc
    return result
