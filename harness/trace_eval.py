"""Deterministic efficiency and coverage metrics for Harnessie event traces.

The analyzer is intentionally policy-free: it reduces already-recorded events
to stable counts that scorecards can compare. It neither repairs malformed
traces nor treats missing claim evidence as success.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CLAIM_EVIDENCE_KINDS = frozenset({"claim_evidence", "claim_finding", "claim_verdict"})

# Refusals that mean the brain spoke a tool vocabulary this harness does not
# have: an unknown tool name, arguments that were not JSON, or arguments that
# did not fit the schema. Policy refusals (consent, role, approval, allowlisted
# command) are deliberate denials and are not contract breaks.
TOOL_CONTRACT_ERRORS = frozenset({"action_unsupported", "malformed_arguments",
                                  "bad_arguments"})


def load_events(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL records, rejecting non-object event values."""
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError(f"event line {line_number} is not an object")
        events.append(event)
    return events


def analyze_trace(
    events: Iterable[Mapping[str, Any]],
    *,
    claim_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Return deterministic tool, denial, step, token, and claim metrics.

    Duplicate calls are counted from the ``tool_calls`` names recorded on each
    model turn. The event surface currently does not retain call arguments, so
    this is deliberately a conservative name-level metric.

    ``tool_contract_breaks`` counts refusals whose error is in
    ``TOOL_CONTRACT_ERRORS``. ``tool_calls_per_completed_task`` divides tool
    results by loops that finished with ``stop == "complete"``; with no
    completed loop it is ``None``, because an efficiency figure for work that
    never finished would read as a number when it is not one.
    """
    materialized = list(events)
    turns = [event for event in materialized if event.get("kind") == "model_turn"]
    tool_results = [event for event in materialized if event.get("kind") == "tool_result"]
    refusals = [event for event in materialized if event.get("kind") == "refusal"]
    completed = sum(
        1 for event in materialized
        if event.get("kind") == "loop_finished" and event.get("stop") == "complete")

    refusals_by_error: dict[str, int] = {}
    for refusal in refusals:
        error = refusal.get("error")
        key = str(error) if error else "unknown"
        refusals_by_error[key] = refusals_by_error.get(key, 0) + 1
    contract_breaks = sum(count for error, count in refusals_by_error.items()
                          if error in TOOL_CONTRACT_ERRORS)

    duplicate_calls = 0
    duplicate_turns = 0
    for turn in turns:
        names = turn.get("tool_calls") or []
        if not isinstance(names, list):
            names = []
        duplicates = len(names) - len(set(str(name) for name in names))
        if duplicates:
            duplicate_turns += 1
            duplicate_calls += duplicates

    normalized_claim_ids = list(dict.fromkeys(str(item) for item in claim_ids))
    evidenced = {
        str(event["claim_id"])
        for event in materialized
        if event.get("kind") in CLAIM_EVIDENCE_KINDS and event.get("claim_id") is not None
    }
    covered = [claim_id for claim_id in normalized_claim_ids if claim_id in evidenced]
    uncovered = [claim_id for claim_id in normalized_claim_ids if claim_id not in evidenced]

    tool_result_count = len(tool_results)
    return {
        "model_turns": len(turns),
        "steps": max((safe_nonnegative_int(turn.get("step")) for turn in turns), default=0),
        "tokens": sum(safe_nonnegative_int(turn.get("tokens")) for turn in turns),
        "tool_results": tool_result_count,
        "refusals": len(refusals),
        "refusals_by_error": dict(sorted(refusals_by_error.items())),
        "tool_contract_breaks": contract_breaks,
        "denial_rate": (len(refusals) / tool_result_count if tool_result_count else 0.0),
        "completed_tasks": completed,
        "tool_calls_per_completed_task": (
            tool_result_count / completed if completed else None),
        "duplicate_tool_calls": duplicate_calls,
        "turns_with_duplicate_calls": duplicate_turns,
        "claim_count": len(normalized_claim_ids),
        "covered_claims": covered,
        "uncovered_claims": uncovered,
        "claim_coverage_rate": (
            len(covered) / len(normalized_claim_ids) if normalized_claim_ids else 1.0
        ),
    }


def safe_nonnegative_int(value: Any) -> int:
    """Normalize counters without allowing malformed or negative inflation."""
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)
