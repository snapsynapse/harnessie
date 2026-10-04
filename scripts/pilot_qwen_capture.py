"""Opt-in, single-use Qwen diagnostic transport with bounded private capture.

No retries, prompt changes, alternate endpoints, proxies or server control.
Killing our HTTP child is not evidence that the server stopped generating.
The legacy pilot_qwen transport and its 120-second ceiling remain unchanged.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from scripts.pilot_capture import ResponseCaptureReservation
from scripts.pilot_contract import PilotLimits, PilotRefusal
from scripts.pilot_qwen import _CHAT_URL, _NoRedirect, _kill_child_group, _strict_json


def _validate_config(config: dict) -> dict:
    if (type(config) is not dict or set(config) != {"timeout_s", "max_output_bytes"}
            or type(config["timeout_s"]) not in {int, float}
            or not math.isfinite(config["timeout_s"])
            or not 0 < config["timeout_s"] <= 300
            or type(config["max_output_bytes"]) is not int
            or not 0 < config["max_output_bytes"] <= 128000):
        raise PilotRefusal("invalid_qwen_capture_config")
    return config


def _validate_evidence_review_config(config: dict) -> dict:
    """Only the separately approved, fixed twenty-minute review profile."""
    if (type(config) is not dict or set(config) != {"timeout_s", "max_output_bytes"}
            or type(config["timeout_s"]) not in {int, float}
            or config["timeout_s"] != 1200
            or type(config["max_output_bytes"]) is not int
            or not 0 < config["max_output_bytes"] <= 128000):
        raise PilotRefusal("invalid_qwen_capture_config")
    return config


class CapturedQwenTransport:
    """A reserved response slot, consumed on first transport invocation.

    ``capture_failure`` is inspected by QwenPilot after accounting parse so a
    storage failure cannot produce an accepted turn or discard complete usage.
    Raw bytes never appear in diagnostics or exceptions.
    """

    _config_validator = staticmethod(_validate_config)
    _child_marker = "--captured-request-child"

    def __init__(self, reservation: ResponseCaptureReservation, *,
                 timeout_ceiling_s: float = 300) -> None:
        if type(reservation) is not ResponseCaptureReservation:
            raise PilotRefusal("invalid_qwen_capture_config")
        self._config_validator({"timeout_s": timeout_ceiling_s,
                                "max_output_bytes": reservation._max_bytes})
        self.reservation = reservation
        self.timeout_ceiling_s = timeout_ceiling_s
        self.response_capture: dict | None = None
        self.diagnostics: dict = {}
        self.capture_failure: str | None = None
        self._used = False

    def _transport_config(self, limits: PilotLimits) -> dict:
        return self._config_validator({
            "timeout_s": min(limits.timeout_s, self.timeout_ceiling_s),
            "max_output_bytes": limits.max_output_bytes})

    def __call__(self, payload: bytes, limits: PilotLimits) -> bytes:
        if self._used:
            raise PilotRefusal("transport_latched")
        self._used = True
        if not isinstance(payload, bytes) or len(payload) > limits.max_input_bytes:
            raise PilotRefusal("input_limit_exceeded")
        config = self._transport_config(limits)
        if limits.max_output_bytes != self.reservation._max_bytes:
            raise PilotRefusal("invalid_qwen_capture_config")
        started = time.monotonic()
        deadline = started + config["timeout_s"]
        raw = bytearray()
        diagnostic_raw = bytearray()
        first_byte = None
        process = None
        returncode = None
        failure = None
        child_failure = None
        http_status = None
        cleanup_attempted = False
        cleanup_exited = None
        selector = selectors.DefaultSelector()
        input_file = tempfile.TemporaryFile()
        try:
            input_file.write(payload)
            input_file.seek(0)
            root = Path(__file__).resolve().parents[1]
            process = subprocess.Popen(
                [sys.executable, __file__, self._child_marker, json.dumps(config)],
                stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, env={"PYTHONPATH": str(root)}, cwd=root,
            )
            assert process.stdout is not None and process.stderr is not None
            selector.register(process.stdout, selectors.EVENT_READ)
            selector.register(process.stderr, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PilotRefusal("process_timeout")
                for key, _ in selector.select(remaining):
                    is_body = key.fileobj is process.stdout
                    target = raw if is_body else diagnostic_raw
                    bound = config["max_output_bytes"] if is_body else 4096
                    block = os.read(key.fileobj.fileno(), min(65536, bound + 1 - len(target)))
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    if is_body and first_byte is None:
                        first_byte = time.monotonic() - started
                    target.extend(block)
                    if len(target) > bound:
                        raise PilotRefusal("output_limit_exceeded" if is_body else "transport_failed")
            try:
                returncode = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise PilotRefusal("process_timeout") from exc
            if diagnostic_raw:
                child = _strict_json(bytes(diagnostic_raw))
                if (type(child) is not dict or set(child) != {"failure", "http_status"}
                        or child["failure"] not in {
                            None, "http_timeout", "http_failed", "invalid_request", "output_limit_exceeded"}
                        or (child["http_status"] is not None
                            and (type(child["http_status"]) is not int
                                 or not 100 <= child["http_status"] <= 599))):
                    raise PilotRefusal("transport_failed")
                child_failure = child["failure"]
                http_status = child["http_status"]
            if child_failure == "http_timeout":
                raise PilotRefusal("process_timeout")
            if child_failure == "output_limit_exceeded":
                raise PilotRefusal("output_limit_exceeded")
            if returncode != 0 or child_failure:
                raise PilotRefusal("transport_failed")
        except PilotRefusal as exc:
            failure = exc.code
        except Exception:
            failure = "process_start_failed" if process is None else "transport_failed"
        finally:
            selector.close()
            if process is not None:
                if process.poll() is None:
                    cleanup_attempted = True
                    try:
                        _kill_child_group(process)
                    except Exception:
                        pass
                    cleanup_exited = process.poll() is not None
                returncode = process.poll()
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
            input_file.close()
            self.diagnostics = {
                "schema": "harnessie-qwen-transport-diagnostic/v1",
                "elapsed_s": time.monotonic() - started,
                "first_body_byte_s": first_byte,
                "received_bytes": len(raw),
                "returncode": returncode,
                "http_status": http_status,
                "supervisor_timeout_s": config["timeout_s"],
                "child_http_timeout_s": config["timeout_s"],
                "timeout_source": ("http_child" if child_failure == "http_timeout" else
                                   "supervisor" if failure == "process_timeout" else None),
                "failure": failure,
                "cleanup_attempted": cleanup_attempted,
                "cleanup_child_exited": cleanup_exited,
                "server_cancellation_confirmed": False,
            }
            try:
                self.response_capture = self.reservation.save(
                    bytes(raw), returncode=returncode, process_failure=failure)
            except Exception:
                self.capture_failure = "response_capture_failed"
                self.response_capture = {"status": "failed", "phase": "after_inference"}
        if failure is not None:
            raise PilotRefusal(self.capture_failure or failure)
        return bytes(raw)


class EvidenceReviewQwenTransport(CapturedQwenTransport):
    """Explicit fixed twenty-minute transport for the approved evidence review.

    This does not alter the legacy diagnostic profile or accept caller-chosen
    timeout ceilings. The caller's limits must match the review profile.
    """

    _config_validator = staticmethod(_validate_evidence_review_config)
    _child_marker = "--evidence-review-request-child"

    def __init__(self, reservation: ResponseCaptureReservation) -> None:
        super().__init__(reservation, timeout_ceiling_s=1200)

    def _transport_config(self, limits: PilotLimits) -> dict:
        return self._config_validator({"timeout_s": limits.timeout_s,
                                       "max_output_bytes": limits.max_output_bytes})


def _request_child(config: dict) -> int:
    """Legacy diagnostic child, still limited to at most 300 seconds."""
    _validate_config(config)
    return _request_child_io(config)


def _evidence_review_request_child(config: dict) -> int:
    """Explicit review child, accepting only the fixed 1200-second profile."""
    _validate_evidence_review_config(config)
    return _request_child_io(config)


def _request_child_io(config: dict) -> int:
    """Flush each bounded response prefix before another HTTP read can fail."""
    failure = None
    http_status = None
    try:
        raw = sys.stdin.buffer.read(PilotLimits().max_input_bytes + 1)
        if len(raw) > PilotLimits().max_input_bytes:
            raise ValueError()
        _strict_json(raw)
    except (ValueError, TypeError):
        failure = "invalid_request"
    if failure is None:
        request = Request(_CHAT_URL, data=raw, method="POST",
                          headers={"Content-Type": "application/json"})
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        received = 0
        try:
            with opener.open(request, timeout=config["timeout_s"]) as response:
                http_status = getattr(response, "status", None)
                while True:
                    block = response.read1(min(65536, config["max_output_bytes"] + 1 - received))
                    if not block:
                        break
                    sys.stdout.buffer.write(block)
                    sys.stdout.buffer.flush()
                    received += len(block)
                    if received > config["max_output_bytes"]:
                        failure = "output_limit_exceeded"
                        break
        except TimeoutError:
            failure = "http_timeout"
        except HTTPError as exc:
            http_status = exc.code
            failure = "http_failed"
        except URLError as exc:
            failure = "http_timeout" if isinstance(exc.reason, TimeoutError) else "http_failed"
        except (OSError, ValueError):
            failure = "http_failed"
    sys.stderr.buffer.write(json.dumps({"failure": failure, "http_status": http_status}).encode())
    sys.stderr.buffer.flush()
    return 0 if failure is None else 2


def _child_main(argv: list[str]) -> int:
    handlers = {
        "--captured-request-child": _request_child,
        "--evidence-review-request-child": _evidence_review_request_child,
    }
    if len(argv) != 3 or argv[1] not in handlers:
        return 2
    try:
        return handlers[argv[1]](_strict_json(argv[2]))
    except (PilotRefusal, ValueError, TypeError):
        return 2


if __name__ == "__main__":
    raise SystemExit(_child_main(sys.argv))
