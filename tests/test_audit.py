"""Tamper-evident audit: hash-chained events log + audit verb.

Each event carries seq and prev (SHA-256 of the previous serialized line);
any post-hoc edit, deletion, or reorder breaks every subsequent link.
Tamper-evident, not tamper-proof: whole-file rewrites are out of scope and
documented as such.
"""

import json

from harness.audit import governance_timeline, verify_chain
from harness.cli import main
from harness.events import EventLog


def _emit_run(run_dir, kinds=("a", "b", "c")):
    log = EventLog(run_dir, echo=False)
    for k in kinds:
        log.emit(k, detail=f"payload-{k}")
    log.close()


def test_chain_fields_present_and_verifies(tmp_path):
    _emit_run(tmp_path / "run")
    lines = (tmp_path / "run" / "events.jsonl").read_text().splitlines()
    first = json.loads(lines[0])
    assert first["seq"] == 1 and first["prev"] == "genesis"
    report = verify_chain(tmp_path / "run")
    assert report["ok"] and report["length"] == 3


def test_chain_survives_reopen(tmp_path):
    # resume appends to the same file; the chain must continue, not restart
    _emit_run(tmp_path / "run", kinds=("a", "b"))
    log = EventLog(tmp_path / "run", echo=False)
    log.emit("c", detail="after-resume")
    log.close()
    report = verify_chain(tmp_path / "run")
    assert report["ok"] and report["length"] == 3


def test_edited_line_breaks_chain(tmp_path):
    _emit_run(tmp_path / "run")
    path = tmp_path / "run" / "events.jsonl"
    lines = path.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["detail"] = "history, tidied"
    lines[1] = json.dumps(rec, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n")
    report = verify_chain(tmp_path / "run")
    assert not report["ok"] and report["breaks"]


def test_deleted_line_breaks_chain(tmp_path):
    _emit_run(tmp_path / "run")
    path = tmp_path / "run" / "events.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0]] + lines[2:]) + "\n")
    assert not verify_chain(tmp_path / "run")["ok"]


def test_governance_timeline_selects_governance_events(tmp_path):
    log = EventLog(tmp_path / "run", echo=False)
    log.emit("model_turn", role="worker")                  # noise
    log.emit("consent_granted", agent="implementer")
    log.emit("ownership_denied", agent="bob", path="a.txt")
    log.emit("gate_verdict", attempt=1, passed=True)
    log.close()
    kinds = [e["kind"] for e in governance_timeline(tmp_path / "run")]
    assert "consent_granted" in kinds and "ownership_denied" in kinds
    assert "model_turn" not in kinds


def test_audit_cli_exit_codes(tmp_path):
    run_dir = tmp_path / "runs" / "r1"
    _emit_run(run_dir)
    assert main(["--root", str(tmp_path), "audit", "r1"]) == 0
    # tamper
    path = run_dir / "events.jsonl"
    lines = path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["detail"] = "x"
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")
    assert main(["--root", str(tmp_path), "audit", "r1"]) == 1
    assert main(["--root", str(tmp_path), "audit", "nope"]) == 2
