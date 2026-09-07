"""Deterministic, offline event observation. No model, runner, or tool dispatch.

Only selected structured metadata is rendered. Hash links establish local
consistency, not authenticity, and cannot detect a rewritten complete chain.
See OBSERVER.md for event predicates, attribution limits and output semantics.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import uuid
from typing import Any

from .audit import verify_chain_lines

MAX_INPUT_BYTES = 64 * 1024 * 1024
TIER_ORDER = ("local", "cheap", "mid", "frontier")
HALTS = ("needs_human", "needs_arbitration", "needs_approval", "failed", "cancelled")
SUCCESS = ("passed", "skipped_resume")


class ObserverError(ValueError):
    """A stable diagnostic; never includes source text or exception payloads."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def valid_run_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value))


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strict_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("nonfinite JSON constant")


def _validate_event(event: dict) -> None:
    kind = event.get("kind")
    if not _string(kind) or type(event.get("seq")) is not int or event["seq"] < 1:
        raise ObserverError("invalid_event")
    required = {
        "phase_start": ("phase",), "phase_done": ("phase", "status"),
        "routing_trace": ("agent", "tier"), "ownership_claimed": ("agent", "path"),
        "position_recorded": ("phase", "label", "stance"),
        "check": ("name",), "bid_recorded": ("phase", "tier"),
        "bid_outcome": ("phase", "tier"),
    }
    if any(not _string(event.get(key)) for key in required.get(kind, ())):
        raise ObserverError("invalid_event")
    interpreted = set(required) | {"gate_verdict", "model_turn", "workflow_start", "workflow_done"}
    if kind in interpreted and "phase" in event and not _string(event["phase"]):
        raise ObserverError("invalid_event")
    if kind in ("check", "gate_verdict"):
        if type(event.get("passed")) is not bool:
            raise ObserverError("invalid_event")
        if type(event.get("attempt", 1)) is not int or event.get("attempt", 1) < 1:
            raise ObserverError("invalid_event")
    if kind == "model_turn" and "tokens" in event:
        if type(event["tokens"]) is not int or event["tokens"] < 0:
            raise ObserverError("invalid_event")
    if kind == "workflow_done" and "statuses" in event:
        statuses = event["statuses"]
        if not isinstance(statuses, dict) or any(
                not _string(k) or not _string(v) for k, v in statuses.items()):
            raise ObserverError("invalid_event")
    if kind == "position_recorded":
        for key in ("provider", "summary"):
            if key in event and not isinstance(event[key], str):
                raise ObserverError("invalid_event")
    if kind == "bid_outcome" and "premortem_scores" in event:
        if not isinstance(event["premortem_scores"], list):
            raise ObserverError("invalid_event")


def _diagnostic(code: str, run_id: str = "", seq: list[int] | None = None) -> dict:
    return {"schema_version": 1, "run_id": run_id, "outcome": "integrity_error",
            "chain": {"ok": False, "diagnostic": code}, "phases": [],
            "observations": [{"id": code, "severity": "error", "phase": None,
                              "seq": seq or [], "detail": "Observation refused."}]}


