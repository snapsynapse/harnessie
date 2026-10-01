from __future__ import annotations

import hashlib
import json
import os

import pytest

from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_contract import PilotRefusal


def test_capture_writes_exact_stdout_before_durable_metadata(tmp_path):
    root = tmp_path.resolve() / "captures"
    store = ResponseCaptureStore(root, 8)
    handle = store.reserve(1)
    receipt = handle.save(b"hello", returncode=0, process_failure=None)
    assert handle.directory.is_absolute()
    assert (handle.directory / "stdout.bin").read_bytes() == b"hello"
    assert receipt["sha256"] == hashlib.sha256(b"hello").hexdigest()
    assert receipt["capture_complete"] is True
    metadata = json.loads((handle.directory / "receipt.json").read_text())
    assert metadata["path"] == str((handle.directory / "stdout.bin").absolute())
    assert os.stat(root).st_mode & 0o777 == 0o700
    assert os.stat(handle.directory).st_mode & 0o777 == 0o700
    assert os.stat(handle.directory / "stdout.bin").st_mode & 0o777 == 0o600
    assert os.stat(handle.directory / "receipt.json").st_mode & 0o777 == 0o600


def test_overflow_keeps_only_max_plus_one_prefix_and_marks_incomplete(tmp_path):
    handle = ResponseCaptureStore(tmp_path.resolve() / "captures", 3).reserve(1)
    receipt = handle.save(b"abcdef", returncode=None, process_failure="output_limit_exceeded")
    assert (handle.directory / "stdout.bin").read_bytes() == b"abcd"
    assert receipt["bytes"] == 4
    assert receipt["overflow_detected"] is True
    assert receipt["capture_complete"] is False


@pytest.mark.parametrize("failure", ["process_timeout", "process_start_failed"])
def test_incomplete_process_states_are_retained_without_raw_logging(tmp_path, failure):
    handle = ResponseCaptureStore(tmp_path.resolve() / "captures", 8).reserve(1)
    receipt = handle.save(None, returncode=None, process_failure=failure)
    assert receipt["status"] == "retained"
    assert receipt["path"] is None
    assert receipt["capture_complete"] is False
    assert (handle.directory / "receipt.json").exists()


def test_unknown_failure_or_missing_returncode_never_claims_complete(tmp_path):
    first = ResponseCaptureStore(tmp_path.resolve() / "one", 8).reserve(1)
    assert first.save(b"complete-bytes", returncode=None, process_failure=None)["capture_complete"] is False
    second = ResponseCaptureStore(tmp_path.resolve() / "two", 16).reserve(1)
    assert second.save(b"complete-bytes", returncode=1, process_failure="unrecognized")["capture_complete"] is False


def test_reservations_and_roots_are_exclusive_and_consume_once(tmp_path):
    root = tmp_path.resolve() / "captures"
    store = ResponseCaptureStore(root, 8)
    handle = store.reserve(1)
    with pytest.raises(PilotRefusal, match="response_capture_failed"):
        store.reserve(1)
    handle.save(b"x", returncode=1, process_failure="process_failed")
    with pytest.raises(PilotRefusal, match="response_capture_consumed"):
        handle.save(b"x", returncode=1, process_failure="process_failed")
    with pytest.raises(PilotRefusal, match="response_capture_path_invalid"):
        ResponseCaptureStore(root, 8)


def test_paths_and_write_failures_fail_closed_without_cleanup(monkeypatch, tmp_path):
    with pytest.raises(PilotRefusal, match="response_capture_path_invalid"):
        ResponseCaptureStore(tmp_path.resolve() / "a" / ".." / "captures", 8)
    handle = ResponseCaptureStore(tmp_path.resolve() / "captures", 8).reserve(1)
    import scripts.pilot_capture as module
    monkeypatch.setattr(module, "_fsync_directory", lambda path: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(PilotRefusal, match="response_capture_failed"):
        handle.save(b"evidence", returncode=0, process_failure=None)
    assert handle.directory.exists()
    assert (handle.directory / "stdout.bin").read_bytes() == b"evidence"
    with pytest.raises(PilotRefusal, match="response_capture_consumed"):
        handle.save(b"again", returncode=0, process_failure=None)


def test_symlink_and_metadata_collision_failures_do_not_overwrite(tmp_path, monkeypatch):
    target = tmp_path.resolve() / "target"
    target.mkdir()
    ancestor = tmp_path.resolve() / "linked-parent"
    ancestor.symlink_to(target, target_is_directory=True)
    with pytest.raises(PilotRefusal, match="response_capture_path_invalid"):
        ResponseCaptureStore(ancestor / "captures", 8)
    root = tmp_path.resolve() / "captures"
    handle = ResponseCaptureStore(root, 8).reserve(1)
    real_write = __import__("scripts.pilot_capture", fromlist=["_write_exclusive"])._write_exclusive
    import scripts.pilot_capture as module
    def fail_metadata(path, data):
        if path.name == "receipt.json":
            raise OSError("metadata disk failure")
        return real_write(path, data)
    monkeypatch.setattr(module, "_write_exclusive", fail_metadata)
    with pytest.raises(PilotRefusal, match="response_capture_failed"):
        handle.save(b"evidence", returncode=0, process_failure=None)
    assert (handle.directory / "stdout.bin").read_bytes() == b"evidence"
    with pytest.raises(PilotRefusal, match="response_capture_consumed"):
        handle.save(b"again", returncode=0, process_failure=None)
    collision = ResponseCaptureStore(tmp_path.resolve() / "collision", 8).reserve(1)
    (collision.directory / "stdout.bin").write_bytes(b"operator-file")
    with pytest.raises(PilotRefusal, match="response_capture_failed"):
        collision.save(b"new-bytes", returncode=0, process_failure=None)
    assert (collision.directory / "stdout.bin").read_bytes() == b"operator-file"
