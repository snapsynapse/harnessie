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
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
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
    (treated as dissent by the caller). Every objection must be a non-empty
    string. no_new_objection is True only for a literal JSON true: a string,
    number, null or missing marker is not a stand-down."""
    found = None
    for obj in _json_objects(report):
        if "objections" in obj:
            found = obj
    if not found or not isinstance(found.get("objections"), list):
        return None
    items = found["objections"]
    if not all(isinstance(o, str) and o.strip() for o in items):
        return None
    return {"objections": [o[:500] for o in items],
            "no_new_objection": found.get("no_new_objection") is True}


def stood_down(parsed: dict[str, Any] | None) -> bool:
    """An explicit stand-down: a valid empty objection list plus literal
    no_new_objection true. Only a full round of these is quiet."""
    return (parsed is not None and parsed["objections"] == []
            and parsed["no_new_objection"] is True)


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


# Any character a Markdown or YAML reader could treat as a line break.
_LINE_BREAKS = re.compile(r"[\t\n\x0b\x0c\r\x1c-\x1e\x85\u2028\u2029]+")
# Every other C0 control, DEL and C1 control: a terminal would act on them
# and the AIDR exporter rejects them, so they are shown as visible escapes.
_CONTROLS = re.compile(r"[\x00-\x08\x0e-\x1b\x1f\x7f-\x84\x86-\x9f]")
# Prose lines that could read as record structure: ATX/setext headings,
# frontmatter or thematic-break rules and code fences, including when nested
# in list items, plus position and arbitration metadata entries.
_LIST_MARKER = re.compile(r"(?:[-+*]|[0-9]{1,9}[.)])[ \t]+")
_STRUCTURE = re.compile(r"#|`{3,}|~{3,}|(?:=+|-+)[ \t]*$")
_THEMATIC_BREAK = re.compile(r"([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_METADATA_LINE = re.compile(
    r"\s*- (?:agent|model|provider|stance|summary|decided_by|date|decision):")
# An http, https or mailto autolink is kept; any other "<" that could open a
# comment, CDATA, processing instruction, declaration, tag or an autolink in
# another scheme (javascript:, data:, file:) is escaped.
_HTML_OPENER = re.compile(
    r"<(?i:https?|mailto):[^\s<>]*>|<(?=[!?/A-Za-z])")


def _neutralize_html(text: str) -> str:
    """Raw HTML in a record can hide later positions or objections from a
    human reader, so it is rendered as text. A "<" that cannot start HTML,
    as in "a < b", is left as written."""
    return _HTML_OPENER.sub(
        lambda m: m.group() if len(m.group()) > 1 else "&lt;", text)


def _escape_controls(text: str) -> str:
    return _CONTROLS.sub(lambda m: f"\\x{ord(m.group()):02x}", text)


def _scalar(value: Any) -> str:
    """A model- or config-supplied value rendered as one inert line: no line
    breaks, control characters only as visible escapes, and no raw HTML."""
    text = _LINE_BREAKS.sub(" ", _escape_controls(str(value)))
    return _neutralize_html(" ".join(text.split()))


def _structural(line: str) -> bool:
    if _METADATA_LINE.match(line):
        return True
    content = line.lstrip(" \t")
    while True:
        if _THEMATIC_BREAK.match(content):
            return True
        marker = _LIST_MARKER.match(content)
        if not marker:
            break
        content = content[marker.end():].lstrip(" \t")
    return not content.startswith(">") and bool(_STRUCTURE.match(content))


def _fence_prose(prose: str) -> str:
    """Keep prose from breaking record structure: control characters and
    raw HTML are escaped and every line that could read as a heading, rule,
    fence or metadata entry is quoted."""
    # splitlines() is the same boundary rule lint uses, so a CR, VT, FF,
    # NEL or Unicode separator cannot smuggle an unquoted line past this.
    lines = [_neutralize_html(_escape_controls(l)) for l in prose.splitlines()]
    return "\n".join(("> " + l) if _structural(l) else l for l in lines)


def _position_meta(p: PositionRecord) -> dict[str, str]:
    return {"label": _scalar(p.label), "agent": _scalar(p.agent),
            "model": _scalar(p.model_id), "provider": _scalar(p.provider),
            "stance": _scalar(p.stance), "summary": _scalar(p.summary)}


def position_sidecar_path(record_path: Path) -> Path:
    return record_path.with_name(record_path.stem + ".positions.json")


def write_position_sidecar(record_path: Path,
                           positions: list[PositionRecord]) -> None:
    """Structured positions beside the record (outside the workspace jail):
    the source trust claims are derived from, never the rendered text."""
    rows = [{k: v for k, v in asdict(p).items() if k != "prose"}
            for p in positions]
    position_sidecar_path(record_path).write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def load_position_sidecar(record_path: Path) -> list[PositionRecord] | None:
    """None when no sidecar exists (a record from before structured claims);
    an unreadable or malformed sidecar is an empty list, which fails lint."""
    path = position_sidecar_path(record_path)
    if not path.exists():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        fields = ("label", "agent", "model_id", "provider", "stance", "summary")
        if not isinstance(rows, list):
            return []
        positions = []
        for row in rows:
            if not isinstance(row, dict) or not all(
                    isinstance(row.get(k), str) for k in fields):
                return []
            positions.append(PositionRecord(
                **{k: row[k] for k in fields}, prose=""))
        return positions
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []


def lint_record_file(record_path: Path) -> dict[str, Any]:
    return lint_record(record_path.read_text(encoding="utf-8"),
                       positions=load_position_sidecar(record_path))


def assemble_record(record_id: str, title: str, question: str, context: str,
                    arbiter: str, positions: list[PositionRecord],
                    objections: list[dict[str, str]],
                    evidence: list[str], date: str | None = None) -> str:
    date = date or time.strftime("%Y-%m-%d")
    lines = [
        "---",
        f"id: {_scalar(record_id)}",
        f"ref: DR-{generate(5, check_digit=True)}",
        # JSON string quoting is valid YAML and survives colons in titles
        # (the AIDR assemble tool learned this the hard way: unquoted plain
        # scalars go type-ambiguous or blow up the frontmatter parse).
        f"title: {json.dumps(_scalar(title))}",
        "status: open",
        f"date: {date}",
        f"arbiter: {json.dumps(str(arbiter))}",
        "tags: [harnessie, contested-phase]",
        "---",
        f"# {_scalar(record_id)}: {_scalar(title)}",
        "",
        "## Context",
        "",
        _fence_prose(context.strip()),
        "",
        "Independence statement: positions were generated in isolated model "
        "contexts with read-only tool grants within one harness process; "
        "isolation is code-enforced for context and tools, behavioral for "
        "everything a shared filesystem could leak. The hash-chained events "
        "log is the evidence it held.",
        "",
        "## Question",
        "",
        _fence_prose(question.strip()),
        "",
        "## Positions",
        "",
    ]
    for p in positions:
        meta = _position_meta(p)
        lines += [
            f"### Position: {meta['label']}",
            "",
            f"- agent: {meta['agent']}",
            f"- model: {meta['model']}",
            f"- provider: {meta['provider']}",
            f"- stance: {meta['stance']}",
            f"- summary: {meta['summary']}",
            "",
            _fence_prose(p.prose.strip()) or "(no prose)",
            "",
        ]
    lines += ["## Objections", ""]
    for o in objections:
        lines += [
            f"### Objection: {_scalar(o['by'])} to {_scalar(o['to'])}",
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
    lines += [f"- {_scalar(e)}" for e in evidence]
    return "\n".join(lines).rstrip() + "\n"


# -- structural lint + earned claims -------------------------------------------

def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    # Only the first closing delimiter ends the frontmatter: a later rule in
    # the body must never truncate what lint sees.
    head, sep, body = text[3:].partition("\n---")
    if not sep:
        return {}, text
    try:
        fm = yaml.safe_load(head) or {}
    except yaml.YAMLError:
        return {}, text
    return (fm if isinstance(fm, dict) else {}), body


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


def lint_record(text: str,
                positions: list[PositionRecord] | None = None) -> dict[str, Any]:
    """Structural conformance + earned claims, AIDR-style.

    Claims (structural prerequisites only; semantic adequacy is human work):
      independent-positions  2+ positions with distinct providers
      dissent-preserved      dissent recorded AND arbitration complete
      human-arbitrated       status arbitrated, arbitration filled, zero errors

    With structured positions (the harness's own PositionRecords) the
    rendered metadata must match them exactly and independence is derived
    from them alone; without, the record is linted as imported text.
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

    if positions is not None:
        if metas != [_position_meta(p) for p in positions]:
            errors.append("position metadata does not match the structured "
                          "positions recorded by the harness")
        providers = {p.provider for p in positions if p.provider}
        independent = len(positions) >= 2 and len(providers) >= 2
    else:
        providers = {m.get("provider") for m in metas if m.get("provider")}
        independent = len(metas) >= 2 and len(providers) >= 2

    claims: list[str] = []
    if independent:
        claims.append("independent-positions")
    if dissent and arb_complete:
        claims.append("dissent-preserved")
    if status == "arbitrated" and arb_complete and not errors:
        claims.append("human-arbitrated")

    return {"errors": errors, "claims": claims, "status": status,
            "decision": arb.get("decision", "")}