def build_narrative(events: list[dict], workflow: dict | None = None) -> dict:
    """Reduce ordered decoded events; callers supply a verified snapshot.

    No filesystem or configuration lookup occurs here. An explicit workflow
    enables declared-write comparison only; the CLI does not load mutable YAML.
    """
    phases: dict[str, dict] = {}
    active: set[str] = set()
    observations: list[dict] = []
    routes: dict[tuple[str, str], tuple[str, int]] = {}
    failures: dict[str, int] = {}
    providers: dict[str, list[tuple[str, int]]] = {}
    run_id = ""
    outcome = "in_progress"
    done_seq: list[int] = []
    final_statuses: dict[str, str] = {}
    declared = {}
    if workflow is not None:
        if not isinstance(workflow, dict) or not isinstance(workflow.get("phases", []), list):
            raise ObserverError("invalid_event")
        for phase in workflow.get("phases", []):
            if not isinstance(phase, dict) or not _string(phase.get("name")):
                raise ObserverError("invalid_event")
            if "writes" in phase:
                if not isinstance(phase["writes"], list) or not all(_string(x) for x in phase["writes"]):
                    raise ObserverError("invalid_event")
                declared[phase["name"]] = phase["writes"]

    def finding(identifier, phase, seq, detail, severity="warning"):
        observations.append({"id": identifier, "severity": severity,
                             "phase": phase, "seq": seq, "detail": detail})

    def phase_for(name, seq):
        if name not in phases:
            phases[name] = {"name": name, "seq": [seq],
                            "origin": {"tier": None, "routes": [], "bids": []},
                            "execution": {"tokens": 0, "seq": [], "claims": []},
                            "validation": {"status": "in_progress", "seq": [], "attempts": []},
                            "observations": []}
        elif seq not in phases[name]["seq"]:
            phases[name]["seq"].append(seq)
        return phases[name]

    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise ObserverError("invalid_event")
        _validate_event(event)
        seq, kind = event["seq"], event["kind"]
        if seq != index:
            raise ObserverError("chain_break")
        if kind == "workflow_start":
            run_id = event.get("run_id", "") if isinstance(event.get("run_id", ""), str) else ""
            # A resume starts another attempt; old completion is not current.
            outcome, done_seq, final_statuses = "in_progress", [], {}
        if kind == "workflow_done":
            done_seq = [seq]
            final_statuses = event.get("statuses", {})
            outcome = "completed"
            continue
        if kind == "phase_start":
            name = event["phase"]
            active.add(name)
            phase = phase_for(name, seq)
            phase["validation"]["status"] = "in_progress"
            phase["validation"]["seq"] = [seq]
            phase["validation"]["attempts"] = []
            phase["origin"]["tier"] = None
            failures.pop(name, None)
            routes = {key: value for key, value in routes.items() if key[0] != name}
            continue
        name = event.get("phase")
        if name is None and len(active) == 1:
            name = next(iter(active))
        interpreted = kind in {"phase_done", "routing_trace", "model_turn", "check", "gate_verdict",
                               "ownership_claimed", "position_recorded", "bid_recorded", "bid_outcome"}
        if not interpreted:
            continue
        if name is None:
            if active:
                finding("ambiguous_phase", None, [seq], "Event has no unique active phase.", "info")
            continue
        phase = phase_for(name, seq)
        if kind == "phase_done":
            phase["validation"].update(status=event["status"], seq=[seq])
            active.discard(name)
        elif kind == "routing_trace":
            tier, agent = event["tier"], event["agent"]
            prior = routes.get((name, agent))
            if prior and prior[0] in TIER_ORDER and tier in TIER_ORDER:
                if TIER_ORDER.index(tier) > TIER_ORDER.index(prior[0]) and failures.get(name, 0) <= prior[1]:
                    finding("escalation_without_lower_rung_failure", name, [seq],
                            "Known tier increased without an intervening failed check or verdict.")
            routes[(name, agent)] = (tier, seq)
            phase["origin"]["tier"] = tier
            phase["origin"]["routes"].append({"tier": tier, "agent": agent, "seq": [seq]})
        elif kind == "model_turn":
            if "tokens" in event:
                phase["execution"]["tokens"] += event["tokens"]
                phase["execution"]["seq"].append(seq)
        elif kind in ("check", "gate_verdict"):
            attempts = phase["validation"]["attempts"]
            number = event.get("attempt", 1)
            attempt = next((a for a in attempts if a["attempt"] == number), None)
            if attempt is None:
                attempt = {"attempt": number, "checks": [], "seq": []}
                attempts.append(attempt)
            attempt["seq"].append(seq)
            if kind == "check":
                attempt["checks"].append({"name": event["name"], "passed": event["passed"]})
            else:
                attempt["passed"] = event["passed"]
            if not event["passed"]:
                failures[name] = seq
        elif kind == "ownership_claimed":
            path = event["path"]
            phase["execution"]["claims"].append({"path": path, "seq": [seq]})
            if name in declared and not any(path == rule or
                    (rule.endswith("/") and path.startswith(rule)) for rule in declared[name]):
                finding("scope_drift", name, [seq], f"Claimed path outside explicit declared writes: {path}")
        elif kind == "position_recorded":
            provider = event.get("provider")
            if _string(provider):
                providers.setdefault(name, []).append((provider, seq))
            summary = event.get("summary", "")
            if isinstance(summary, str) and summary.startswith("(stance unparseable"):
                finding("unparseable_output", name, [seq], "Position reports an unparseable stance.")
        elif kind == "bid_recorded":
            # Synthetic future-event interpretation only; never invokes bidding.
            bid = {"tier": event["tier"], "seq": [seq]}
            phase["origin"]["bids"].append(bid)
        elif kind == "bid_outcome" and isinstance(event.get("premortem_scores"), list):
            if event["premortem_scores"]:
                finding("premortem_scored", name, [seq], "Source records pre-mortem scores; not independently verified.", "info")

    for name, values in providers.items():
        if len(values) >= 2 and len({p for p, _ in values}) == 1:
            finding("provider_monoculture", name, [s for _, s in values],
                    "Two or more positions report the same provider.", "info")
    if done_seq:
        statuses = list(final_statuses.values()) or [p["validation"]["status"] for p in phases.values()]
        halt = next((s for s in statuses if s in HALTS), None)
        if halt:
            outcome = halt
        elif active or any(s not in SUCCESS for s in statuses):
            outcome = "in_progress"
    observations.sort(key=lambda x: (x["seq"][0], x["phase"] or "", x["id"]))
    for observation in observations:
        if observation["phase"] in phases:
            phases[observation["phase"]]["observations"].append(observation)
    return {"schema_version": 1, "run_id": run_id, "outcome": outcome,
            "outcome_seq": done_seq, "chain": {"ok": True, "length": len(events)},
            "phases": list(phases.values()), "observations": observations}


