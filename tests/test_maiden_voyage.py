"""0.8 maiden voyages: new phase contracts stage before operator promotion."""

import json
import textwrap

from harness import sandbox
from harness.cli import main
from harness.init_project import init_project
from harness.inward_manifest import verify_inward_manifest
from harness.models.base import MockModel, ModelSpec
from harness.runner import WorkflowRunner

from test_runner import scaffold_project, turn_tool


def _workflow(root, task="Create result.txt for {goal}"):
    path = root / "workflows" / "maiden.yaml"
    path.write_text(textwrap.dedent(f"""
        name: maiden
        phases:
          - name: implement
            phase_type: artifact-builder
            agent: implementer
            task: "{task}"
          - name: integrate
            agent: orchestrator
            task: "Summarize: {{implement}}"
    """), encoding="utf-8")
    return path


def _events(root, run_id):
    return [
        json.loads(line)
        for line in (root / "runs" / run_id / "events.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _proposal_script(content="proposed"):
    return [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "result.txt", "content": content}),
        turn_tool("task_complete", {"report": f"wrote {content}"}),
    ]


def _runner(root, run_id, script):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    brain = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=script,
    )
    runner._models["mid"] = brain
    return runner, brain


def test_new_phase_type_stages_verified_output_without_applying(
        tmp_path, monkeypatch):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, brain = _runner(tmp_path, "voyage", _proposal_script())

    outcomes = runner.run_workflow(workflow, goal="g")

    assert [outcome.status for outcome in outcomes] == ["needs_approval"]
    assert not (tmp_path / "workspace" / "result.txt").exists()
    proposals = list(
        (tmp_path / "runs" / "voyage" / "maiden").glob("*/proposal.json"))
    assert len(proposals) == 1
    proposal = json.loads(proposals[0].read_text(encoding="utf-8"))
    staged = next(
        (tmp_path / ".maiden" / "voyage")
        .glob("*/workspace/result.txt"))
    assert staged.read_text(encoding="utf-8") == "proposed"
    assert proposal["phase"] == "implement"
    assert proposal["phase_type"] == "artifact-builder"
    assert len(proposal["fingerprint"]) == 64
    assert len(brain.calls) == 3
    events = _events(tmp_path, "voyage")
    assert any(event["kind"] == "maiden_proposed" for event in events)
    assert not any(event["kind"] == "maiden_approved" for event in events)


