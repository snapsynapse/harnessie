"""ATIF export: a truthful trajectory from a verified event log, or a refusal."""

import json

import pytest

from harness import __version__
from harness.atif import (
    ATIF_SCHEMA_VERSION,
    AtifExportError,
    build_trajectory,
    export_dir,
    write_trajectory,
)
from harness.cli import main
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def _call(idx, name, **args):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=f"c{idx}", name=name, arguments=args)],
                         input_tokens=100 + idx, output_tokens=10 + idx)


def run_loop(tmp_path, script, *, goal=None):
    run_dir = tmp_path / "run"
    events = EventLog(run_dir, echo=False)
    if goal is not None:
        events.emit("workflow_start", name="wf", run_id="RUN1", goal=goal)
    reg = ToolRegistry()
    workspace = tmp_path / "ws"
    workspace.mkdir(exist_ok=True)
    (workspace / "a.txt").write_text("alpha\n", encoding="utf-8")
    register_builtin(reg, workspace=workspace)
    model = MockModel(ModelSpec(name="local", provider="mock", model_id="mock-brain"),
                      script=list(script))
    loop = AgentLoop(role="worker", model=model, registry=reg, events=events,
                     max_steps=6, agent_name="implementer")
    result = loop.run("system", "task", effort="low")
    events.close()
    return run_dir, result


SCRIPT = [
    _call(1, "bash", command="ls"),
    _call(2, "list_files"),
    _call(3, "task_complete", report="done"),
]


def test_export_renders_agent_steps_with_matched_observations(tmp_path):
    run_dir, result = run_loop(tmp_path, SCRIPT)
    assert result.stop == "complete"

    doc = export_dir(run_dir)

    assert doc["schema_version"] == ATIF_SCHEMA_VERSION
    assert doc["session_id"] == "run"
    assert doc["agent"] == {"name": "harnessie", "version": __version__,
                            "model_name": "mock-brain",
                            "extra": {"roles": ["worker"]}}
    assert [s["step_id"] for s in doc["steps"]] == [1, 2, 3]
    assert all(s["source"] == "agent" for s in doc["steps"])
    # Every observation result points at a tool call declared in its own step.
    for step in doc["steps"]:
        declared = {tc["tool_call_id"] for tc in step.get("tool_calls", [])}
        for res in step.get("observation", {}).get("results", []):
            assert res["source_call_id"] in declared
    first = doc["steps"][0]
    assert first["tool_calls"] == [{"tool_call_id": "c1", "function_name": "bash",
                                    "arguments": {},
                                    "extra": {"arguments_recorded": False}}]
    refused = first["observation"]["results"][0]
    assert refused["extra"]["ok"] is False
    assert refused["extra"]["refusal"] == {"error": "action_unsupported",
                                           "boundary": "allowlist"}
    assert first["metrics"] == {"prompt_tokens": 101, "completion_tokens": 11}
    assert first["model_name"] == "mock-brain"
    assert first["reasoning_effort"] == "low"
    assert first["llm_call_count"] == 1
    last = doc["steps"][2]
    assert last["observation"]["results"][0]["content"] == "loop ended: task_complete"
    assert last["observation"]["results"][0]["source_call_id"] == "c3"
    metrics = doc["final_metrics"]
    assert metrics["total_steps"] == 3
    assert metrics["total_prompt_tokens"] == 101 + 102 + 103
    assert metrics["total_completion_tokens"] == 11 + 12 + 13
    assert metrics["extra"]["loops"] == [
        {"loop": 1, "role": "worker", "stop": "complete", "steps": 3,
         "event_seq": metrics["extra"]["loops"][0]["event_seq"]}]
    assert doc["extra"]["chain_verified"] is True


def test_workflow_goal_becomes_the_first_user_step(tmp_path):
    run_dir, _ = run_loop(tmp_path, SCRIPT, goal="make alpha beta")
    doc = export_dir(run_dir)
    assert doc["session_id"] == "RUN1"
    assert doc["steps"][0] == {
        "step_id": 1, "source": "user", "message": "make alpha beta",
        "timestamp": doc["steps"][0]["timestamp"],
        "extra": {"event_seq": 1}}
    assert [s["step_id"] for s in doc["steps"]] == [1, 2, 3, 4]