def render_narrative(narrative: dict) -> str:
    def cite(seqs):
        return " (" + ", ".join(f"seq {s}" for s in seqs) + ")" if seqs else ""

    def safe(value):
        return html.escape(json.dumps(value, ensure_ascii=True)).replace("`", "&#96;")

    lines = ["# Offline run observation", "", f"Run: {safe(narrative['run_id'])}"]
    if "source_sha256" in narrative:
        lines.append(f"Source SHA-256: {narrative['source_sha256']}")
    if not narrative["chain"]["ok"]:
        lines += ["", f"Integrity BROKEN: {narrative['chain']['diagnostic']}",
                  "No narrative claims generated."]
        return "\n".join(lines) + "\n"
    lines += [f"Outcome: {safe(narrative['outcome'])}" + cite(narrative.get("outcome_seq", [])),
              "Derived metadata only. This report grants no authority."]
    for phase in narrative["phases"]:
        lines += ["", f"## Phase {safe(phase['name'])}" + cite(phase["seq"][:1]),
                  f"Status: {safe(phase['validation']['status'])}" + cite(phase["validation"]["seq"])]
        for route in phase["origin"]["routes"]:
            lines.append(f"Route: {safe(route['tier'])}" + cite(route["seq"]))
        for attempt in phase["validation"]["attempts"]:
            lines.append(f"Validation: {safe({k: v for k, v in attempt.items() if k != 'seq'})}" + cite(attempt["seq"]))
        if phase["execution"]["seq"]:
            lines.append(f"Reported tokens: {phase['execution']['tokens']}" + cite(phase["execution"]["seq"]))
    if narrative["observations"]:
        lines += ["", "## Observations"]
        for item in narrative["observations"]:
            lines.append(f"- {item['id']}: {safe(item['detail'])}" + cite(item["seq"]))
    return "\n".join(lines) + "\n"


def _regular(fd: int, name: str, *, optional=False) -> None:
    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        if optional:
            return
        raise ObserverError("missing_input") from None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ObserverError("unsafe_path")