def test_operator_approval_promotes_exact_stage_and_resume_skips_worker(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")

    code = main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"])

    assert code == 0
    assert "approved maiden output" in capsys.readouterr().out
    assert (tmp_path / "workspace" / "result.txt").read_text() == "proposed"
    events = _events(tmp_path, "voyage")
    assert any(event["kind"] == "maiden_approved" for event in events)

    resumed, brain = _runner(
        tmp_path, "voyage",
        [turn_tool("task_complete", {"report": "FINAL"})])
    outcomes = resumed.run_workflow(workflow, goal="g")
    assert [outcome.status for outcome in outcomes] == [
        "skipped_resume", "passed"]
    assert len(brain.calls) == 1


def test_approved_auto_claim_preserves_inward_policy_integrity(
        tmp_path, monkeypatch):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    init_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")

    assert main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"]) == 0

    result = verify_inward_manifest(
        tmp_path, tmp_path / "INWARD_MANIFEST.yaml")
    assert result.ok, result.problems


def test_approved_phase_contract_runs_normally_in_future_run(
        tmp_path, monkeypatch):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    first, _ = _runner(tmp_path, "first", _proposal_script("first"))
    first.run_workflow(workflow, goal="g")
    assert main([
        "--root", str(tmp_path), "approve-maiden", "first", "implement"]) == 0

    second, _ = _runner(
        tmp_path, "second",
        _proposal_script("second")
        + [turn_tool("task_complete", {"report": "FINAL"})])
    outcomes = second.run_workflow(workflow, goal="g")

    assert [outcome.status for outcome in outcomes] == ["passed", "passed"]
    assert (tmp_path / "workspace" / "result.txt").read_text() == "second"
    assert not (tmp_path / "runs" / "second" / "maiden").exists()


def test_changed_phase_contract_requires_new_maiden(
        tmp_path, monkeypatch):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    first, _ = _runner(tmp_path, "first", _proposal_script("first"))
    first.run_workflow(workflow, goal="g")
    assert main([
        "--root", str(tmp_path), "approve-maiden", "first", "implement"]) == 0

    changed = _workflow(tmp_path, task="Create a changed result for {goal}")
    second, _ = _runner(tmp_path, "changed", _proposal_script("changed"))
    outcomes = second.run_workflow(changed, goal="g")

    assert [outcome.status for outcome in outcomes] == ["needs_approval"]
    assert (tmp_path / "workspace" / "result.txt").read_text() == "first"


def test_workspace_drift_refuses_promotion_without_partial_apply(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")
    (tmp_path / "workspace" / "operator.txt").write_text(
        "newer work", encoding="utf-8")

    code = main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"])

    assert code == 2
    assert "workspace changed after the proposal" in capsys.readouterr().err
    assert not (tmp_path / "workspace" / "result.txt").exists()
    assert (tmp_path / "workspace" / "operator.txt").read_text() == "newer work"
    assert not any(
        event["kind"] == "maiden_approved"
        for event in _events(tmp_path, "voyage"))


def test_tampered_staged_output_refuses_promotion(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")
    staged = next(
        (tmp_path / ".maiden" / "voyage")
        .glob("*/workspace/result.txt"))
    staged.write_text("tampered", encoding="utf-8")

    code = main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"])

    assert code == 2
    assert "changed after verification" in capsys.readouterr().err
    assert not (tmp_path / "workspace" / "result.txt").exists()


def test_broken_audit_chain_refuses_promotion(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")
    events_path = tmp_path / "runs" / "voyage" / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"seq": 1', '"seq": 99')
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    code = main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"])

    assert code == 2
    assert "audit chain is broken" in capsys.readouterr().err
    assert not (tmp_path / "workspace" / "result.txt").exists()


def test_ownership_drift_refuses_promotion(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sandbox, "wrap",
        lambda argv, workspace, allow_network=False: argv)
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    runner, _ = _runner(tmp_path, "voyage", _proposal_script())
    runner.run_workflow(workflow, goal="g")
    (tmp_path / "OWNERSHIP.yaml").write_text(
        "lanes:\n  operator: ['new/*']\nfiles: {}\n", encoding="utf-8")

    code = main([
        "--root", str(tmp_path), "approve-maiden", "voyage", "implement"])

    assert code == 2
    assert "ownership ledger changed" in capsys.readouterr().err
    assert not (tmp_path / "workspace" / "result.txt").exists()


def test_invalid_phase_type_refuses_before_model_dispatch(tmp_path):
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            "artifact-builder", "Invalid phase type!"),
        encoding="utf-8")
    runner, brain = _runner(tmp_path, "invalid", [])

    outcomes = runner.run_workflow(workflow, goal="g")

    assert [outcome.status for outcome in outcomes] == ["needs_human"]
    assert brain.calls == []
    assert any(
        event["kind"] == "workflow_config_invalid"
        for event in _events(tmp_path, "invalid"))


def test_parallel_maiden_refuses_before_any_group_dispatch(tmp_path):
    scaffold_project(tmp_path)
    workflow = _workflow(tmp_path)
    text = workflow.read_text(encoding="utf-8").replace(
        "phase_type: artifact-builder",
        "phase_type: artifact-builder\n    parallel: workers")
    workflow.write_text(text, encoding="utf-8")
    runner, brain = _runner(tmp_path, "parallel-invalid", [])

    outcomes = runner.run_workflow(workflow, goal="g")

    assert [outcome.status for outcome in outcomes] == ["needs_human"]
    assert brain.calls == []
    assert not (tmp_path / "workspace" / ".phases").exists()
