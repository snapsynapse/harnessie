"""Content-free, durable request measurements for the local pilot.

The journal is written before a transport may run. It records exact encoded
request identity and component sizes without retaining prompt or tool-result
content. A metrics failure is an admission failure, never a reason to dispatch
without evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from dataclasses import dataclass

from harness.models.base import Message
from scripts.pilot_contract import PilotRefusal


SCHEMA = "harnessie-pilot-request-metrics/1"
STAGES = ("claude:position", "qwen:position", "claude:objection", "qwen:objection")


@dataclass(frozen=True)
class PreparedPilotRequest:
    """Exact immutable bytes that admission measures and transport consumes."""

    request: bytes
    transport: str
    encoding: str
    inner_prompt_bytes: int | None = None


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _message_metrics(messages: list[Message]) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    tool_results: list[dict] = []
    for index, message in enumerate(messages):
        if (type(message) is not Message or message.role not in {"system", "user", "assistant", "tool"}
                or not isinstance(message.content, str) or not isinstance(message.tool_calls, list)
                or not isinstance(message.tool_call_id, str) or not isinstance(message.name, str)):
            raise PilotRefusal("request_metrics_invalid")
        calls = []
        for call in message.tool_calls:
            if (not isinstance(call.id, str) or not isinstance(call.name, str)
                    or not isinstance(call.arguments, dict)):
                raise PilotRefusal("request_metrics_invalid")
            calls.append({"id": call.id, "name": call.name, "arguments": call.arguments})
        wire = {"role": message.role, "content": message.content, "tool_calls": calls,
                "tool_call_id": message.tool_call_id, "name": message.name}
        row = {
            "index": index,
            "role": message.role,
            "content_utf8_bytes": len(message.content.encode("utf-8")),
            "serialized_bytes": len(_canonical(wire)),
            "tool_calls": len(calls),
            "tool_calls_serialized_bytes": len(_canonical(calls)),
        }
        rows.append(row)
        if message.role == "tool":
            tool_results.append({"message_index": index,
                                 "content_utf8_bytes": row["content_utf8_bytes"],
                                 "serialized_bytes": row["serialized_bytes"]})
    return rows, tool_results


class RequestMetricsStore:
    """Create one non-resumable, append-only request measurement journal."""

    def __init__(self, path: Path) -> None:
        if (not isinstance(path, Path) or not path.is_absolute() or path.name in {"", ".", ".."}
                or path.exists() or path.is_symlink() or not path.parent.is_dir()
                or path.parent.is_symlink()):
            raise PilotRefusal("request_metrics_path_invalid")
        ancestor = path.parent
        while ancestor != ancestor.parent:
            if ancestor.is_symlink():
                raise PilotRefusal("request_metrics_path_invalid")
            ancestor = ancestor.parent
        self.path = path
        self._fd: int | None = None
        self._sequence = 0
        self._previous_hash = ""
        self._open()

    def _open(self) -> None:
        try:
            self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND, 0o600)
            parent_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as exc:
            self._fd = None
            raise PilotRefusal("request_metrics_io_failure") from exc

    def record(self, *, stage: str, participant: str, prepared: PreparedPilotRequest,
               messages: list[Message], tools: list[dict], max_input_bytes: int,
               max_evidence_bytes: int) -> dict:
        try:
            if (self._fd is None or stage not in STAGES
                    or participant not in {"claude", "qwen"}
                    or not stage.startswith(participant + ":")
                    or type(prepared) is not PreparedPilotRequest
                    or not isinstance(prepared.transport, str) or not prepared.transport
                    or not isinstance(prepared.encoding, str) or not prepared.encoding
                    or not isinstance(prepared.request, bytes)
                    or type(max_input_bytes) is not int or max_input_bytes <= 0
                    or type(max_evidence_bytes) is not int or max_evidence_bytes <= 0
                    or type(tools) is not list
                    or (prepared.inner_prompt_bytes is not None
                        and (type(prepared.inner_prompt_bytes) is not int
                             or prepared.inner_prompt_bytes < 0))):
                raise PilotRefusal("request_metrics_invalid")
            message_rows, tool_results = _message_metrics(messages)
            request_bytes = len(prepared.request)
            evidence_bytes = sum(row["content_utf8_bytes"] for row in tool_results)
            input_admitted = request_bytes <= max_input_bytes
            evidence_admitted = evidence_bytes <= max_evidence_bytes
            admitted = input_admitted and evidence_admitted
            data = {
                "schema": SCHEMA,
                "request_id": f"request-{self._sequence + 1:04d}",
                "stage": stage,
                "participant": participant,
                "transport": prepared.transport,
                "encoding": prepared.encoding,
                "request_bytes": request_bytes,
                "request_sha256": hashlib.sha256(prepared.request).hexdigest(),
                "max_input_bytes": max_input_bytes,
                "headroom_bytes": max_input_bytes - request_bytes,
                "evidence_bytes": evidence_bytes,
                "max_evidence_bytes": max_evidence_bytes,
                "evidence_headroom_bytes": max_evidence_bytes - evidence_bytes,
                "admitted": admitted,
                "messages": message_rows,
                "tool_results": tool_results,
                "tools_count": len(tools),
                "tools_serialized_bytes": len(_canonical(tools)),
                "inner_prompt_bytes": prepared.inner_prompt_bytes,
                "encoding_overhead_bytes": (None if prepared.inner_prompt_bytes is None
                                             else request_bytes - prepared.inner_prompt_bytes),
            }
            payload = {"sequence": self._sequence + 1, "data": data,
                       "previous_hash": self._previous_hash}
            digest = _digest(payload)
            encoded = _canonical({**payload, "hash": digest}) + b"\n"
            if os.write(self._fd, encoded) != len(encoded):
                raise OSError("partial request metrics write")
            os.fsync(self._fd)
            self._sequence += 1
            self._previous_hash = digest
            if not input_admitted:
                raise PilotRefusal("input_limit_exceeded")
            if not evidence_admitted:
                raise PilotRefusal("evidence_limit_exceeded")
            return data
        except PilotRefusal:
            raise
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            raise PilotRefusal("request_metrics_io_failure") from exc

    def close(self) -> None:
        if self._fd is None:
            return
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
            raise PilotRefusal("request_metrics_io_failure") from failure


def read_request_metrics(path: Path) -> dict:
    """Verify a closed journal without exposing any request content."""
    try:
        lines = path.read_bytes().splitlines()
    except OSError as exc:
        raise PilotRefusal("request_metrics_read_failed") from exc
    previous = ""
    admitted = 0
    for index, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
            if (type(row) is not dict or set(row) != {"sequence", "data", "previous_hash", "hash"}
                    or row["sequence"] != index or row["previous_hash"] != previous
                    or type(row["data"]) is not dict or row["data"].get("schema") != SCHEMA):
                raise ValueError
            payload = {key: row[key] for key in ("sequence", "data", "previous_hash")}
            if row["hash"] != _digest(payload):
                raise ValueError
            previous = row["hash"]
            admitted += int(row["data"].get("admitted") is True)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError,
                RecursionError, OverflowError) as exc:
            raise PilotRefusal("request_metrics_integrity_invalid") from exc
    if not lines:
        raise PilotRefusal("request_metrics_integrity_invalid")
    return {"integrity": "valid", "records": len(lines), "admitted": admitted,
            "tail_hash": previous}