def _read(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks, size = [], 0
    while chunk := os.read(fd, 65536):
        size += len(chunk)
        if size > MAX_INPUT_BYTES:
            raise ObserverError("input_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def observe_run(run_dir: Path, *, workflow: dict | None = None) -> dict:
    """Read one pinned journal and replace derived artifacts only.

    Directory descriptors and no-follow opens confine traversal and writes on
    supported POSIX systems. No unsafe-platform fallback follows symlinks.
    """
    run_dir = Path(run_dir).absolute()
    if not valid_run_id(run_dir.name) or run_dir.parent.name != "runs":
        raise ObserverError("unsafe_path")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ObserverError("unsafe_path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        with ExitStack() as stack:
            def directory(name, parent=None):
                fd = os.open(name, flags, dir_fd=parent)
                stack.callback(os.close, fd)
                return fd
            rootfd = directory(run_dir.parent.parent.resolve())
            runsfd = directory("runs", rootfd)
            runfd = directory(run_dir.name, runsfd)
            try:
                outfd = directory("observer", runfd)
            except FileNotFoundError:
                outfd = None
            if outfd is not None:
                for name in ("narrative.json", "narrative.md"):
                    _regular(outfd, name, optional=True)
            data = b""
            sourcefd = None
            try:
                _regular(runfd, "events.jsonl")
                sourcefd = os.open("events.jsonl", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=runfd)
                stack.callback(os.close, sourcefd)
                info = os.fstat(sourcefd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ObserverError("unsafe_path")
                data = _read(sourcefd)
                if not data:
                    raise ObserverError("missing_input")
                if not data.endswith(b"\n"):
                    raise ObserverError("partial_record")
                try:
                    lines = [line for line in data.decode("utf-8").splitlines() if line.strip()]
                    events = [json.loads(line, parse_constant=_reject_constant,
                                         object_pairs_hook=_strict_object) for line in lines]
                except (UnicodeError, ValueError, RecursionError):
                    raise ObserverError("malformed_json") from None
                if not lines:
                    raise ObserverError("missing_input")
                chain = verify_chain_lines(lines)
                if not chain["ok"]:
                    result = _diagnostic("chain_break", run_dir.name, chain["breaks"])
                else:
                    result = build_narrative(events, workflow=workflow)
                    result["run_id"] = run_dir.name
            except ObserverError as exc:
                if exc.code == "unsafe_path":
                    raise
                result = _diagnostic(exc.code, run_dir.name)
            result["source_sha256"] = hashlib.sha256(data).hexdigest()
            # A changing journal is refused rather than reported against stale bytes.
            if sourcefd is not None and _read(sourcefd) != data:
                raise ObserverError("source_changed")
            if outfd is None:
                os.mkdir("observer", mode=0o700, dir_fd=runfd)
                outfd = directory("observer", runfd)
            outputs = {"narrative.json": json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=2) + "\n",
                       "narrative.md": render_narrative(result)}
            if sourcefd is not None:
                try:
                    current = os.stat("events.jsonl", dir_fd=runfd, follow_symlinks=False)
                except OSError:
                    raise ObserverError("source_changed") from None
                if ((current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)
                        or _read(sourcefd) != data):
                    raise ObserverError("source_changed")
            # Stage before replacing; replacing a directory entry never writes through
            # an existing symlink/hardlink. Each output file is atomically replaced.
            staged = []
            try:
                for name, content in outputs.items():
                    _regular(outfd, name, optional=True)
                    temp = "." + name + "." + uuid.uuid4().hex
                    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=outfd)
                    staged.append((temp, name))
                    with os.fdopen(fd, "w", encoding="utf-8") as fh:
                        fh.write(content)
                for temp, name in staged:
                    _regular(outfd, name, optional=True)
                    os.replace(temp, name, src_dir_fd=outfd, dst_dir_fd=outfd)
            finally:
                for temp, _ in staged:
                    try:
                        os.unlink(temp, dir_fd=outfd)
                    except FileNotFoundError:
                        pass
            return result
    except ObserverError:
        raise
    except FileNotFoundError:
        raise ObserverError("missing_input") from None
    except (OSError, ValueError, TypeError):
        raise ObserverError("unsafe_path") from None
