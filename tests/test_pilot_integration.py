"""Offline injected-transport integration of the guarded live-panel seam."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import socket
from unittest.mock import patch

import pytest

from harness.models.base import ModelSpec
from scripts.pilot_claude_code import AUTH_CLASS, ClaudeCodePilot, _RunResult
from scripts.pilot_contract import (CLAUDE_MODEL, QWEN_MODEL, CallAllowance,
                                    PilotLimits, digest_json)
from scripts.pilot_execution import proposal
from scripts.pilot_live import _run_panel
from scripts.pilot_policy import CLAUDE_MAX_HAIKU_CONTEXT, HAIKU_MODEL
from scripts.pilot_prepare import capture_packet_identity, prepare_packet
from scripts.pilot_qwen import QwenPilot


REPO = Path(__file__).resolve().parents[1]


def _fetch(method, path, payload=None):
    del payload
    digest = "a" * 64
    if path == "/api/version":
        return {"version": "offline"}
    if path == "/api/tags":
        return {"models": [{"name": QWEN_MODEL, "digest": digest, "size": 1}]}
    assert (method, path) == ("POST", "/api/show")
    return {"details": {}, "model_info": {}, "capabilities": [],
            "modelfile": "FROM sha256-" + "b" * 64}


def _envelope(participant: str, call: int) -> dict:
    if call % 2:
        return {"content": "", "tool_calls": [{"id": f"{participant}-{call}", "name": "read_file",
                "arguments": {"path": "evidence-index.json"}}], "stop_reason": "tool_use"}
    if call == 2:
        report = {"stance": "recommend" if participant == "claude" else "oppose",
                  "summary": f"{participant} injected transport position."}
    else:
        report = {"objections": [] if participant == "claude" else ["qwen injected objection"],
                  "no_new_objection": participant == "claude"}
    return {"content": "", "tool_calls": [{"id": f"{participant}-{call}", "name": "task_complete",
            "arguments": {"report": json.dumps(report)}}], "stop_reason": "tool_use"}


def _claude_stream(envelope: dict, *, extra_model: bool = False) -> bytes:
    usage = {
        CLAUDE_MODEL: {"inputTokens": 2, "outputTokens": 3, "cacheCreationInputTokens": 0,
                       "cacheReadInputTokens": 0, "provider": "firstParty"},
        HAIKU_MODEL: {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0,
                      "cacheReadInputTokens": 0, "provider": "firstParty", "webSearchRequests": 0},
    }
    if extra_model:
        usage["unexpected-model"] = {"inputTokens": 1, "outputTokens": 1,
                                       "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}
    session, tool = "offline-session", "structured-1"
    events = [
        {"type": "system", "subtype": "init", "session_id": session, "tools": ["StructuredOutput"],
         "mcp_servers": [], "model": CLAUDE_MODEL},
        {"type": "assistant", "session_id": session, "parent_tool_use_id": None, "request_id": "offline-request",
         "message": {"role": "assistant", "model": CLAUDE_MODEL, "id": "offline-message", "content": [
             {"type": "tool_use", "id": tool, "name": "StructuredOutput", "input": envelope}]}},
        {"type": "user", "session_id": session, "parent_tool_use_id": None,
         "tool_use_result": "Structured output provided successfully", "message": {"content": [
             {"type": "tool_result", "tool_use_id": tool, "content": "Structured output provided successfully"}]}},
        {"type": "result", "session_id": session, "is_error": False, "subtype": "success",
         "terminal_reason": "completed", "modelUsage": usage, "structured_output": envelope,
         "result": json.dumps(envelope)},
    ]
    return ("\n".join(json.dumps(event) for event in events) + "\n").encode()


class _InjectedClaude(ClaudeCodePilot):
    def __init__(self, executable: Path, cwd: Path, *, extra_model: bool = False,
                 process_limits: dict | None = None):
        super().__init__(ModelSpec("frontier", "claude-code-max-pilot", CLAUDE_MODEL), executable, cwd,
                         CallAllowance(PilotLimits(max_calls=8, **(process_limits or {}))),
                         policy=CLAUDE_MAX_HAIKU_CONTEXT)
        self.calls = 0
        self.extra_model = extra_model

    def _run(self, argv, stdin):
        if argv[1:] == ["auth", "status", "--json"]:
            return _RunResult(json.dumps({"loggedIn": True, "authMethod": "claude.ai",
                                           "subscriptionType": "max", "apiProvider": "firstParty"}).encode(), 0, None)
        self.calls += 1
        return _RunResult(_claude_stream(_envelope("claude", self.calls), extra_model=self.extra_model), 0, None)


def _qwen_payload(envelope: dict) -> bytes:
    return json.dumps({"model": QWEN_MODEL, "choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps(envelope)}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3,
        "total_tokens": 5}}).encode()


def _prepared(root: Path):
    packet = prepare_packet(REPO, root, live_candidate=True)
    execution = proposal(root, packet["manifest_sha256"], "pilot-injected-integration")
    assert execution["limits"]["calls"] == {"claude": 8, "qwen": 8}
    identity = capture_packet_identity(root, packet["manifest_sha256"], client_version="offline", fetch_json=_fetch)["identity"]
    return execution, identity


def _factories(root: Path, identity: dict, executable: Path, *, drift=False, extra_model=False,
               process_limits: dict | None = None):
    qwen_calls = {"count": 0}
    def capture():
        qwen_calls["count"] += 1
        value = copy.deepcopy(identity)
        if drift and qwen_calls["count"] == 2:
            value["server_version"] = "drift"
            value["fingerprint"] = digest_json({key: value[key] for key in (
                "receipt_version", "client_version", "ollama_base_url", "server_version", "model", "harness_identity")})
        return value
    qwen_turns = {"count": 0}
    def qwen_transport(_request, _limits):
        qwen_turns["count"] += 1
        return _qwen_payload(_envelope("qwen", qwen_turns["count"]))
    return {
        "claude": lambda: _InjectedClaude(executable, root, extra_model=extra_model,
                                            process_limits=process_limits),
        "qwen": lambda: QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, "http://127.0.0.1:11434/v1"),
                                    identity, capture,
                                    CallAllowance(PilotLimits(max_calls=8, **(process_limits or {}))),
                                    qwen_transport),
    }


def _forbidden(*_args, **_kwargs):
    raise AssertionError("external provider/process/network use is forbidden")


def test_injected_real_adapters_complete_four_stages_and_halt_for_human_arbitration(tmp_path):
    root = tmp_path / "packet"
    execution, identity = _prepared(root)
    executable = tmp_path / "fake-claude"; executable.write_text("offline")
    executable.chmod(0o700)
    with patch("socket.socket.connect", _forbidden), patch("socket.create_connection", _forbidden), \
            patch("scripts.pilot_live.forbidden", _forbidden), \
            patch("scripts.pilot_live._export", lambda *_args: "offline-export.md"):
        result = _run_panel(root, execution, _factories(root, identity, executable), offline=True)
    assert result["status"] == "needs_arbitration", result
    assert result["ledger"]["calls"] == {"claude": 4, "qwen": 4}
    assert result["request_metrics"]["integrity"] == "valid"
    assert result["request_metrics"]["records"] == 8
    assert result["request_metrics"]["admitted"] == 8
    assert result["ledger"]["accounting_complete"] and result["ledger"]["usage"]["input_tokens"] == 20
    rows = [json.loads(line) for line in (root / "runs" / execution["run_id"] / "operator" / "ledger.jsonl").read_text().splitlines()]
    receipts = [row["data"]["receipt"] for row in rows if row.get("kind") == "receipt"]
    models = {next(iter(receipt["model_usage"])) for receipt in receipts}
    assert models == {CLAUDE_MODEL, QWEN_MODEL}
    assert all("SCRIPTED-" not in model for model in models)
    assert all(receipt["dollar_cost"] is None for receipt in receipts)
    claude_receipt = next(receipt for receipt in receipts if CLAUDE_MODEL in receipt["model_usage"])
    assert claude_receipt["policy_id"] == CLAUDE_MAX_HAIKU_CONTEXT.id
    assert set(claude_receipt["reported_model_usages"][0]) == {CLAUDE_MODEL, HAIKU_MODEL}
    metrics_path = root / "runs" / execution["run_id"] / "operator" / "request-metrics.jsonl"
    metrics = [json.loads(line)["data"] for line in metrics_path.read_text().splitlines()]
    assert [row["stage"] for row in metrics] == [
        "claude:position", "claude:position", "qwen:position", "qwen:position",
        "claude:objection", "claude:objection", "qwen:objection", "qwen:objection",
    ]
    assert [row["participant"] for row in metrics] == [
        "claude", "claude", "qwen", "qwen", "claude", "claude", "qwen", "qwen",
    ]
    assert all(metrics[index + 1]["request_bytes"] > metrics[index]["request_bytes"]
               for index in (0, 2, 4, 6))
    assert all(row["encoding_overhead_bytes"] is None for row in metrics if row["participant"] == "claude")
    assert all(row["encoding_overhead_bytes"] > 0 for row in metrics if row["participant"] == "qwen")
    raw_metrics = metrics_path.read_text()
    assert "evidence-index.json" not in raw_metrics and "injected transport position" not in raw_metrics


def test_evidence_admission_refuses_before_second_transport_and_before_qwen(tmp_path):
    root = tmp_path / "packet"
    execution, identity = _prepared(root)
    execution["process_limits"]["max_evidence_bytes"] = 1
    executable = tmp_path / "fake-claude"; executable.write_text("offline")
    executable.chmod(0o700)
    factories = _factories(root, identity, executable,
                           process_limits=execution["process_limits"])
    claude = factories["claude"]()
    qwen = factories["qwen"]()
    with patch("socket.socket.connect", _forbidden), patch("socket.create_connection", _forbidden), \
            patch("scripts.pilot_live.forbidden", _forbidden), \
            patch("scripts.pilot_live._export", _forbidden):
        result = _run_panel(root, execution, {"claude": lambda: claude, "qwen": lambda: qwen}, offline=True)
    assert result["status"] == "incomplete"
    assert claude.calls == 1 and qwen.allowance.used == 0
    assert result["ledger"]["calls"] == {"claude": 1, "qwen": 0}
    assert result["request_metrics"] == {
        "integrity": "valid", "records": 2, "admitted": 1,
        "tail_hash": result["request_metrics"]["tail_hash"],
    }
    rows = [json.loads(line)["data"] for line in
            (root / "runs" / execution["run_id"] / "operator" / "request-metrics.jsonl").read_text().splitlines()]
    assert rows[0]["admitted"] is True and rows[1]["admitted"] is False
    assert rows[1]["evidence_bytes"] > rows[1]["max_evidence_bytes"]


@pytest.mark.parametrize("failure", ["qwen_after_identity_drift"])
def test_refused_adapter_receipt_stops_later_stage_and_preserves_usage(tmp_path, failure):
    assert failure == "qwen_after_identity_drift"
    root = tmp_path / "packet"
    execution, identity = _prepared(root)
    executable = tmp_path / "fake-claude"; executable.write_text("offline")
    executable.chmod(0o700)
    with patch("socket.socket.connect", _forbidden), patch("socket.create_connection", _forbidden), \
            patch("scripts.pilot_live.forbidden", _forbidden), \
            patch("scripts.pilot_live._export", _forbidden):
        result = _run_panel(root, execution, _factories(root, identity, executable, drift=True), offline=True)
    assert result["status"] == "incomplete"
    assert result["ledger"]["calls"] == {"claude": 2, "qwen": 1}
    assert result["ledger"]["known_usage"]["input_tokens"] == 8
    assert result["ledger"]["halted"] and result["ledger"]["accounting_complete"]
