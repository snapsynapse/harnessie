"""Export a Harnessie event log as an ATIF trajectory.

ATIF (Agent Trajectory Interchange Format, Harbor RFC 0001) is the record a
harness writes of its own run so that an independent capture of the same run,
such as a proxy sitting between the harness and the model, can be checked
against it call for call. Harnessie's hash-chained ``events.jsonl`` is
already that record; this module reshapes it.

The exporter refuses rather than guess. A broken hash chain, a loop that never
reached ``loop_finished``, or steps that do not advance by one each produce an
``AtifExportError``, because a plausible trajectory built from a damaged log
is worse than no trajectory.

What the event log does not hold is reported, not invented. Model messages,
system prompts and tool arguments are deliberately absent from the audit
stream (it carries placeholders and 300-character tool-result excerpts), so
``message`` is empty, ``arguments`` is ``{}`` with ``arguments_recorded``
false, and observation content is the excerpt the log kept. Token fields
appear only when the log recorded them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .audit import verify_chain_lines

ATIF_SCHEMA_VERSION = "ATIF-v1.7"
ATIF_SPEC = ("https://github.com/harbor-framework/harbor/blob/main/rfcs/"
             "0001-trajectory-format.md")
AGENT_NAME = "harnessie"
TOOL_RESULT_EXCERPT_CHARS = 300
OUTPUT_NAME = "trajectory.json"

NOTES = (
    "Exported from Harnessie's hash-chained events.jsonl after the chain "
    "verified. Model messages, system prompts and tool arguments are not "
    "recorded in that log, so agent `message` fields are empty and tool-call "
    "`arguments` are `{}` with `arguments_recorded: false`. Observation "
    f"content is the {TOOL_RESULT_EXCERPT_CHARS}-character excerpt the log "
    "keeps. A run with several agent loops is flattened into one step "
    "sequence; each agent step's `extra.role` and `extra.loop` say which loop "
    "it belongs to, and `final_metrics.extra.loops` lists how each ended."
)


class AtifExportError(ValueError):
    """The event log cannot honestly be rendered as a trajectory."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _iso(ts: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def build_trajectory(events: list[dict[str, Any]], *, session_id: str,
                     chain_length: int | None = None) -> dict[str, Any]:
    """Shape verified events into an ATIF document. Pure; raises on a log
    that cannot be rendered truthfully."""
    turns = [e for e in events if e.get("kind") == "model_turn"]
    if not turns:
        raise AtifExportError("no_model_turns", "the log records no model call")

    steps: list[dict[str, Any]] = []
    start = next((e for e in events if e.get("kind") == "workflow_start"), None)
    if start is not None and start.get("goal"):
        step: dict[str, Any] = {"step_id": 1, "source": "user",
                                "message": str(start["goal"]),
                                "extra": {"event_seq": start.get("seq")}}
        stamp = _iso(start.get("ts"))
        if stamp:
            step["timestamp"] = stamp
        steps.append(step)

    identity = next((e for e in events if e.get("kind") == "harness_identity"), None)

    loops: list[dict[str, Any]] = []
    loop_index = 1
    expected_step = 1
    open_turns = 0
    current: dict[str, Any] | None = None
    unmatched_calls: list[str] = []
    roles: set[str] = set()
    models: list[str] = []
    prompt_total: int | None = 0
    completion_total: int | None = 0
    tokens_total = 0

    for event in events:
        kind = event.get("kind")
        if kind == "model_turn":
            step_no = event.get("step")
            if step_no != expected_step:
                raise AtifExportError(
                    "step_sequence",
                    f"loop {loop_index} expected step {expected_step}, "
                    f"log has {step_no!r} at seq {event.get('seq')}")
            expected_step += 1
            open_turns += 1
            names = event.get("tool_calls") or []
            if not isinstance(names, list):
                names = []
            ids = event.get("tool_call_ids")
            if not isinstance(ids, list) or len(ids) != len(names):
                ids = [f"seq{event.get('seq')}-call{i}" for i in range(1, len(names) + 1)]
            ids = [str(item) for item in ids]
            role = event.get("role")
            if role:
                roles.add(str(role))
            step = {
                "step_id": len(steps) + 1,
                "source": "agent",
                "message": "",
                "llm_call_count": 1,
                "extra": {
                    "event_seq": event.get("seq"),
                    "role": role,
                    "loop": loop_index,
                    "loop_step": step_no,
                    "stop_reason": event.get("stop_reason"),
                    "message_recorded": False,
                },
            }
            stamp = _iso(event.get("ts"))
            if stamp:
                step["timestamp"] = stamp
            if event.get("model"):
                step["model_name"] = str(event["model"])
                if event["model"] not in models:
                    models.append(str(event["model"]))
            if event.get("effort"):
                step["reasoning_effort"] = str(event["effort"])
            if names:
                step["tool_calls"] = [
                    {"tool_call_id": call_id, "function_name": str(name),
                     "arguments": {}, "extra": {"arguments_recorded": False}}
                    for call_id, name in zip(ids, names)
                ]
            metrics: dict[str, Any] = {}
            prompt = _int_or_none(event.get("input_tokens"))
            completion = _int_or_none(event.get("output_tokens"))
            total = _int_or_none(event.get("tokens"))
            if prompt is not None and completion is not None:
                metrics["prompt_tokens"] = prompt
                metrics["completion_tokens"] = completion
                if prompt_total is not None:
                    prompt_total += prompt
                if completion_total is not None:
                    completion_total += completion
            else:
                # Older logs carry one total; say so rather than split it.
                prompt_total = completion_total = None
                if total is not None:
                    metrics["extra"] = {"total_tokens": total, "split_recorded": False}
            if total is not None:
                tokens_total += total
            if metrics:
                step["metrics"] = metrics
            steps.append(step)
            current = step
            unmatched_calls = list(ids)
        elif kind == "tool_result" and current is not None:
            call_id = event.get("call_id")
            if isinstance(call_id, str) and call_id in unmatched_calls:
                unmatched_calls.remove(call_id)
            elif not isinstance(call_id, str):
                call_id = unmatched_calls.pop(0) if unmatched_calls else None
            else:
                call_id = None
            result: dict[str, Any] = {
                "content": str(event.get("content", "")),
                "extra": {
                    "tool": event.get("tool"),
                    "ok": event.get("ok"),
                    "provenance": event.get("provenance"),
                    "content_excerpt_chars": TOOL_RESULT_EXCERPT_CHARS,
                    "event_seq": event.get("seq"),
                },
            }
            if call_id is not None:
                result["source_call_id"] = call_id
            current.setdefault("observation", {"results": []})["results"].append(result)
        elif kind == "refusal" and current is not None and current.get("observation"):
            last = current["observation"]["results"][-1]
            last["extra"]["refusal"] = {"error": event.get("error"),
                                        "boundary": event.get("boundary")}
        elif kind == "task_complete" and current is not None:
            completion_id = next(
                (tc["tool_call_id"] for tc in current.get("tool_calls", [])
                 if tc["function_name"] == "task_complete"), None)
            result = {"content": "loop ended: task_complete",
                      "extra": {"tool": "task_complete", "event_seq": event.get("seq")}}
            if completion_id is not None:
                result["source_call_id"] = completion_id
            current.setdefault("observation", {"results": []})["results"].append(result)
        elif kind == "loop_finished":
            loops.append({"loop": loop_index, "role": event.get("role"),
                          "stop": event.get("stop"),
                          "steps": _int_or_none(event.get("steps")),
                          "event_seq": event.get("seq")})
            loop_index += 1
            expected_step = 1
            open_turns = 0
            current = None
            unmatched_calls = []

    if open_turns:
        raise AtifExportError(
            "loop_unfinished",
            f"loop {loop_index} has {open_turns} model turn(s) and no loop_finished")

    agent: dict[str, Any] = {"name": AGENT_NAME, "version": __version__,
                             "extra": {"roles": sorted(roles)}}
    if models:
        agent["model_name"] = models[0]
        if len(models) > 1:
            agent["extra"]["models"] = models
    if identity is not None:
        agent["extra"]["harness_identity"] = {
            k: identity.get(k) for k in
            ("harness_version", "inward_manifest_sha256", "tool_set_sha256")}

    final_metrics: dict[str, Any] = {
        "total_steps": len(steps),
        "extra": {"total_tokens": tokens_total, "loops": loops,
                  "agent_steps": len(turns)},
    }
    if prompt_total is not None and completion_total is not None:
        final_metrics["total_prompt_tokens"] = prompt_total
        final_metrics["total_completion_tokens"] = completion_total

    document: dict[str, Any] = {
        "schema_version": ATIF_SCHEMA_VERSION,
        "session_id": session_id,
        "trajectory_id": f"{session_id}:events",
        "agent": agent,
        "steps": steps,
        "notes": NOTES,
        "final_metrics": final_metrics,
        "extra": {"source": "events.jsonl", "chain_verified": True,
                  "spec": ATIF_SPEC},
    }
    if chain_length is not None:
        document["extra"]["chain_length"] = chain_length
    return document


