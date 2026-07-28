"""0.8 blast-radius ceilings: bounded, atomic workspace mutation."""

import json
import textwrap

from harness import sandbox
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner
from harness.tools import builtin

from test_runner import scaffold_project, turn_tool


def _events(root, run_id):
    return [
        json.loads(line)
        for line in (root / "runs" / run_id / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]


def _brain(root, run_id, script):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    brain = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=list(script),
    )
    runner._models["mid"] = brain
    return runner, brain


def test_phase_file_ceiling_rolls_back_breaching_write_and_halts(tmp_path):
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Write two files"
            blast_radius:
              max_files_touched: 1
              max_edits_applied: 10
              max_bytes_written: 100
    """))
    runner, brain = _brain(tmp_path, "filecap", [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "kept.txt", "content": "kept"}),
        turn_tool("write_file", {"path": "rolled-back.txt", "content": "no"}),
        turn_tool("task_complete", {"report": "must not run"}),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["needs_human"]
    assert "max_files_touched=2 exceeded limit 1" in outcomes[0].report
    assert (tmp_path / "workspace" / "kept.txt").read_text() == "kept"
    assert not (tmp_path / "workspace" / "rolled-back.txt").exists()
    assert len(brain.calls) == 3
    exceeded = [e for e in _events(tmp_path, "filecap")
                if e["kind"] == "blast_radius_exceeded"]
    assert len(exceeded) == 1
    assert exceeded[0]["scope"] == "phase"
    assert exceeded[0]["counter"] == "max_files_touched"
    assert exceeded[0]["count"] == 2
    assert exceeded[0]["limit"] == 1


def test_phase_byte_ceiling_restores_previous_file_content(tmp_path):
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Rewrite one file"
            blast_radius:
              max_files_touched: 10
              max_edits_applied: 10
              max_bytes_written: 5
    """))
    runner, _ = _brain(tmp_path, "bytecap", [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "result.txt", "content": "ok"}),
        turn_tool("write_file", {"path": "result.txt", "content": "toolong"}),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["needs_human"]
    assert "max_bytes_written=9 exceeded limit 5" in outcomes[0].report
    assert (tmp_path / "workspace" / "result.txt").read_text() == "ok"


def test_shell_artifacts_are_rolled_back_atomically_on_ceiling_breach(
        tmp_path, monkeypatch):
    monkeypatch.setattr(builtin, "sandbox_wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Create files through shell"
            blast_radius:
              max_files_touched: 1
              max_edits_applied: 10
              max_bytes_written: 100
    """))
    runner, _ = _brain(tmp_path, "shellcap", [
        turn_tool("accept_task", {}),
        turn_tool("run_shell", {
            "command": "python3 -c \"open('a.txt','w').write('a');"
                       "open('b.txt','w').write('b')\"",
        }),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["needs_human"]
    assert not (tmp_path / "workspace" / "a.txt").exists()
    assert not (tmp_path / "workspace" / "b.txt").exists()


def test_verification_check_artifacts_are_rolled_back_and_do_not_retry(
        tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Finish without worker writes"
            blast_radius:
              max_files_touched: 1
              max_edits_applied: 10
              max_bytes_written: 100
            verify:
              max_attempts: 3
              checks:
                - name: writes-two
                  command: python3 -c "open('a.txt','w').write('a');open('b.txt','w').write('b')"
    """))
    runner, brain = _brain(tmp_path, "checkcap", [
        turn_tool("accept_task", {}),
        turn_tool("task_complete", {"report": "ready for checks"}),
        turn_tool("task_complete", {"report": "must not retry"}),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["needs_human"]
    assert "max_files_touched=2 exceeded limit 1" in outcomes[0].report
    assert not (tmp_path / "workspace" / "a.txt").exists()
    assert not (tmp_path / "workspace" / "b.txt").exists()
    assert len(brain.calls) == 2


def test_workflow_ceiling_aggregates_successful_phase_writes(tmp_path):
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        blast_radius:
          max_files_touched: 1
          max_edits_applied: 10
          max_bytes_written: 100
        phases:
          - name: first
            agent: implementer
            task: "Write first"
            blast_radius:
              max_files_touched: 1
          - name: second
            agent: implementer
            task: "Write second"
            blast_radius:
              max_files_touched: 1
    """))
    runner, _ = _brain(tmp_path, "runcap", [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "first.txt", "content": "one"}),
        turn_tool("task_complete", {"report": "first done"}),
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "second.txt", "content": "two"}),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    assert (tmp_path / "workspace" / "first.txt").read_text() == "one"
    assert not (tmp_path / "workspace" / "second.txt").exists()
    exceeded = [e for e in _events(tmp_path, "runcap")
                if e["kind"] == "blast_radius_exceeded"]
    assert exceeded[-1]["scope"] == "run"


def test_invalid_ceiling_refuses_before_model_dispatch(tmp_path):
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Never starts"
            blast_radius:
              max_files_touched: -1
    """))
    runner, brain = _brain(tmp_path, "badcap", [])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in outcomes] == ["needs_human"]
    assert "invalid blast_radius" in outcomes[0].report
    assert brain.calls == []


