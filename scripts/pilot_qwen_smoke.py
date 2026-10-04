"""Prepare one local Qwen smoke. The CLI cannot dispatch or create approval.

The execution API is for trusted operator code after separate human approval.
Like pilot_execution, it binds an external seal and approval record; it does not
authenticate a human or defend against arbitrary code running as the owner.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from typing import Callable

from harness.models.base import Message, ModelSpec
from harness.verify import PARSER_VERSION
from scripts.pilot_capture import ResponseCaptureStore, _fsync_directory, _write_exclusive
from scripts.pilot_claude_code import ClaudeCodePilot
from scripts.pilot_contract import CallAllowance, PilotLimits, PilotRefusal, QWEN_MODEL, digest_json
from scripts.pilot_execution import implementation_hashes, require, timestamp, utc_now
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_preflight import local_qwen_identity
from scripts.pilot_prepare import _read
from scripts.pilot_qwen import QwenPilot, _child_transport, _strict_json

ENDPOINT = "http://127.0.0.1:11434/v1"
PROMPT = ("Return the exact text PILOT_SMOKE_OK using the requested response format. "
          "Do not request or execute tools.")
LIMITS = PilotLimits(max_calls=1, timeout_s=120, max_input_bytes=4096,
                     max_evidence_bytes=4096, max_output_tokens=1024,
                     max_output_bytes=128000)


def request_bytes() -> bytes:
    """Build fixed synthetic bytes without needing or inventing model identity."""
    prompt = ClaudeCodePilot._request_prompt([Message("user", PROMPT)], [])
    data = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "Return only the strict neutral structured response. Do not execute tools."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "harnessie_neutral_turn", "strict": True,
            "schema": ClaudeCodePilot._output_schema()}},
        "max_tokens": 1024, "temperature": 0.0, "stream": False,
    }
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def harness_identity() -> dict:
    return {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": ENDPOINT,
            "prompt_sha256": hashlib.sha256(request_bytes()).hexdigest(),
            "parser_version": PARSER_VERSION, "sampling": {"temperature": 0.0}}


def _save(root: Path, name: str, data: bytes | dict) -> None:
    require(not root.is_symlink() and all(not p.is_symlink() for p in root.parents), "unsafe_path")
    raw = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True, indent=2, allow_nan=False).encode()
    _write_exclusive(root / name, raw)
    _fsync_directory(root)


def prepare(root: Path, *, expected_identity: dict | None = None,
            identity_checked_at: str | None = None) -> dict:
    """No service access. Supplied metadata is only a future candidate input."""
    root = root.absolute()
    if expected_identity is not None:
        assert_same_identity(expected_identity, expected_identity)
        require(expected_identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
        require(identity_checked_at is not None, "identity_timestamp_required")
        timestamp(identity_checked_at)
    else:
        require(identity_checked_at is None, "identity_timestamp_invalid")
    request = request_bytes()
    require(len(request) <= LIMITS.max_input_bytes, "input_limit_exceeded")
    now = utc_now()
    proposal = {
        "schema": "harnessie-qwen-smoke/v1", "status": "proposal_not_authorization",
        "live_allowance": 0, "root": str(root), "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "endpoint": ENDPOINT, "model": QWEN_MODEL, "limits": asdict(LIMITS),
        "tools": [], "decision_evidence": [], "retries": 0,
        "request_sha256": hashlib.sha256(request).hexdigest(), "request_bytes": len(request),
        "declared_harness_identity": harness_identity(),
        "expected_identity": expected_identity, "identity_checked_at": identity_checked_at,
        "implementation_sha256": implementation_hashes(),
        "acceptance": "exact PILOT_SMOKE_OK; completed receipt; complete usage; unchanged identity; output_tokens <= 1024",
    }
    ResponseCaptureStore(root, LIMITS.max_output_bytes)
    _save(root, "request.json", request)
    _save(root, "proposal.json", proposal)
    return proposal


def _authority(root: Path, approval: dict | None, confirmation: str | None) -> dict:
    require(type(approval) is dict and isinstance(confirmation, str), "live_authority_required")
    for name in ("proposal.json", "request.json"):
        info = (root / name).lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_mode & 0o077 == 0, "unsafe_evidence_file")
    require(not root.is_symlink() and root.stat().st_mode & 0o077 == 0, "unsafe_evidence_directory")
    proposal = _strict_json(_read(root, "proposal.json", 1_500_000))
    require(type(proposal) is dict, "invalid_proposal")
    seal = digest_json(proposal)
    require(confirmation == seal, "proposal_drift")
    require(set(approval) == {"proposal_sha256", "approved_by", "action", "approved_at", "expires_at"}
            and approval["proposal_sha256"] == seal and approval["approved_by"] == "Sam Rogers"
            and approval["action"] == "execute_one_local_qwen_smoke", "invalid_live_authority")
    now = utc_now()
    require(timestamp(approval["approved_at"]) <= now < timestamp(approval["expires_at"])
            <= timestamp(proposal["expires_at"]), "live_authority_expired")
    require(proposal["schema"] == "harnessie-qwen-smoke/v1"
            and proposal["status"] == "proposal_not_authorization" and proposal["live_allowance"] == 0
            and proposal["root"] == str(root) and proposal["endpoint"] == ENDPOINT
            and proposal["model"] == QWEN_MODEL and proposal["limits"] == asdict(LIMITS)
            and proposal["tools"] == [] and proposal["decision_evidence"] == []
            and proposal["retries"] == 0, "invalid_proposal")
    require(proposal["implementation_sha256"] == implementation_hashes(), "implementation_drift")
    request = _read(root, "request.json", LIMITS.max_input_bytes)
    require(request == request_bytes() and proposal["request_bytes"] == len(request)
            and proposal["request_sha256"] == hashlib.sha256(request).hexdigest(), "request_drift")
    require(proposal["declared_harness_identity"] == harness_identity(), "qwen_configuration_drift")
    identity = proposal["expected_identity"]
    assert_same_identity(identity, identity)
    require(identity["harness_identity"] == harness_identity(), "qwen_configuration_drift")
    require(timedelta(0) <= now - timestamp(proposal["identity_checked_at"]) <= timedelta(minutes=15),
            "qwen_identity_stale")
    return proposal


def execute(root: Path, approval: dict | None = None, confirmation: str | None = None, *,
            identity_capture: Callable[[], dict] | None = None,
            transport: Callable[[bytes, PilotLimits], bytes] | None = None) -> dict:
    """Trusted operator entrypoint, default denied. Every attempt is consume-once."""
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
                                     "request_sha256": proposal["request_sha256"],
                                     "reserved_at": utc_now().isoformat(), "approval": approval})
    except OSError as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc

    failures: list[str] = []
    captures = 0
    expected = proposal["expected_identity"]
    capture = identity_capture or (lambda: local_qwen_identity(
        harness_identity(), expected["client_version"]))
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

    def observed_transport(request: bytes, limits: PilotLimits) -> bytes:
        raw = (transport or _child_transport)(request, limits)
        if isinstance(raw, bytes):
            try:
                _save(attempt, "response.bin", raw[:LIMITS.max_output_bytes + 1])
            except OSError:
                # Let the adapter retain usage before applying this refusal.
                failures.append("evidence_persistence_failed")
        return raw

    adapter = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, ENDPOINT), expected,
                        observed_identity, CallAllowance(LIMITS), observed_transport)
    turn = adapter.complete([Message("user", PROMPT)], [])
    receipt = adapter.receipts[-1].as_dict()
    outcome = receipt["failure"] or "completed"
    if outcome == "completed" and (turn.content != "PILOT_SMOKE_OK" or turn.tool_calls
                                   or turn.stop_reason != "end_turn"):
        outcome = "sentinel_mismatch"
    if receipt["usage"]["output_tokens"] is not None and receipt["usage"]["output_tokens"] > 1024:
        outcome = "output_tokens_exceeded"
    if failures:
        outcome = failures[0]
    result = {"schema": "harnessie-qwen-smoke-result/v1", "outcome": outcome,
              "proposal_sha256": confirmation, "request_sha256": proposal["request_sha256"],
              "elapsed_s": time.monotonic() - started, "receipt": receipt}
    try:
        _save(attempt, "outcome.json", result)
    except OSError as exc:
        raise PilotRefusal("evidence_persistence_failed") from exc
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new private candidate directory")
    args = parser.parse_args()
    proposal = prepare(args.destination)
    print(json.dumps({"proposal_sha256": digest_json(proposal), "root": proposal["root"],
                      "live_allowance": 0, "identity": "pending", "live_model_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
