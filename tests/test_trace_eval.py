import json

import pytest

from harness.trace_eval import analyze_trace, load_events


def test_trace_metrics_cover_parallel_denials_steps_tokens_and_claims() -> None:
    events = [
        {"kind": "model_turn", "step": 1, "tokens": 120,
         "tool_calls": ["run_shell", "run_shell", "run_shell"]},
        {"kind": "tool_result", "tool": "run_shell", "ok": True},
        {"kind": "refusal", "tool": "run_shell"},
        {"kind": "tool_result", "tool": "run_shell", "ok": True},
        {"kind": "refusal", "tool": "run_shell"},
        {"kind": "tool_result", "tool": "run_shell", "ok": True},
        {"kind": "refusal", "tool": "run_shell"},
        {"kind": "claim_finding", "claim_id": "claim-1", "status": "refuted"},
        {"kind": "model_turn", "step": 2, "tokens": 30,
         "tool_calls": ["task_complete"]},
        {"kind": "tool_result", "tool": "task_complete", "ok": True},
        {"kind": "loop_finished", "stop": "complete", "steps": 2},
    ]

    metrics = analyze_trace(events, claim_ids=["claim-1", "claim-2"])

    assert metrics == {
        "model_turns": 2,
        "steps": 2,
        "tokens": 150,
        "tool_results": 4,
        "refusals": 3,
        "refusals_by_error": {"unknown": 3},
        "tool_contract_breaks": 0,
        "denial_rate": 0.75,
        "completed_tasks": 1,
        "tool_calls_per_completed_task": 4.0,
        "duplicate_tool_calls": 2,
        "turns_with_duplicate_calls": 1,
        "claim_count": 2,
        "covered_claims": ["claim-1"],
        "uncovered_claims": ["claim-2"],
        "claim_coverage_rate": 0.5,
    }


def test_tool_contract_breaks_count_vocabulary_refusals_only() -> None:
    events = [
        {"kind": "model_turn", "step": 1, "tokens": 10, "tool_calls": ["bash"]},
        {"kind": "tool_result", "tool": "bash", "ok": False},
        {"kind": "refusal", "tool": "bash", "error": "action_unsupported"},
        {"kind": "model_turn", "step": 2, "tokens": 10, "tool_calls": ["list_files"]},
        {"kind": "tool_result", "tool": "list_files", "ok": False},
        {"kind": "refusal", "tool": "list_files", "error": "malformed_arguments"},
        {"kind": "model_turn", "step": 3, "tokens": 10, "tool_calls": ["write_file"]},
        {"kind": "tool_result", "tool": "write_file", "ok": False},
        {"kind": "refusal", "tool": "write_file", "error": "consent_required"},
        {"kind": "model_turn", "step": 4, "tokens": 10, "tool_calls": ["read_file"]},
        {"kind": "tool_result", "tool": "read_file", "ok": False},
        {"kind": "refusal", "tool": "read_file", "error": "bad_arguments"},
        {"kind": "model_turn", "step": 5, "tokens": 10,
         "tool_calls": ["task_complete"]},
        {"kind": "tool_result", "tool": "task_complete", "ok": True},
        {"kind": "loop_finished", "stop": "complete", "steps": 5},
    ]

    metrics = analyze_trace(events)

    assert metrics["refusals"] == 4
    assert metrics["refusals_by_error"] == {
        "action_unsupported": 1, "bad_arguments": 1,
        "consent_required": 1, "malformed_arguments": 1}
    # The consent refusal is policy, not a vocabulary mismatch.
    assert metrics["tool_contract_breaks"] == 3
    assert metrics["completed_tasks"] == 1
    assert metrics["tool_calls_per_completed_task"] == 5.0


def test_tool_calls_per_completed_task_is_none_without_a_completed_loop() -> None:
    metrics = analyze_trace([
        {"kind": "model_turn", "step": 1, "tokens": 5, "tool_calls": ["bash"]},
        {"kind": "tool_result", "tool": "bash", "ok": False},
        {"kind": "refusal", "tool": "bash", "error": "action_unsupported"},
        {"kind": "loop_finished", "stop": "stuck", "steps": 1},
    ])

    assert metrics["completed_tasks"] == 0
    assert metrics["tool_calls_per_completed_task"] is None
    assert metrics["tool_contract_breaks"] == 1


def test_trace_metrics_fail_closed_on_malformed_counters_and_dedupe_claims() -> None:
    metrics = analyze_trace(
        [
            {"kind": "model_turn", "step": "bad", "tokens": -5,
             "tool_calls": "not-a-list"},
            {"kind": "claim_evidence", "claim_id": "a"},
        ],
        claim_ids=["a", "a"],
    )

    assert metrics["steps"] == 0
    assert metrics["tokens"] == 0
    assert metrics["claim_count"] == 1
    assert metrics["claim_coverage_rate"] == 1.0


def test_load_events_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"kind": "model_turn"}) + "\n[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_events(path)