def test_resume_reconstructs_phase_counters_from_audit_events(tmp_path):
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Bounded resumed work"
            blast_radius:
              max_files_touched: 1
              max_edits_applied: 10
              max_bytes_written: 100
    """))
    runner, _ = _brain(tmp_path, "resumecap", [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "first.txt", "content": "one"}),
        turn_tool("decline_task", {"reason": "operator input needed"}),
    ])
    first = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")
    assert [o.status for o in first] == ["needs_human"]

    resumed, _ = _brain(tmp_path, "resumecap", [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "second.txt", "content": "two"}),
    ])
    second = resumed.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [o.status for o in second] == ["needs_human"]
    assert "max_files_touched=2 exceeded limit 1" in second[0].report
    assert (tmp_path / "workspace" / "first.txt").exists()
    assert not (tmp_path / "workspace" / "second.txt").exists()


def test_parallel_phases_share_run_ceiling_without_racing(
        tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        blast_radius:
          max_files_touched: 1
          max_edits_applied: 10
          max_bytes_written: 100
        phases:
          - name: left
            parallel: workers
            agent: implementer
            task: "Write left"
          - name: right
            parallel: workers
            agent: implementer
            task: "Write right"
    """))

    def brain(messages):
        task = messages[1].content
        if messages[-1].name == "accept_task":
            side = "left" if "left" in task else "right"
            return turn_tool(
                "write_file", {"path": f"{side}.txt", "content": side})
        if messages[-1].name == "write_file":
            return turn_tool("task_complete", {"report": "done"})
        return turn_tool("accept_task", {})

    runner = WorkflowRunner(
        project_root=tmp_path, run_id="parallelcap", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), fn=brain)

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    statuses = [outcome.status for outcome in outcomes]
    assert statuses.count("passed") == 1
    assert statuses.count("needs_human") == 1
    created = list((tmp_path / "workspace" / ".phases").rglob("*.txt"))
    assert len(created) == 1
    exceeded = [event for event in _events(tmp_path, "parallelcap")
                if event["kind"] == "blast_radius_exceeded"]
    assert len(exceeded) == 1
    assert exceeded[0]["scope"] == "run"


def test_unmeasurable_special_file_fails_closed_and_rolls_back(
        tmp_path, monkeypatch):
    monkeypatch.setattr(builtin, "sandbox_wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    (tmp_path / "workflows" / "radius.yaml").write_text(textwrap.dedent("""
        name: radius
        phases:
          - name: implement
            agent: implementer
            task: "Create an unsupported artifact"
            blast_radius:
              max_files_touched: 10
    """))
    runner, _ = _brain(tmp_path, "specialcap", [
        turn_tool("accept_task", {}),
        turn_tool("run_shell", {
            "command": "python3 -c \"import os;os.mkfifo('pipe')\"",
        }),
    ])

    outcomes = runner.run_workflow(tmp_path / "workflows" / "radius.yaml")

    assert [outcome.status for outcome in outcomes] == ["needs_human"]
    assert "workspace_measurement=1 exceeded limit 0" in outcomes[0].report
    assert not (tmp_path / "workspace" / "pipe").exists()
