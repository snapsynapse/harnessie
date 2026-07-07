"""Plain-language operator surface: halts and reports a non-developer can read.

The harness makes a promise on its own README: every halt is a named condition
with one plain next action, and disagreement between agents becomes a human
decision, not a silent merge. This module is where that promise becomes text.
Every stop condition explains itself in one sentence and names the single next
action, and `harnessie report` leads with a summary a non-developer can read
rather than a raw event dump (the full trail is still `harnessie audit`).

Pure formatting over run events and phase outcomes, so it is testable without a
live run and imports nothing that would pull in a provider SDK.
"""

from __future__ import annotations

import json
from pathlib import Path

HALT_STATUSES = ("needs_human", "needs_arbitration")

STATUS_PLAIN = {
    "passed": "completed",
    "skipped_resume": "already done, skipped on resume",
    "needs_human": "stopped and is waiting for you",
    "needs_arbitration": "stopped: a contested decision needs your call",
}

_WORKFLOW_PLACEHOLDER = "<your workflow file>"


def plain_status(status: str) -> str:
    """A non-developer phrasing for a phase status."""
    return STATUS_PLAIN.get(status, status)


def halt_next_action(status: str, run_id: str, workflow_ref: str,
                     phase: str) -> str | None:
    """The single next action for a halt, or None if the status is not a halt.

    Named actions only: a real command the operator can run, or a specific file
    to edit, never "investigate further".
    """
    workflow_ref = workflow_ref or _WORKFLOW_PLACEHOLDER
    if status == "needs_human":
        return (
            f'What to do: read the report for "{phase}" above, fix what blocked '
            f"it, then resume where it stopped:\n"
            f"  harnessie resume {run_id} {workflow_ref}"
        )
    if status == "needs_arbitration":
        return (
            f'What to do: a contested decision in "{phase}" needs a human, not '
            f"the agents. Open the decision record under runs/{run_id}/decisions/ "
            f"and, in its Arbitration section, set status: arbitrated with a "
            f"decided: date and your decision. Then resume:\n"
            f"  harnessie resume {run_id} {workflow_ref}"
        )
    return None


def _first_halt(phase_statuses: list[tuple[str, str]]) -> tuple[str, str] | None:
    for phase, status in phase_statuses:
        if status in HALT_STATUSES:
            return phase, status
    return None


def format_run_summary(run_id: str, workflow_ref: str,
                       phase_statuses: list[tuple[str, str]],
                       spent_usd: float, spent_tokens: int) -> str:
    """Summary printed after a run/resume finishes. Leads with the outcome and,
    on a halt, the one named next action."""
    lines: list[str] = []
    halt = _first_halt(phase_statuses)
    if halt is None:
        lines.append(f"Run {run_id} completed. {len(phase_statuses)} phase(s), "
                     f"${spent_usd:.4f}, {spent_tokens} tokens.")
    else:
        phase, status = halt
        lines.append(f"Run {run_id} {plain_status(status)} at \"{phase}\". "
                     f"${spent_usd:.4f}, {spent_tokens} tokens so far.")
    lines.append("")
    for phase, status in phase_statuses:
        lines.append(f"  - {phase}: {plain_status(status)}")
    if halt is not None:
        lines.append("")
        lines.append(halt_next_action(halt[1], run_id, workflow_ref, halt[0]))
    return "\n".join(lines)


def _load_events(run_dir: Path) -> list[dict]:
    events = run_dir / "events.jsonl"
    if not events.exists():
        return []
    out = []
    for line in events.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def format_report(run_dir: Path) -> str:
    """Plain-language report for `harnessie report <run_id>`, reconstructed from
    the run's event log. Works even on a run that crashed mid-phase (no
    workflow_done), which is exactly when the operator reaches for it."""
    events = _load_events(run_dir)
    if not events:
        return (f"No run found at {run_dir.name}. Check the run id, or list runs "
                f"under the runs/ directory.")

    start = next((e for e in events if e.get("kind") == "workflow_start"), {})
    done = next((e for e in reversed(events)
                 if e.get("kind") == "workflow_done"), None)
    name = start.get("name") or "(unnamed workflow)"
    goal = start.get("goal") or ""
    workflow_ref = start.get("workflow") or _WORKFLOW_PLACEHOLDER
    run_id = start.get("run_id") or run_dir.name

    # last status wins per phase, order of first appearance preserved
    order: list[str] = []
    status_by_phase: dict[str, str] = {}
    spent_usd = 0.0
    for e in events:
        if e.get("kind") == "phase_done":
            phase = e.get("phase", "?")
            if phase not in status_by_phase:
                order.append(phase)
            status_by_phase[phase] = e.get("status", "?")
            spent_usd = e.get("spent_usd", spent_usd)
    if done is not None:
        spent_usd = done.get("spent_usd", spent_usd)
    phase_statuses = [(p, status_by_phase[p]) for p in order]

    lines = [f"Run {run_id}  —  workflow: {name}"]
    if goal:
        lines.append(f"Goal: {goal}")
    lines.append("")

    if not phase_statuses:
        lines.append("This run recorded no completed phases. It may have failed "
                      "before the first phase finished.")
    else:
        halt = _first_halt(phase_statuses)
        if halt is None and done is not None:
            lines.append(f"Outcome: completed. ${spent_usd:.4f} spent.")
        elif halt is None:
            lines.append("Outcome: in progress or interrupted (no completion "
                         f"recorded yet). ${spent_usd:.4f} spent so far.")
        else:
            lines.append(f"Outcome: {plain_status(halt[1])} at \"{halt[0]}\". "
                         f"${spent_usd:.4f} spent so far.")
        lines.append("")
        lines.append("Phases:")
        for phase, status in phase_statuses:
            lines.append(f"  - {phase}: {plain_status(status)}")
        halt = _first_halt(phase_statuses)
        if halt is not None:
            lines.append("")
            lines.append(halt_next_action(halt[1], run_id, workflow_ref, halt[0]))

    lines.append("")
    lines.append(f"Full audit trail (every action, hash-verified): "
                 f"harnessie audit {run_id}")
    return "\n".join(lines)


__all__ = [
    "plain_status",
    "halt_next_action",
    "format_run_summary",
    "format_report",
    "HALT_STATUSES",
]
