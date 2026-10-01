"""Measure the complete four-stage pilot workload without provider inference."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

from harness.models.base import ModelSpec
from scripts.pilot_claude_code import AUTH_CLASS, ClaudeCodePilot, _RunResult
from scripts.pilot_contract import (CLAUDE_MODEL, QWEN_MODEL, CallAllowance,
                                    PilotLimits, PilotRefusal, digest_json)
from scripts.pilot_execution import proposal
from scripts.pilot_live import _run_panel
from scripts.pilot_policy import (CLAUDE_MAX_HAIKU_CONTEXT, HAIKU_CONTEXT_POLICY_ID,
                                  HAIKU_MODEL)
from scripts.pilot_prepare import capture_packet_identity, prepare_packet
from scripts.pilot_qwen import QwenPilot


ACTUAL_V3_READS = (
    "evidence/INTENT.md",
    "evidence/decisions/AIDR-0009-bid-rounds-and-run-observer.md",
    "evidence/decisions/AIDR-0009-design-draft.md",
    "evidence/harness/routing.py",
    "evidence/harness/loop.py",
    "evidence/evals/pending/bidding.yaml",
    "evidence/tests/test_bidding.py",
)
WORST_CASE_ADDITIONAL_READS = (
    "evidence/audits/aidr-0009-preparation-2026-09-04.md",
    "evidence/audits/aidr-0009-readiness-review-antigravity-2026-09-04.md",
    "evidence/audits/aidr-0009-readiness-review-claude-code-2026-09-04.md",
    "evidence/audits/aidr-0009-readiness-review-codex-2026-09-04.md",
    "evidence/audits/aidr-0009-readiness-review-qwen3-8-2026-09-04.md",
    "evidence/audits/capability-program-readiness-2026-09-09.md",
    "evidence/harness/adversarial.py",
    "evidence/harness/boundary.py",
    "evidence/harness/cascade.py",
    "evidence/harness/models/base.py",
)
SYNTHETIC_HAIKU_INPUT_PROFILE = (1_750, 3_372, 33_729, 65_000,
                                 1_750, 3_372, 33_729, 65_000)
SYNTHETIC_HAIKU_OUTPUT_TOKENS = 18


def _envelope(participant: str, call: int) -> dict:
    step = ((call - 1) % 4) + 1
    stage = (call - 1) // 4
    if step == 1:
        paths = ("evidence-index.json",)
    elif step == 2:
        paths = ACTUAL_V3_READS
    elif step == 3:
        paths = WORST_CASE_ADDITIONAL_READS
    else:
        if stage == 0:
            report = {"stance": "recommend" if participant == "claude" else "oppose",
                      "summary": "SYNTHETIC workload-sizing position, not a model opinion."}
        else:
            report = {"objections": ([] if participant == "claude" else
                                      ["SYNTHETIC workload-sizing objection."]),
                      "no_new_objection": participant == "claude"}
        return {"content": "", "tool_calls": [{"id": f"{participant}-{call}-done",
                "name": "task_complete", "arguments": {"report": json.dumps(report)}}],
                "stop_reason": "tool_use"}
    return {"content": "", "tool_calls": [
        {"id": f"{participant}-{call}-{index}", "name": "read_file", "arguments": {"path": name}}
        for index, name in enumerate(paths)], "stop_reason": "tool_use"}


def _claude_stream(envelope: dict, haiku_input_tokens: int) -> bytes:
    usage = {
        CLAUDE_MODEL: {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0,
                       "cacheReadInputTokens": 0, "provider": "firstParty"},
        HAIKU_MODEL: {"inputTokens": haiku_input_tokens,
                      "outputTokens": SYNTHETIC_HAIKU_OUTPUT_TOKENS,
                      "cacheCreationInputTokens": 0,
                      "cacheReadInputTokens": 0, "provider": "firstParty", "webSearchRequests": 0},
    }
    session, tool = "offline-workload-sizing", "structured-output"
    events = [
        {"type": "system", "subtype": "init", "session_id": session,
         "tools": ["StructuredOutput"], "mcp_servers": [], "model": CLAUDE_MODEL},
        {"type": "assistant", "session_id": session, "parent_tool_use_id": None,
         "request_id": "offline-workload-sizing", "message": {"role": "assistant",
         "model": CLAUDE_MODEL, "id": "offline-message", "content": [{"type": "tool_use",
         "id": tool, "name": "StructuredOutput", "input": envelope}]}},
        {"type": "user", "session_id": session, "parent_tool_use_id": None,
         "tool_use_result": "Structured output provided successfully", "message": {"content": [
         {"type": "tool_result", "tool_use_id": tool,
          "content": "Structured output provided successfully"}]}},
        {"type": "result", "session_id": session, "is_error": False, "subtype": "success",
         "terminal_reason": "completed", "modelUsage": usage, "structured_output": envelope,
         "result": json.dumps(envelope)},
    ]
    return ("\n".join(json.dumps(event) for event in events) + "\n").encode()


def _qwen_response(envelope: dict) -> bytes:
    return json.dumps({"model": QWEN_MODEL, "choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps(envelope)}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1,
        "total_tokens": 2}}, separators=(",", ":")).encode()


class OfflineClaudeWorkload(ClaudeCodePilot):
    def __init__(self, executable: Path, cwd: Path, limits: PilotLimits):
        super().__init__(ModelSpec("frontier", "claude-code-max-pilot", CLAUDE_MODEL),
                         executable, cwd, CallAllowance(limits),
                         policy=CLAUDE_MAX_HAIKU_CONTEXT)
        self.calls = 0

    def _run(self, argv, stdin):
        if argv[1:] == ["auth", "status", "--json"]:
            return _RunResult(json.dumps({"loggedIn": True, "authMethod": "oauth_token",
                "apiProvider": "firstParty"}).encode(), 0, None)
        self.calls += 1
        return _RunResult(_claude_stream(
            _envelope("claude", self.calls),
            SYNTHETIC_HAIKU_INPUT_PROFILE[self.calls - 1],
        ), 0, None)


def _identity_fetch(method, endpoint, payload=None):
    del payload
    if endpoint == "/api/version":
        return {"version": "offline-workload-sizing"}
    if endpoint == "/api/tags":
        return {"models": [{"name": QWEN_MODEL, "digest": "a" * 64, "size": 1}]}
    if (method, endpoint) == ("POST", "/api/show"):
        return {"details": {}, "model_info": {}, "capabilities": [],
                "modelfile": "FROM sha256-" + "b" * 64}
    raise PilotRefusal("offline_identity_fixture_invalid")


def _forbidden(*_args, **_kwargs):
    raise PilotRefusal("network_forbidden")


def measure_full_workload(repo: Path, destination: Path,
                          run_id: str = "pilot-offline-workload-sizing") -> dict:
    repo, destination = repo.resolve(), destination.resolve()
    packet = prepare_packet(repo, destination, live_candidate=True)
    execution = proposal(destination, packet["manifest_sha256"], run_id)
    identity = capture_packet_identity(destination, packet["manifest_sha256"],
                                       client_version="offline-workload-sizing",
                                       fetch_json=_identity_fetch)["identity"]
    limits = PilotLimits(max_calls=8, **execution["process_limits"])
    qwen_state = {"calls": 0}

    def qwen_identity():
        return copy.deepcopy(identity)

    def qwen_transport(_request, _limits):
        qwen_state["calls"] += 1
        return _qwen_response(_envelope("qwen", qwen_state["calls"]))

    claude = OfflineClaudeWorkload(Path(sys.executable).resolve(), destination, limits)
    qwen = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL,
                              base_url="http://127.0.0.1:11434/v1"),
                     identity, qwen_identity, CallAllowance(limits), qwen_transport)
    with patch("socket.socket.connect", _forbidden), patch("socket.create_connection", _forbidden):
        result = _run_panel(destination, execution,
                            {"claude": lambda: claude, "qwen": lambda: qwen}, offline=True)
    metrics_path = destination / execution["outputs"]["request_metrics"]
    rows = [json.loads(line)["data"] for line in metrics_path.read_text().splitlines()]
    by_stage = {}
    for row in rows:
        summary = by_stage.setdefault(row["stage"], {"requests": 0, "max_request_bytes": 0,
                                                      "max_evidence_bytes": 0,
                                                      "minimum_input_headroom_bytes": None,
                                                      "minimum_evidence_headroom_bytes": None})
        summary["requests"] += 1
        summary["max_request_bytes"] = max(summary["max_request_bytes"], row["request_bytes"])
        summary["max_evidence_bytes"] = max(summary["max_evidence_bytes"], row["evidence_bytes"])
        for source, target in (("headroom_bytes", "minimum_input_headroom_bytes"),
                               ("evidence_headroom_bytes", "minimum_evidence_headroom_bytes")):
            summary[target] = (row[source] if summary[target] is None
                               else min(summary[target], row[source]))
    report = {
        "schema": "harnessie-pilot-workload-sizing/1",
        "mode": "offline_synthetic_transport_full_evidence",
        "status": result["status"],
        "live_model_calls": 0,
        "synthetic_transport_calls": {"claude": claude.calls, "qwen": qwen_state["calls"]},
        "policy_id": HAIKU_CONTEXT_POLICY_ID,
        "execution_limits": execution["limits"],
        "synthetic_haiku_input_tokens": sum(SYNTHETIC_HAIKU_INPUT_PROFILE),
        "synthetic_haiku_usage": {
            "classification": "synthetic_fixture_not_provider_evidence",
            "input_tokens_by_call": list(SYNTHETIC_HAIKU_INPUT_PROFILE),
            "output_tokens_per_call": SYNTHETIC_HAIKU_OUTPUT_TOKENS,
            "output_tokens_total": SYNTHETIC_HAIKU_OUTPUT_TOKENS * len(
                SYNTHETIC_HAIKU_INPUT_PROFILE),
        },
        "actual_v3_read_set": list(ACTUAL_V3_READS),
        "worst_case_additional_read_set": list(WORST_CASE_ADDITIONAL_READS),
        "all_declared_evidence_read_each_stage": True,
        "process_limits": execution["process_limits"],
        "request_metrics": result.get("request_metrics"),
        "stages": by_stage,
        "all_requests_admitted": bool(rows) and all(row["admitted"] is True for row in rows),
        "byte_envelope_result": ("fits_candidate_process_limits" if rows and all(
            row["admitted"] is True for row in rows) else "does_not_fit_candidate_process_limits"),
        "token_limit_result": "not_inferred_from_bytes",
        "existing_live_evidence": {"neutral_request_bytes_before_v3_stop": 113_699,
                                   "reported_haiku_input_tokens": 33_729,
                                   "approved_haiku_input_tokens_per_run": 32_768,
                                   "conclusion": "full-evidence live review does not fit the existing Haiku cap"},
        "next_live_allowance": {"claude": 0, "qwen": 0},
        "limitations": ["synthetic responses do not establish review quality",
                        "synthetic Haiku token counts are fixtures, not provider evidence",
                        "bytes do not establish provider token counts",
                        "no provider, account, model or service was contacted"],
    }
    output = destination / "runs" / run_id / "operator" / "workload-sizing.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    report["report_path"] = str(output)
    report["report_canonical_json_sha256"] = digest_json(json.loads(output.read_text()))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run-id", default="pilot-offline-workload-sizing")
    args = parser.parse_args()
    try:
        report = measure_full_workload(args.repo, args.destination, args.run_id)
    except PilotRefusal as exc:
        print(json.dumps({"status": "refused", "code": exc.code}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "needs_arbitration" and report["all_requests_admitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
