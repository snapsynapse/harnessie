"""Audit: verify the event hash chain and render the governance timeline.

The events log (events.py) chains each line to its predecessor by SHA-256.
verify_chain() walks the file and reports every broken link; a clean report
means the log was appended in order and never edited in place. The governance
timeline filters the log down to the events a human auditor cares about:
consent, ownership, structured refusals, change requests, injection flags, gate
verdicts, decisions, arbitration, operator actions (approval grants/denials,
arbitration detected on resume), and memory maintenance (facts saved and
expired) — one composite timeline of agent and human actions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .events import GENESIS, line_hash

GOVERNANCE_KINDS = frozenset({
    "consent_granted", "consent_declined",
    "ownership_claimed", "ownership_denied", "change_request",
    "refusal",
    "injection_flag",
    "gate_verdict", "check",
    "position_recorded", "objection_recorded",
    "decision_assembled", "decision_converged", "needs_arbitration",
    "decision_arbitrated",
    # operator actions: the human is IN the composite timeline (v0.3)
    "approval_granted", "approval_denied", "operator_action",
    # memory maintenance (v0.3)
    "fact_saved", "fact_expired",
    "phase_done", "workflow_start", "workflow_done",
})


def verify_chain(run_dir: Path) -> dict[str, Any]:
    """Walk events.jsonl and check every seq/prev link.

    Returns {ok, length, breaks} where breaks lists the 1-based line numbers
    whose link check failed (bad prev hash, bad seq, or unparseable line).
    """
    path = Path(run_dir) / "events.jsonl"
    if not path.exists():
        return {"ok": False, "length": 0, "breaks": [], "error": "no events log"}
    breaks: list[int] = []
    prev, seq = GENESIS, 0
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            breaks.append(n)
            prev, seq = line_hash(line), seq + 1
            continue
        if rec.get("prev") != prev or rec.get("seq") != seq + 1:
            breaks.append(n)
        prev, seq = line_hash(line), rec.get("seq", seq + 1)
    return {"ok": not breaks, "length": len(lines), "breaks": breaks}


def governance_timeline(run_dir: Path) -> list[dict[str, Any]]:
    """The governance-relevant events, in order, parsed."""
    path = Path(run_dir) / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out.append({"kind": "unparseable_line", "raw": line[:200]})
            continue
        if rec.get("kind") in GOVERNANCE_KINDS:
            out.append(rec)
    return out


def format_audit(run_id: str, chain: dict[str, Any],
                 timeline: list[dict[str, Any]],
                 decisions: list[dict[str, Any]] | None = None) -> str:
    lines = [f"audit {run_id}: chain "
             + ("OK" if chain["ok"] else f"BROKEN at line(s) {chain['breaks']}")
             + f" ({chain['length']} events)"]
    for rec in timeline:
        data = {k: v for k, v in rec.items()
                if k not in ("ts", "seq", "prev", "kind")}
        lines.append(f"  {rec.get('seq', '?'):>5}  {rec['kind']:<22} "
                     f"{json.dumps(data, default=str)[:160]}")
    for d in decisions or []:
        lines.append(f"  decision {d['path']}: status={d['status']} "
                     f"claims={d['claims']}")
    return "\n".join(lines)
