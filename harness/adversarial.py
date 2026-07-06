"""Adversarial contested phases: positions -> objections -> record -> human.

Modeled on AIDR's record lifecycle (one decision, one file; positions with
metadata; dissent never deleted; human-only arbitration; structurally earned
claims) and Turnfile's conflict ladder (bounded rebuttal rounds, explicit
no-new-objection convergence). The harness assembles the record and lints it;
no agent and no harness code path ever writes the Arbitration section — the
operator edits the record file in their own words and re-runs.

Records are AIDR-shaped markdown under runs/<run_id>/decisions/, outside the
workspace jail, so no agent can reach them. Claims are structural only:
whether arbitration prose genuinely answers each objection is the human's
responsibility. Lint checks form, never judgment.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import yaml

from .ids import generate
from .verify import _json_objects

STANCES = ("recommend", "oppose", "alternative", "abstain")
RECORD_STATUSES = ("open", "arbitrated", "superseded")


@dataclass
class PositionRecord:
    label: str
    agent: str
    model_id: str
    provider: str
    stance: str
    summary: str
    prose: str


def parse_stance(report: str) -> dict[str, str] | None:
    """Last JSON object carrying a valid "stance" wins (same discipline as
    verifier verdicts). Anything else returns None — fail closed: an
    unparseable stance is dissent, never silent convergence."""
    found = None
    for obj in _json_objects(report):
        if "stance" in obj:
            found = obj
    if not found or found.get("stance") not in STANCES:
        return None
    return {"stance": str(found["stance"]),
            "summary": str(found.get("summary", ""))[:500]}


def parse_objection_response(report: str) -> dict[str, Any] | None:
    """Last JSON object carrying an "objections" list wins; None fails closed
    (treated as dissent by the caller)."""
    found = None
    for obj in _json_objects(report):
        if "objections" in obj:
            found = obj
    if not found or not isinstance(found.get("objections"), list):
        return None
    return {"objections": [str(o)[:500] for o in found["objections"]],
            "no_new_objection": bool(found.get("no_new_objection", False))}


def converged(positions: list[PositionRecord],
              objections: list[dict[str, str]]) -> bool:
    """Structural convergence: every stance is "recommend" and no objection
    stands. Semantic conflict between two "recommend" summaries is expected to
    surface as an objection in the rebuttal round — that is what the round is
    for; anything unresolved there goes to the human."""
    if not positions:
        return False
    return (all(p.stance == "recommend" for p in positions)
            and not objections)


def _fence_prose(prose: str) -> str:
    """Keep position prose from breaking record structure: any line that could
    read as a markdown heading is quoted."""
    return "\n".join(("> " + l) if l.lstrip().startswith("#") else l
                     for l in prose.splitlines())


def assemble_record(record_id: str, title: str, question: str, context: str,
                    arbiter: str, positions: list[PositionRecord],
                    objections: list[dict[str, str]],
                    evidence: list[str], date: str | None = None) -> str:
    date = date or time.strftime("%Y-%m-%d")
    lines = [
        "---",
        f"id: {record_id}",
        f"ref: DR-{generate(5, check_digit=True)}",
        # JSON string quoting is valid YAML and survives colons in titles
        # (the AIDR assemble tool learned this the hard way: unquoted plain
        # scalars go type-ambiguous or blow up the frontmatter parse).
        f"title: {json.dumps(title)}",
        "status: open",
        f"date: {date}",
        f"arbiter: {json.dumps(str(arbiter))}",
        "tags: [harnessie, contested-phase]",
        "---",
        f"# {record_id}: {title}",
        "",
        "## Context",
        "",
        context.strip(),
        "",
        "Independence statement: positions were generated in isolated model "
        "contexts with read-only tool grants within one harness process; "
        "isolation is code-enforced for context and tools, behavioral for "
        "everything a shared filesystem could leak. The hash-chained events "
        "log is the evidence it held.",
        "",
        "## Question",
        "",
        question.strip(),
        "",
        "## Positions",
        "",
    ]
    for p in positions:
        lines += [
            f"### Position: {p.label}",
            "",
            f"- agent: {p.agent}",
            f"- model: {p.model_id}",
            f"- provider: {p.provider}",
            f"- stance: {p.stance}",
            f"- summary: {p.summary}",
            "",
            _fence_prose(p.prose.strip()) or "(no prose)",
            "",
        ]
    lines += ["## Objections", ""]
    for o in objections:
        lines += [
            f"### Objection: {o['by']} to {o['to']}",
            "",
            _fence_prose(str(o["text"]).strip()),
            "",
        ]
    lines += [
        "## Arbitration",
        "",
        "## Evidence",
        "",
    ]
    lines += [f"- {e}" for e in evidence]
    return "\n".join(lines).rstrip() + "\n"


# -- structural lint + earned claims -------------------------------------------

def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        return {}, text
    try:
        fm = yaml.safe_load(parts[0][3:]) or {}
    except yaml.YAMLError:
        return {}, text
    return (fm if isinstance(fm, dict) else {}), parts[1]


def _sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def _positions_meta(positions_body: str) -> list[dict[str, str]]:
    metas: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in positions_body.splitlines():
        if line.startswith("### Position:"):
            current = {"label": line.split(":", 1)[1].strip()}
            metas.append(current)
        elif current is not None and line.startswith("- ") and ":" in line:
            key, _, val = line[2:].partition(":")
            if key.strip() in ("agent", "model", "provider", "stance", "summary"):
                current.setdefault(key.strip(), val.strip())
    return metas


def _arb_meta(arb_body: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in arb_body.splitlines():
        if line.startswith("- ") and ":" in line:
            key, _, val = line[2:].partition(":")
            if key.strip() in ("decided_by", "date", "decision") and val.strip():
                meta[key.strip()] = val.strip()
    return meta


def lint_record(text: str) -> dict[str, Any]:
    """Structural conformance + earned claims, AIDR-style.

    Claims (structural prerequisites only; semantic adequacy is human work):
      independent-positions  2+ positions with distinct providers
      dissent-preserved      dissent recorded AND arbitration complete
      human-arbitrated       status arbitrated, arbitration filled, zero errors
    """
    errors: list[str] = []
    fm, body = _frontmatter(text)
    for field_name in ("id", "title", "status", "date", "arbiter"):
        if not fm.get(field_name):
            errors.append(f"missing frontmatter field: {field_name}")
    status = str(fm.get("status", ""))
    if status and status not in RECORD_STATUSES:
        errors.append(f"invalid status: {status!r}")
    if status in ("arbitrated", "superseded") and not fm.get("decided"):
        errors.append("arbitrated/superseded record missing decided field")

    sections = _sections(body)
    for name in ("Context", "Question", "Positions", "Arbitration"):
        if name not in sections:
            errors.append(f"missing section: {name}")

    metas = _positions_meta(sections.get("Positions", ""))
    if not metas:
        errors.append("no positions recorded")
    for m in metas:
        for key in ("agent", "model", "provider", "stance", "summary"):
            if not m.get(key):
                errors.append(f"position {m.get('label', '?')!r} missing {key}")
        if m.get("stance") and m["stance"] not in STANCES:
            errors.append(f"position {m.get('label', '?')!r} invalid stance "
                          f"{m['stance']!r}")

    arb = _arb_meta(sections.get("Arbitration", ""))
    arb_complete = all(k in arb for k in ("decided_by", "date", "decision"))
    if status == "open" and arb_complete:
        errors.append("open record must not carry a completed Arbitration")
    if status == "arbitrated" and not arb_complete:
        errors.append("arbitrated record has incomplete Arbitration metadata")

    objection_count = sections.get("Objections", "").count("### Objection:")
    dissent = (objection_count > 0
               or any(m.get("stance") in ("oppose", "alternative") for m in metas))

    claims: list[str] = []
    providers = {m.get("provider") for m in metas if m.get("provider")}
    if len(metas) >= 2 and len(providers) >= 2:
        claims.append("independent-positions")
    if dissent and arb_complete:
        claims.append("dissent-preserved")
    if status == "arbitrated" and arb_complete and not errors:
        claims.append("human-arbitrated")

    return {"errors": errors, "claims": claims, "status": status,
            "decision": arb.get("decision", "")}
