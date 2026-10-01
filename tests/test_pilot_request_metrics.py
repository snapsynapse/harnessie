"""Content-free request sizing and pre-dispatch admission contracts."""
from __future__ import annotations

import json

import pytest

from harness.models.base import Message, ToolCall
from scripts.pilot_contract import PilotRefusal
from scripts.pilot_request_metrics import (PreparedPilotRequest, RequestMetricsStore,
                                           read_request_metrics)


def messages():
    return [
        Message("system", "rules"),
        Message("assistant", "", [ToolCall("one", "read_file", {"path": "evidence/a.md"})]),
        Message("tool", "SECRET-CANARY", tool_call_id="one", name="read_file"),
    ]


def test_records_exact_identity_sizes_and_no_content(tmp_path):
    path = (tmp_path / "request-metrics.jsonl").resolve()
    store = RequestMetricsStore(path)
    request = b'{"encoded":"request"}'
    row = store.record(stage="claude:position", participant="claude",
                       prepared=PreparedPilotRequest(request, "claude-code-max-pilot",
                                                    "claude_code_stdin_neutral_json"),
                       messages=messages(), tools=[{"name": "read_file"}],
                       max_input_bytes=1000, max_evidence_bytes=1000)
    store.close()
    assert row["request_bytes"] == len(request)
    assert row["headroom_bytes"] == 1000 - len(request)
    assert row["tool_results"] == [{"message_index": 2, "content_utf8_bytes": 13,
                                    "serialized_bytes": row["messages"][2]["serialized_bytes"]}]
    raw = path.read_text()
    assert "SECRET-CANARY" not in raw and "evidence/a.md" not in raw
    assert read_request_metrics(path)["records"] == 1


def test_oversize_is_durably_recorded_then_refused(tmp_path):
    path = (tmp_path / "request-metrics.jsonl").resolve()
    store = RequestMetricsStore(path)
    with pytest.raises(PilotRefusal, match="input_limit_exceeded"):
        store.record(stage="qwen:position", participant="qwen",
                     prepared=PreparedPilotRequest(b"12345", "openai-compat-local-pilot",
                                                   "openai_chat_completions_json", 1),
                     messages=[Message("user", "x")], tools=[],
                     max_input_bytes=4, max_evidence_bytes=4)
    store.close()
    row = json.loads(path.read_text())
    assert row["data"]["admitted"] is False and row["data"]["headroom_bytes"] == -1
    assert read_request_metrics(path) == {"integrity": "valid", "records": 1, "admitted": 0,
                                          "tail_hash": row["hash"]}


def test_invalid_stage_and_evidence_ceiling_refuse(tmp_path):
    store = RequestMetricsStore((tmp_path / "request-metrics.jsonl").resolve())
    args = dict(stage="claude:position", participant="claude",
                prepared=PreparedPilotRequest(b"{}", "claude", "neutral"),
                messages=[Message("user", "x")], tools=[], max_input_bytes=10,
                max_evidence_bytes=10)
    store.record(**args)
    with pytest.raises(PilotRefusal, match="request_metrics_invalid"):
        store.record(**{**args, "stage": "qwen:position"})
    with pytest.raises(PilotRefusal, match="evidence_limit_exceeded"):
        store.record(**{**args, "stage": "claude:objection",
                        "messages": [Message("tool", "123", name="read_file")],
                        "max_evidence_bytes": 2})
    store.close()


def test_tampering_is_detected(tmp_path):
    path = (tmp_path / "request-metrics.jsonl").resolve()
    store = RequestMetricsStore(path)
    store.record(stage="claude:position", participant="claude",
                 prepared=PreparedPilotRequest(b"{}", "claude", "neutral"),
                 messages=[Message("user", "x")], tools=[], max_input_bytes=10,
                 max_evidence_bytes=10)
    store.close()
    path.write_text(path.read_text().replace('"request_bytes":2', '"request_bytes":3'))
    with pytest.raises(PilotRefusal, match="request_metrics_integrity_invalid"):
        read_request_metrics(path)


def test_malformed_message_refuses_without_leaking_an_attribute_error(tmp_path):
    store = RequestMetricsStore((tmp_path / "request-metrics.jsonl").resolve())
    invalid = Message("tool", "x")
    invalid.content = None
    with pytest.raises(PilotRefusal, match="request_metrics_invalid"):
        store.record(stage="claude:position", participant="claude",
                     prepared=PreparedPilotRequest(b"{}", "claude", "neutral"),
                     messages=[invalid], tools=[], max_input_bytes=10, max_evidence_bytes=10)
    store.close()
