"""Offline observer CLI, integrity, privacy and path acceptance contracts."""
import json

import pytest

from harness.events import EventLog




def seed(root, *, finished=True, unknown=False, missing_field=False):
    run = root / "runs" / "R"
    log = EventLog(run, echo=False)
    log.emit("workflow_start", name="wf", run_id="R", goal="CANARY_GOAL_742")
    log.emit("phase_start", phase="work")
    log.emit("tool_result", tool="read_file", content="CANARY_TOOL_742")
    log.emit("model_turn", role="worker", content="CANARY_PROSE_742")
    if unknown:
        log.emit("future_unknown_kind", payload="CANARY_UNKNOWN_742")
    if missing_field:
        log.emit("phase_done", phase="work")
    elif finished:
        log.emit("phase_done", phase="work", status="passed")
        log.emit("workflow_done", run_id="R")
    log.close()
    return run


def invoke(root, run_id="R"):
    from harness import observer  # noqa: F401
    from harness.cli import main
    return main(["--root", str(root), "observe", run_id])


def test_cli_success_creates_artifacts_without_runner(tmp_path, monkeypatch):
    from harness import observer  # noqa: F401
    from harness.runner import WorkflowRunner
    def forbidden(*args, **kwargs):
        raise AssertionError("offline observer invoked workflow runner")
    monkeypatch.setattr(WorkflowRunner, "__init__", forbidden)
    run = seed(tmp_path)
    source = (run / "events.jsonl").read_bytes()
    assert invoke(tmp_path) == 0
    assert (run / "observer" / "narrative.md").is_file()
    result = json.loads((run / "observer" / "narrative.json").read_text())
    assert result["outcome"] == "completed"
    assert result["chain"]["ok"] is True
    assert (run / "events.jsonl").read_bytes() == source


@pytest.mark.parametrize("damage,code", [
    ("missing", "missing_input"), ("broken", "chain_break"),
    ("malformed", "malformed_json"), ("partial", "partial_record"),
    ("field", "invalid_event"),
])
def test_cli_refusal_has_diagnostic_and_no_narrative_claims(tmp_path, capsys, damage, code):
    run = seed(tmp_path, missing_field=damage == "field")
    path = run / "events.jsonl"
    if damage == "missing":
        path.unlink()
    elif damage == "broken":
        path.write_text(path.read_text().replace('"name": "wf"', '"name": "tampered"'))
    elif damage == "malformed":
        path.write_text("not JSON\n")
    elif damage == "partial":
        path.write_bytes(path.read_bytes() + b'{"kind":')
    before = path.read_bytes() if path.exists() else None
    assert invoke(tmp_path) != 0
    captured = capsys.readouterr()
    assert code in captured.err
    assert (path.read_bytes() if path.exists() else None) == before
    output = run / "observer" / "narrative.json"
    if output.exists():
        result = json.loads(output.read_text())
        assert result["phases"] == []
        assert result["outcome"] == "integrity_error"


@pytest.mark.parametrize("escape", ["traversal", "run_symlink", "output_symlink", "file_symlink"])
def test_cli_refuses_path_escape_without_outside_writes(tmp_path, escape, capsys):
    root = tmp_path / "project"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("unchanged")
    run = seed(root)
    run_id = "R"
    if escape == "traversal":
        run_id = "../../outside"
    elif escape == "run_symlink":
        (root / "runs" / "escape").symlink_to(outside, target_is_directory=True)
        run_id = "escape"
    elif escape == "output_symlink":
        (run / "observer").symlink_to(outside, target_is_directory=True)
    else:
        (run / "observer").mkdir()
        (run / "observer" / "narrative.json").symlink_to(sentinel)
    assert invoke(root, run_id) != 0
    assert "unsafe_path" in capsys.readouterr().err
    assert sentinel.read_text() == "unchanged"
    assert sorted(p.name for p in outside.iterdir()) == ["sentinel"]


def test_derived_outputs_omit_raw_payload_canaries(tmp_path):
    run = seed(tmp_path, unknown=True)
    assert invoke(tmp_path) == 0
    for name in ("narrative.json", "narrative.md"):
        content = (run / "observer" / name).read_text()
        for canary in ("CANARY_GOAL_742", "CANARY_TOOL_742", "CANARY_PROSE_742", "CANARY_UNKNOWN_742"):
            assert canary not in content


@pytest.mark.parametrize("finished", [False, True])
def test_unknown_event_does_not_invent_completion(tmp_path, finished):
    run = seed(tmp_path, finished=finished, unknown=True)
    assert invoke(tmp_path) == 0
    result = json.loads((run / "observer" / "narrative.json").read_text())
    assert result["outcome"] == ("completed" if finished else "in_progress")
    assert result["phases"][0]["validation"]["status"] == ("passed" if finished else "in_progress")


def test_cli_never_constructs_a_model(tmp_path, monkeypatch):
    import harness.models as models
    from harness import observer
    def forbidden(*args, **kwargs):
        raise AssertionError("offline observation attempted model construction")
    monkeypatch.setattr(models, "build_model", forbidden)
    seed(tmp_path)
    assert invoke(tmp_path) == 0