def test_legacy_single_token_total_is_reported_not_split():
    events = [
        {"ts": 1.0, "seq": 1, "kind": "model_turn", "role": "worker", "step": 1,
         "tool_calls": ["list_files"], "tokens": 50},
        {"ts": 1.1, "seq": 2, "kind": "tool_result", "tool": "list_files",
         "ok": True, "content": "a.txt"},
        {"ts": 1.2, "seq": 3, "kind": "model_turn", "role": "worker", "step": 2,
         "tool_calls": ["task_complete"], "tokens": 20},
        {"ts": 1.3, "seq": 4, "kind": "task_complete", "role": "worker", "step": 2},
        {"ts": 1.4, "seq": 5, "kind": "loop_finished", "role": "worker",
         "stop": "complete", "steps": 2},
    ]
    doc = build_trajectory(events, session_id="legacy")
    step = doc["steps"][0]
    assert step["metrics"] == {"extra": {"total_tokens": 50, "split_recorded": False}}
    # Pairing by order when the log carries no call ids.
    assert step["tool_calls"][0]["tool_call_id"] == "seq1-call1"
    assert step["observation"]["results"][0]["source_call_id"] == "seq1-call1"
    assert "total_prompt_tokens" not in doc["final_metrics"]
    assert doc["final_metrics"]["extra"]["total_tokens"] == 70


def test_broken_chain_is_refused(tmp_path):
    run_dir, _ = run_loop(tmp_path, SCRIPT)
    path = run_dir / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace('"ok": false', '"ok": true')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(AtifExportError) as excinfo:
        export_dir(run_dir)
    assert excinfo.value.code == "chain_broken"


def test_unfinished_loop_is_refused(tmp_path):
    run_dir, _ = run_loop(tmp_path, SCRIPT)
    path = run_dir / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    # Dropping the tail keeps the chain valid but leaves the loop open.
    assert json.loads(lines[-1])["kind"] == "loop_finished"
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(AtifExportError) as excinfo:
        export_dir(run_dir)
    assert excinfo.value.code == "loop_unfinished"


def test_step_sequence_gap_is_refused():
    events = [
        {"ts": 1.0, "seq": 1, "kind": "model_turn", "role": "worker", "step": 1,
         "tool_calls": [], "tokens": 1},
        {"ts": 1.1, "seq": 2, "kind": "model_turn", "role": "worker", "step": 3,
         "tool_calls": [], "tokens": 1},
        {"ts": 1.2, "seq": 3, "kind": "loop_finished", "role": "worker",
         "stop": "no_action", "steps": 3},
    ]
    with pytest.raises(AtifExportError) as excinfo:
        build_trajectory(events, session_id="gap")
    assert excinfo.value.code == "step_sequence"


def test_no_model_turns_is_refused():
    with pytest.raises(AtifExportError) as excinfo:
        build_trajectory([{"ts": 1.0, "seq": 1, "kind": "check", "passed": True}],
                         session_id="empty")
    assert excinfo.value.code == "no_model_turns"


def test_write_refuses_to_overwrite_without_force(tmp_path):
    run_dir, _ = run_loop(tmp_path, SCRIPT)
    written = write_trajectory(run_dir)
    assert written == (run_dir / "trajectory.json").resolve()
    assert json.loads(written.read_text())["schema_version"] == ATIF_SCHEMA_VERSION
    with pytest.raises(AtifExportError) as excinfo:
        write_trajectory(run_dir)
    assert excinfo.value.code == "output_exists"
    assert write_trajectory(run_dir, force=True) == written


def test_cli_exports_a_directory_and_fails_closed_on_second_write(tmp_path, capsys):
    run_dir, _ = run_loop(tmp_path, SCRIPT)
    assert main(["--root", str(tmp_path), "atif", str(run_dir)]) == 0
    assert (run_dir / "trajectory.json").exists()
    assert main(["--root", str(tmp_path), "atif", str(run_dir)]) == 2
    assert "output_exists" in capsys.readouterr().err
    assert main(["--root", str(tmp_path), "atif", "no-such-run"]) == 2


def test_cli_exports_a_run_id_under_runs(tmp_path):
    runs = tmp_path / "runs" / "R-abc"
    runs.mkdir(parents=True)
    events = EventLog(runs, echo=False)
    events.emit("model_turn", role="worker", step=1, tool_calls=[], tokens=3)
    events.emit("loop_finished", role="worker", stop="no_action", steps=1)
    events.close()
    assert main(["--root", str(tmp_path), "atif", "R-abc"]) == 0
    assert (runs / "trajectory.json").exists()


def test_export_validates_against_harbor_models_when_available(tmp_path):
    harbor_models = pytest.importorskip("harbor.models.trajectories")
    run_dir, _ = run_loop(tmp_path, SCRIPT, goal="validate me")
    doc = export_dir(run_dir)
    trajectory = harbor_models.Trajectory.model_validate(doc)
    assert trajectory.schema_version == ATIF_SCHEMA_VERSION
