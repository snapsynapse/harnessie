"""Durable, offline, one-shot ledger for an explicitly approved pilot run.

The ledger contains no provider code.  Its ``usage`` counters include input,
output, cache creation, and cache read tokens.  A Qwen receipt may report
cache counters as zero only when its protocol has included the full prompt in
its classified input accounting.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.pilot_contract import PilotRefusal
from scripts.pilot_policy import HAIKU_MODEL
from scripts.pilot_stream import _loads


STAGES = (
    "claude:position", "qwen:position", "claude:objection", "qwen:objection",
)
USAGE_KEYS = (
    "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
)
REQUIRED_LIMITS = {
    "calls": {"claude": 8, "qwen": 8},
    "calls_per_stage": 4,
    "total_tokens": 160000,
    "haiku_input_tokens": 32768,
    "haiku_output_tokens": 2048,
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _zero_usage() -> dict[str, int]:
    return {key: 0 for key in USAGE_KEYS}


class RunLedger:
    """Create exactly one run directory; reopening and automatic recovery refuse."""

    def __init__(self, directory: Path, manifest_sha256: str, limits: dict) -> None:
        self.directory = self._validate_directory(directory)
        self._validate_manifest(manifest_sha256)
        self._validate_limits(limits)
        self.manifest_sha256 = manifest_sha256
        self.limits = json.loads(_canonical(limits))
        self.journal_path = self.directory / "ledger.jsonl"
        self._fd: int | None = None
        self._closed = False
        self._halted = False
        self._active: dict[str, str] | None = None
        self._sequence = 0
        self._previous_hash = ""
        self._calls = {"claude": 0, "qwen": 0}
        self._stage_calls: dict[str, int] = {}
        self._usage = _zero_usage()
        self._haiku_input_tokens = 0
        self._haiku_output_tokens = 0
        self._accounting_unknown = False
        self._last_stage = -1
        self._create()

    def __enter__(self) -> "RunLedger":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def reserve(self, stage: str, participant: str) -> str:
        self._ready()
        if self._active is not None:
            raise PilotRefusal("ledger_attempt_active")
        if participant not in self._calls or not isinstance(stage, str) or stage not in STAGES:
            raise PilotRefusal("ledger_stage_invalid")
        if not stage.startswith(participant + ":"):
            raise PilotRefusal("ledger_participant_mismatch")
        stage_index = STAGES.index(stage)
        if stage_index < self._last_stage or stage_index > self._last_stage + 1:
            raise PilotRefusal("ledger_stage_order_invalid")
        if sum(self._usage.values()) >= self.limits["total_tokens"]:
            self.halt("total_token_budget_exceeded")
            raise PilotRefusal("total_token_budget_exceeded")
        if self._haiku_input_tokens >= self.limits["haiku_input_tokens"]:
            self.halt("haiku_input_budget_exceeded")
            raise PilotRefusal("haiku_input_budget_exceeded")
        if self._haiku_output_tokens >= self.limits["haiku_output_tokens"]:
            self.halt("haiku_output_budget_exceeded")
            raise PilotRefusal("haiku_output_budget_exceeded")
        if self._calls[participant] >= self.limits["calls"][participant]:
            self.halt("participant_call_budget_exhausted")
            raise PilotRefusal("participant_call_budget_exhausted")
        if self._stage_calls.get(stage, 0) >= self.limits["calls_per_stage"]:
            self.halt("stage_call_budget_exhausted")
            raise PilotRefusal("stage_call_budget_exhausted")
        attempt_id = f"attempt-{self._sequence + 1:04d}"
        self._append("reserve", {"attempt_id": attempt_id, "stage": stage, "participant": participant})
        self._active = {"id": attempt_id, "stage": stage, "participant": participant, "state": "reserved"}
        self._calls[participant] += 1
        self._stage_calls[stage] = self._stage_calls.get(stage, 0) + 1
        self._last_stage = max(self._last_stage, stage_index)
        return attempt_id

    def dispatched(self, attempt_id: str) -> None:
        active = self._require_active(attempt_id, "reserved")
        self._append("dispatched", {"attempt_id": attempt_id, "stage": active["stage"],
                                    "participant": active["participant"]})
        active["state"] = "dispatched"

    def finish(self, attempt_id: str, receipt: dict, accepted: bool) -> None:
        active = self._require_active(attempt_id, "dispatched")
        if type(accepted) is not bool or not isinstance(receipt, dict):
            self.halt("receipt_invalid")
            raise PilotRefusal("receipt_invalid")
        # Persist exact raw evidence before interpreting it or enforcing limits.
        try:
            _canonical(receipt)
        except (TypeError, ValueError):
            self.halt("receipt_invalid")
            raise PilotRefusal("receipt_invalid")
        self._append("receipt", {"attempt_id": attempt_id, "stage": active["stage"],
                                 "participant": active["participant"], "accepted": accepted,
                                 "receipt": receipt})
        self._active = None
        usage = self._usage_from(receipt)
        if usage is None:
            self._accounting_unknown = True
            self.halt("receipt_usage_unknown")
            raise PilotRefusal("receipt_usage_unknown")
        helper = self._haiku_usage(receipt)
        if helper is None:
            self._usage = {key: self._usage[key] + usage[key] for key in USAGE_KEYS}
            self._accounting_unknown = True
            self.halt("helper_usage_unknown")
            raise PilotRefusal("helper_usage_unknown")
        proposed = {key: self._usage[key] + usage[key] for key in USAGE_KEYS}
        proposed_total = sum(proposed.values())
        proposed_helper_input = self._haiku_input_tokens + helper[0]
        proposed_helper_output = self._haiku_output_tokens + helper[1]
        if proposed_total > self.limits["total_tokens"]:
            self._usage = proposed
            self._haiku_input_tokens = proposed_helper_input
            self._haiku_output_tokens = proposed_helper_output
            self.halt("total_token_budget_exceeded")
            raise PilotRefusal("total_token_budget_exceeded")
        if proposed_helper_input > self.limits["haiku_input_tokens"]:
            self._usage = proposed
            self._haiku_input_tokens = proposed_helper_input
            self._haiku_output_tokens = proposed_helper_output
            self.halt("haiku_input_budget_exceeded")
            raise PilotRefusal("haiku_input_budget_exceeded")
        if proposed_helper_output > self.limits["haiku_output_tokens"]:
            self._usage = proposed
            self._haiku_input_tokens = proposed_helper_input
            self._haiku_output_tokens = proposed_helper_output
            self.halt("haiku_output_budget_exceeded")
            raise PilotRefusal("haiku_output_budget_exceeded")
        self._usage = proposed
        self._haiku_input_tokens = proposed_helper_input
        self._haiku_output_tokens = proposed_helper_output
        self._append("finish", {"attempt_id": attempt_id, "accepted": accepted,
                                "usage": usage, "haiku_input_tokens": helper[0],
                                "haiku_output_tokens": helper[1]})
        if not accepted:
            self.halt("receipt_refused")

    def halt(self, reason: str) -> None:
        if self._halted:
            return
        if reason not in {
            "participant_call_budget_exhausted", "stage_call_budget_exhausted", "receipt_invalid",
            "receipt_usage_unknown", "helper_usage_unknown", "total_token_budget_exceeded",
            "haiku_input_budget_exceeded", "haiku_output_budget_exceeded", "receipt_refused",
        }:
            reason = "ledger_halted"
        self._halted = True
        self._append("halt", {"reason": reason})

    def summary(self) -> dict:
        return {
            "manifest_sha256": self.manifest_sha256,
            "limits": self.limits,
            "calls": dict(self._calls),
            "calls_per_stage": dict(self._stage_calls),
            "usage": (dict(self._usage) if self._accounting_complete() else None),
            "known_usage": dict(self._usage),
            "haiku_input_tokens": self._haiku_input_tokens,
            "haiku_output_tokens": self._haiku_output_tokens,
            "active_attempt": None if self._active is None else dict(self._active),
            "halted": self._halted,
            "accounting_complete": self._accounting_complete(),
            "closed": self._closed,
        }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._fd is not None:
            failure: OSError | None = None
            try:
                os.fsync(self._fd)
            except OSError as exc:
                failure = exc
            finally:
                try:
                    os.close(self._fd)
                except OSError as exc:
                    failure = failure or exc
                self._fd = None
            if failure is not None:
                raise PilotRefusal("ledger_io_failure") from failure

    @staticmethod
    def _validate_directory(directory: Path) -> Path:
        if (not isinstance(directory, Path) or not directory.is_absolute()
                or directory.name in {"", ".", ".."} or ".." in directory.parts):
            raise PilotRefusal("ledger_path_invalid")
        parent = directory.parent
        ancestor = parent
        while ancestor != ancestor.parent:
            if ancestor.is_symlink():
                raise PilotRefusal("ledger_path_invalid")
            ancestor = ancestor.parent
        if not parent.is_dir() or parent.is_symlink() or directory.exists() or directory.is_symlink():
            raise PilotRefusal("ledger_directory_exists")
        return directory

    @staticmethod
    def _validate_manifest(value: str) -> None:
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise PilotRefusal("ledger_manifest_invalid")

    @staticmethod
    def _validate_limits(limits: dict) -> None:
        if not isinstance(limits, dict) or set(limits) != set(REQUIRED_LIMITS):
            raise PilotRefusal("ledger_limits_invalid")
        calls = limits.get("calls")
        if not isinstance(calls, dict) or set(calls) != {"claude", "qwen"}:
            raise PilotRefusal("ledger_limits_invalid")
        if any(type(calls[name]) is not int or calls[name] < 0 for name in calls):
            raise PilotRefusal("ledger_limits_invalid")
        for key in ("calls_per_stage", "total_tokens", "haiku_input_tokens", "haiku_output_tokens"):
            if type(limits.get(key)) is not int or limits[key] < 0:
                raise PilotRefusal("ledger_limits_invalid")

    def _create(self) -> None:
        try:
            os.mkdir(self.directory, 0o700)
            parent_fd = os.open(self.directory.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
            self._fd = os.open(self.journal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND, 0o600)
            journal_dir_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(journal_dir_fd)
            finally:
                os.close(journal_dir_fd)
            self._append("initial", {"manifest_sha256": self.manifest_sha256,
                                     "limits": self.limits, "stages": list(STAGES)})
        except OSError as exc:
            self._halted = True
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            raise PilotRefusal("ledger_io_failure") from exc

    def _append(self, kind: str, data: dict) -> None:
        if self._fd is None:
            self._halted = True
            raise PilotRefusal("ledger_io_failure")
        payload = {"sequence": self._sequence + 1, "kind": kind, "data": data,
                   "previous_hash": self._previous_hash}
        try:
            digest = _hash(payload)
            record = {**payload, "hash": digest}
            encoded = _canonical(record) + b"\n"
            if os.write(self._fd, encoded) != len(encoded):
                raise OSError("partial journal write")
            os.fsync(self._fd)
        except (OSError, TypeError, ValueError) as exc:
            self._halted = True
            raise PilotRefusal("ledger_io_failure") from exc
        self._sequence += 1
        self._previous_hash = digest

    def _ready(self) -> None:
        if self._closed or self._halted:
            raise PilotRefusal("ledger_halted")

    def _require_active(self, attempt_id: str, state: str) -> dict[str, str]:
        self._ready()
        if not isinstance(attempt_id, str) or self._active is None or self._active["id"] != attempt_id:
            raise PilotRefusal("ledger_attempt_invalid")
        if self._active["state"] != state:
            raise PilotRefusal("ledger_attempt_state_invalid")
        return self._active

    @staticmethod
    def _usage_from(receipt: dict) -> dict[str, int] | None:
        usage = receipt.get("usage")
        if not isinstance(usage, dict):
            return None
        values = {key: usage.get(key) for key in USAGE_KEYS}
        if any(type(value) is not int or value < 0 for value in values.values()):
            return None
        return values

    @staticmethod
    def _haiku_usage(receipt: dict) -> tuple[int, int] | None:
        models = receipt.get("model_usage")
        if not isinstance(models, dict):
            return None
        if HAIKU_MODEL not in models:
            return (0, 0)
        usage = models[HAIKU_MODEL]
        if not isinstance(usage, dict):
            return None
        values = {key: usage.get(key) for key in USAGE_KEYS}
        if any(type(value) is not int or value < 0 for value in values.values()):
            return None
        return (values["input_tokens"] + values["cache_creation_input_tokens"] + values["cache_read_input_tokens"],
                values["output_tokens"])

    def _accounting_complete(self) -> bool:
        return not self._accounting_unknown and self._active is None


def read_ledger_summary(directory: Path) -> dict:
    """Read-only integrity check.  It never opens a run for resumption."""
    path = directory / "ledger.jsonl"
    try:
        lines = path.read_bytes().splitlines()
    except OSError as exc:
        raise PilotRefusal("ledger_read_failed") from exc
    previous = ""
    for index, line in enumerate(lines, 1):
        try:
            record = _loads(line.decode("utf-8"))
            expected_keys = {"sequence", "kind", "data", "previous_hash", "hash"}
            if (not isinstance(record, dict) or set(record) != expected_keys
                    or type(record["sequence"]) is not int or record["sequence"] != index
                    or not isinstance(record["kind"], str) or not record["kind"]
                    or not isinstance(record["data"], dict)
                    or not isinstance(record["previous_hash"], str)
                    or record["previous_hash"] != previous):
                raise ValueError
            digest = record.get("hash")
            payload = {key: record[key] for key in ("sequence", "kind", "data", "previous_hash")}
            if not isinstance(digest, str) or _hash(payload) != digest:
                raise ValueError
            previous = digest
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError,
                ValueError, RecursionError, OverflowError):
            raise PilotRefusal("ledger_integrity_invalid")
    if not lines:
        raise PilotRefusal("ledger_integrity_invalid")
    return {"integrity": "valid", "records": len(lines), "tail_hash": previous}