def test_halted_workflow_done_does_not_mean_completed(tmp_path):
    from harness.observer import observe_run
    run = seed(tmp_path, finished=False)
    log = EventLog(run, echo=False)
    log.emit("phase_done", phase="work", status="needs_human")
    log.emit("workflow_done", run_id="R", statuses={"work": "needs_human"})
    log.close()
    assert observe_run(run)["outcome"] == "needs_human"


def test_parallel_unattributed_events_are_not_assigned_to_last_phase(tmp_path):
    from harness.observer import observe_run
    run = seed(tmp_path, finished=False)
    log = EventLog(run, echo=False)
    log.emit("phase_start", phase="other")
    log.emit("model_turn", tokens=100)
    log.close()
    result = observe_run(run)
    assert all(p["execution"]["tokens"] == 0 for p in result["phases"])
    assert any(o["id"] == "ambiguous_phase" for o in result["observations"])


def test_failure_replaces_previous_success_with_diagnostic(tmp_path):
    run = seed(tmp_path)
    assert invoke(tmp_path) == 0
    (run / "events.jsonl").write_bytes(b"not JSON\n")
    assert invoke(tmp_path) != 0
    result = json.loads((run / "observer/narrative.json").read_text())
    assert result["outcome"] == "integrity_error"
    assert result["phases"] == []
    assert "completed" not in (run / "observer/narrative.md").read_text()


@pytest.mark.parametrize("kind,payload", [
    ("phase_done", {"phase": "work", "status": []}),
    ("routing_trace", {"agent": "worker", "tier": {}}),
    ("check", {"name": "test", "passed": "false"}),
    ("gate_verdict", {"passed": True, "attempt": True}),
    ("model_turn", {"tokens": -1}),
    ("workflow_done", {"statuses": []}),
])
def test_malformed_known_fields_fail_without_traceback(tmp_path, kind, payload, capsys):
    run = seed(tmp_path, finished=False)
    log = EventLog(run, echo=False)
    log.emit(kind, **payload)
    log.close()
    assert invoke(tmp_path) == 2
    assert "invalid_event" in capsys.readouterr().err


@pytest.mark.parametrize("path_kind", ["source_symlink", "source_hardlink", "output_hardlink", "runs_symlink"])
def test_other_path_aliases_refuse_without_mutation(tmp_path, path_kind, capsys):
    import os
    root = tmp_path / "project"
    run = seed(root)
    source = run / "events.jsonl"
    original = source.read_bytes()
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(original)
    if path_kind == "source_symlink":
        source.unlink()
        source.symlink_to(sentinel)
    elif path_kind == "source_hardlink":
        source.unlink()
        os.link(sentinel, source)
    elif path_kind == "output_hardlink":
        (run / "observer").mkdir()
        os.link(sentinel, run / "observer/narrative.md")
    else:
        (root / "runs").rename(root / "real_runs")
        (root / "runs").symlink_to(root / "real_runs", target_is_directory=True)
    assert invoke(root) == 2
    assert "unsafe_path" in capsys.readouterr().err
    assert sentinel.read_bytes() == original


def test_whitespace_only_journal_is_missing_input(tmp_path, capsys):
    run = seed(tmp_path)
    (run / "events.jsonl").write_bytes(b" \n\n")
    assert invoke(tmp_path) == 2
    assert "missing_input" in capsys.readouterr().err


def test_resume_does_not_inherit_prior_route(tmp_path):
    from harness.observer import observe_run
    run = seed(tmp_path, finished=False)
    log = EventLog(run, echo=False)
    log.emit("routing_trace", agent="worker", tier="mid")
    log.emit("phase_done", phase="work", status="needs_human")
    log.emit("workflow_done", statuses={"work": "needs_human"})
    log.emit("workflow_start", run_id="R")
    log.emit("phase_start", phase="work")
    log.close()
    result = observe_run(run)
    assert result["outcome"] == "in_progress"
    assert result["phases"][0]["origin"]["tier"] is None


def test_bid_rationale_is_not_copied_into_derived_output(tmp_path):
    run = seed(tmp_path, finished=False)
    log = EventLog(run, echo=False)
    log.emit("bid_recorded", phase="work", tier="local", why="CANARY_BID_PROSE_742")
    log.close()
    assert invoke(tmp_path) == 0
    assert "CANARY_BID_PROSE_742" not in (run / "observer/narrative.json").read_text()


def test_duplicate_json_fields_are_rejected_before_chain_check(tmp_path, capsys):
    run = seed(tmp_path)
    source = run / "events.jsonl"
    source.write_text(source.read_text().replace('{"ts":', '{"kind": "injected", "ts":', 1))
    assert invoke(tmp_path) == 2
    assert "malformed_json" in capsys.readouterr().err


def test_journal_replacement_during_render_refuses_publication(tmp_path, monkeypatch, capsys):
    from harness import observer
    run = seed(tmp_path)
    source = run / "events.jsonl"
    original_render = observer.render_narrative
    def replace_source(result):
        replacement = run / "replacement.jsonl"
        replacement.write_bytes(source.read_bytes())
        replacement.replace(source)
        return original_render(result)
    monkeypatch.setattr(observer, "render_narrative", replace_source)
    assert invoke(tmp_path) == 2
    assert "source_changed" in capsys.readouterr().err
    assert not (run / "observer/narrative.json").exists()