def export_events(lines: list[str], *, session_id: str) -> dict[str, Any]:
    """Verify the chain over raw journal lines, then build the trajectory."""
    lines = [line for line in lines if line.strip()]
    chain = verify_chain_lines(lines)
    if not chain["ok"]:
        raise AtifExportError(
            "chain_broken",
            f"hash chain fails at line(s) {chain['breaks'][:5]} of {chain['length']}")
    events = [json.loads(line) for line in lines]
    return build_trajectory(events, session_id=session_id,
                            chain_length=chain["length"])


def export_dir(directory: Path) -> dict[str, Any]:
    """Export the ``events.jsonl`` under a run or verify-report directory."""
    path = directory / "events.jsonl"
    if not path.is_file():
        raise AtifExportError("no_events_log", str(path))
    lines = path.read_text(encoding="utf-8").splitlines()
    session_id = directory.name
    for line in lines:
        if '"workflow_start"' in line:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                break
            if isinstance(record, dict) and record.get("kind") == "workflow_start" \
                    and record.get("run_id"):
                session_id = str(record["run_id"])
            break
    return export_events(lines, session_id=session_id)


def write_trajectory(directory: Path, out: Path | None = None, *,
                     force: bool = False) -> Path:
    """Operator-issued file write; no model calls. Refuses to overwrite
    unless told to, so an existing record is never replaced by accident."""
    document = export_dir(directory)
    target = (out or directory / OUTPUT_NAME).resolve()
    if target.exists() and not force:
        raise AtifExportError("output_exists", f"{target} (pass --force to replace)")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return target


__all__ = [
    "ATIF_SCHEMA_VERSION",
    "AtifExportError",
    "build_trajectory",
    "export_dir",
    "export_events",
    "write_trajectory",
]
