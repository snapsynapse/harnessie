import json

from harness.explain import (
    format_report,
    format_run_summary,
    halt_next_action,
    plain_status,
)


def test_plain_status_translates_known_statuses():
    assert plain_status("passed") == "completed"
    assert plain_status("needs_human") == "stopped and is waiting for you"
    assert plain_status("needs_arbitration").startswith("stopped")
    # unknown status passes through rather than raising
    assert plain_status("weird") == "weird"


def test_halt_next_action_names_a_command_for_needs_human():
    action = halt_next_action("needs_human", "R1", "workflows/x.yaml", "build")
    assert action is not None
    assert "harnessie resume R1 workflows/x.yaml" in action
    assert "build" in action


def test_halt_next_action_points_at_the_decision_record_for_arbitration():
    action = halt_next_action("needs_arbitration", "R1", "workflows/x.yaml", "decide")
    assert "runs/R1/decisions/" in action
    assert "arbitrated" in action
    assert "harnessie resume R1 workflows/x.yaml" in action


def test_halt_next_action_is_none_for_success():
    assert halt_next_action("passed", "R1", "w.yaml", "p") is None
    assert halt_next_action("skipped_resume", "R1", "w.yaml", "p") is None


def test_run_summary_success_has_no_next_action():
    summary = format_run_summary(
        "R1", "w.yaml", [("plan", "passed"), ("build", "passed")], 0.12, 3400)
    assert "completed" in summary
    assert "What to do" not in summary
    assert "$0.1200" in summary


def test_run_summary_halt_leads_with_outcome_and_names_action():
    summary = format_run_summary(
        "R1", "w.yaml", [("plan", "passed"), ("build", "needs_human")], 0.05, 900)
    assert "stopped and is waiting for you" in summary
    assert "harnessie resume R1 w.yaml" in summary
    # the halted phase is named
    assert "build" in summary


def _write_events(run_dir, events):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_format_report_missing_run(tmp_path):
    out = format_report(tmp_path / "runs" / "nope")
    assert "No run found" in out


def test_format_report_completed_run(tmp_path):
    run_dir = tmp_path / "runs" / "R1"
    _write_events(run_dir, [
        {"kind": "workflow_start", "name": "build-and-verify", "run_id": "R1",
         "goal": "make a thing", "workflow": "workflows/bv.yaml"},
        {"kind": "phase_done", "phase": "plan", "status": "passed", "spent_usd": 0.02},
        {"kind": "phase_done", "phase": "build", "status": "passed", "spent_usd": 0.09},
        {"kind": "workflow_done", "run_id": "R1", "spent_usd": 0.09},
    ])
    out = format_report(run_dir)
    assert "build-and-verify" in out
    assert "make a thing" in out
    assert "Outcome: completed" in out
    assert "plan: completed" in out
    assert "harnessie audit R1" in out
    assert "What to do" not in out


def test_format_report_halted_run_names_next_action(tmp_path):
    run_dir = tmp_path / "runs" / "R2"
    _write_events(run_dir, [
        {"kind": "workflow_start", "name": "bv", "run_id": "R2",
         "workflow": "workflows/bv.yaml"},
        {"kind": "phase_done", "phase": "plan", "status": "passed", "spent_usd": 0.02},
        {"kind": "phase_done", "phase": "build", "status": "needs_human", "spent_usd": 0.04},
        # note: no workflow_done — the run halted
    ])
    out = format_report(run_dir)
    assert 'stopped and is waiting for you at "build"' in out
    assert "harnessie resume R2 workflows/bv.yaml" in out
    assert "harnessie audit R2" in out


def test_format_report_crashed_before_any_phase(tmp_path):
    run_dir = tmp_path / "runs" / "R3"
    _write_events(run_dir, [
        {"kind": "workflow_start", "name": "bv", "run_id": "R3",
         "workflow": "workflows/bv.yaml"},
    ])
    out = format_report(run_dir)
    assert "no completed phases" in out
