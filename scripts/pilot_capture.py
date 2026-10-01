"""Durable private capture of one bounded Claude Code response stream.

This module never starts a process or interprets provider output.  It records
only the bounded stdout bytes supplied by its caller, before that caller parses
them.  Raw bytes are intentionally not redacted or logged elsewhere.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.pilot_contract import PilotRefusal


_INCOMPLETE_FAILURES = frozenset({
    "process_timeout", "output_limit_exceeded", "process_start_failed",
})
_KNOWN_FAILURES = _INCOMPLETE_FAILURES | frozenset({
    "input_limit_exceeded", "process_failed", "response_capture_failed",
})


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_exclusive(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("partial capture write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


class ResponseCaptureStore:
    """Exclusive private root for attempts in one operator-approved run."""

    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = self._validate_root(root)
        if type(max_bytes) is not int or max_bytes < 1:
            raise PilotRefusal("response_capture_invalid_limits")
        self.max_bytes = max_bytes
        try:
            os.mkdir(self.root, 0o700)
            _fsync_directory(self.root.parent)
            _fsync_directory(self.root)
        except OSError as exc:
            raise PilotRefusal("response_capture_failed") from exc

    def reserve(self, attempt: int) -> "ResponseCaptureReservation":
        if type(attempt) is not int or attempt < 1:
            raise PilotRefusal("response_capture_invalid_attempt")
        directory = self.root / f"attempt-{attempt:04d}"
        try:
            os.mkdir(directory, 0o700)
            _fsync_directory(self.root)
            _fsync_directory(directory)
        except OSError as exc:
            raise PilotRefusal("response_capture_failed") from exc
        return ResponseCaptureReservation(directory, self.max_bytes, attempt)

    @staticmethod
    def _validate_root(root: Path) -> Path:
        if not isinstance(root, Path) or not root.is_absolute() or ".." in root.parts:
            raise PilotRefusal("response_capture_path_invalid")
        absolute = root.absolute()
        if absolute.exists() or absolute.is_symlink() or absolute.name in {"", ".", ".."}:
            raise PilotRefusal("response_capture_path_invalid")
        ancestor = absolute.parent
        while ancestor != ancestor.parent:
            if ancestor.is_symlink():
                raise PilotRefusal("response_capture_path_invalid")
            ancestor = ancestor.parent
        if not absolute.parent.is_dir():
            raise PilotRefusal("response_capture_path_invalid")
        return absolute


class ResponseCaptureReservation:
    """One consume-once attempt directory. ``directory`` is absolute."""

    def __init__(self, directory: Path, max_bytes: int, attempt: int) -> None:
        self.directory = directory.absolute()
        self._max_bytes = max_bytes
        self._attempt = attempt
        self._consumed = False

    def save(
        self,
        stdout: bytes | None,
        *,
        returncode: int | None,
        process_failure: str | None,
    ) -> dict[str, Any]:
        if self._consumed:
            raise PilotRefusal("response_capture_consumed")
        self._consumed = True
        if stdout is not None and not isinstance(stdout, bytes):
            raise PilotRefusal("response_capture_failed")
        if returncode is not None and (type(returncode) is not int):
            raise PilotRefusal("response_capture_failed")
        failure = process_failure if process_failure in _KNOWN_FAILURES else (
            None if process_failure is None else "unclassified")
        stored = stdout
        overflow = stdout is not None and len(stdout) > self._max_bytes
        if overflow:
            stored = stdout[:self._max_bytes + 1]
        stdout_path: Path | None = None
        try:
            if stored is not None:
                stdout_path = self.directory / "stdout.bin"
                _write_exclusive(stdout_path, stored)
                _fsync_directory(self.directory)
            # A complete capture means bounded bytes reached an observed EOF.
            # A nonzero process can still have complete stdout, but unknown
            # failures or no return code cannot establish that boundary.
            complete = (stdout is not None and not overflow and returncode is not None
                        and failure in {None, "process_failed"})
            receipt: dict[str, Any] = {
                "schema": "harnessie-response-capture/v1",
                "status": "retained",
                "attempt": self._attempt,
                "returncode": returncode,
                "process_failure": failure,
                "path": str(stdout_path.absolute()) if stdout_path is not None else None,
                "sha256": hashlib.sha256(stored).hexdigest() if stored is not None else None,
                "bytes": len(stored) if stored is not None else None,
                "capture_complete": complete,
                "overflow_detected": overflow,
            }
            metadata_path = self.directory / "receipt.json"
            _write_exclusive(metadata_path, _canonical(receipt))
            _fsync_directory(self.directory)
            receipt["metadata_path"] = str(metadata_path.absolute())
            return receipt
        except (OSError, TypeError, ValueError) as exc:
            # The reservation remains consumed and any bytes written remain
            # available for operator inspection.  No cleanup or retry occurs.
            raise PilotRefusal("response_capture_failed") from exc
