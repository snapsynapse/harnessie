"""Tamper-evident audit: hash-chained events log + audit verb.

Each event carries seq and prev (SHA-256 of the previous serialized line);
an edit, deletion, or reorder of an interior line breaks the next link.
Tamper-evident, not tamper-proof. The chain is unanchored: an edit to the
final event and a truncated suffix leave a valid shorter chain, and whole-file
rewrites are out of scope. Detecting those needs a terminal digest and count
held somewhere the log writer cannot reach (SEC-20261118-019); the limit tests
below pin that behavior so a claim cannot silently outgrow it.
"""

import json

from harness.audit import governance_timeline, verify_chain
from harness.cli import main
from harness.events import EventLog, line_hash


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


def _lines(run_dir):
    return (run_dir / "events.jsonl").read_text().splitlines()


def test_interior_edit_is_detected_at_the_next_link(tmp_path):
    _emit_run(tmp_path / "run", kinds=("a", "b", "c", "d"))
    path = tmp_path / "run" / "events.jsonl"
    lines = _lines(tmp_path / "run")
    rec = json.loads(lines[1])
    rec["detail"] = "history, tidied"
    lines[1] = json.dumps(rec, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n")
    report = verify_chain(tmp_path / "run")
    assert report["ok"] is False and report["breaks"] == [3]


def test_edited_final_event_is_not_detected_by_the_chain_alone(tmp_path):
    # Pinned limitation: no later line links to the final event's hash.
    _emit_run(tmp_path / "run")
    path = tmp_path / "run" / "events.jsonl"
    lines = _lines(tmp_path / "run")
    rec = json.loads(lines[-1])
    rec["detail"] = "history, tidied"
    lines[-1] = json.dumps(rec, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n")
    assert verify_chain(tmp_path / "run") == {"ok": True, "length": 3, "breaks": []}


def test_suffix_truncation_is_not_detected_by_the_chain_alone(tmp_path):
    # Pinned limitation: a prefix of a valid chain is itself a valid chain.
    _emit_run(tmp_path / "run")
    path = tmp_path / "run" / "events.jsonl"
    lines = _lines(tmp_path / "run")
    path.write_text("\n".join(lines[:2]) + "\n")
    assert verify_chain(tmp_path / "run") == {"ok": True, "length": 2, "breaks": []}
    path.write_text("")
    assert verify_chain(tmp_path / "run") == {"ok": True, "length": 0, "breaks": []}


def test_missing_log_is_not_a_clean_chain(tmp_path):
    (tmp_path / "run").mkdir()
    report = verify_chain(tmp_path / "run")
    assert report["ok"] is False and report["length"] == 0


def test_separately_held_terminal_digest_exposes_tail_changes(tmp_path):
    # What closes the gap: a terminal count and digest recorded outside the
    # log's trust boundary. The harness does not store one beside the log,
    # because a writer who can edit the log could edit that copy too.
    _emit_run(tmp_path / "run")
    path = tmp_path / "run" / "events.jsonl"
    original = _lines(tmp_path / "run")
    trusted = (len(original), line_hash(original[-1]))

    def terminal():
        lines = _lines(tmp_path / "run")
        return (len(lines), line_hash(lines[-1]) if lines else None)

    assert terminal() == trusted
    rec = json.loads(original[-1])
    rec["detail"] = "history, tidied"
    path.write_text("\n".join([*original[:-1], json.dumps(rec)]) + "\n")
    assert verify_chain(tmp_path / "run")["ok"] and terminal() != trusted
    path.write_text("\n".join(original[:2]) + "\n")
    assert verify_chain(tmp_path / "run")["ok"] and terminal() != trusted


def test_resume_extends_a_valid_chain_positive_control(tmp_path):
    _emit_run(tmp_path / "run", kinds=("a", "b"))
    log = EventLog(tmp_path / "run", echo=False)
    log.emit("c", detail="after-resume")
    log.close()
    lines = _lines(tmp_path / "run")
    assert json.loads(lines[-1])["prev"] == line_hash(lines[-2])
    assert verify_chain(tmp_path / "run") == {"ok": True, "length": 3, "breaks": []}


def test_governance_timeline_selects_governance_events(tmp_path):
    log = EventLog(tmp_path / "run", echo=False)
    log.emit("model_turn", role="worker")                  # noise
    log.emit("consent_granted", agent="implementer")
    log.emit("ownership_denied", agent="bob", path="a.txt")
    log.emit("refusal", role="worker", agent="bob", tool="write_file",
             error="ownership_denied", boundary="ownership")
    log.emit("gate_verdict", attempt=1, passed=True)
    log.close()
    kinds = [e["kind"] for e in governance_timeline(tmp_path / "run")]
    assert "consent_granted" in kinds and "ownership_denied" in kinds
    assert "refusal" in kinds
    assert "model_turn" not in kinds


def test_governance_timeline_includes_blast_radius_events(tmp_path):
    log = EventLog(tmp_path / "run", echo=False)
    log.emit("blast_radius_usage", phase="build", phase_files=1)
    log.emit("blast_radius_exceeded", phase="build", scope="phase",
             counter="max_files_touched", count=2, limit=1)
    log.close()

    kinds = [event["kind"] for event in governance_timeline(tmp_path / "run")]

    assert "blast_radius_usage" in kinds
    assert "blast_radius_exceeded" in kinds


def test_governance_timeline_includes_operator_and_memory_events(tmp_path):
    # v0.3 claim: operator actions and memory maintenance are IN the rendered
    # audit timeline, same stream as agent actions — not just in the raw log.
    log = EventLog(tmp_path / "run", echo=False)
    for kind in ("approval_granted", "approval_denied", "operator_action",
                 "fact_saved", "fact_expired"):
        log.emit(kind, detail=f"x-{kind}")
    log.close()
    kinds = [e["kind"] for e in governance_timeline(tmp_path / "run")]
    for kind in ("approval_granted", "approval_denied", "operator_action",
                 "fact_saved", "fact_expired"):
        assert kind in kinds, f"{kind} missing from governance timeline"


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
