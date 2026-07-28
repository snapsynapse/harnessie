"""0.8 inward manifest: the run records or refuses harness drift."""

import json
import textwrap
from pathlib import Path

from harness.cli import main
from harness.inward_manifest import (
    discover_inward_files,
    render_inward_manifest,
    verify_inward_manifest,
)
from harness.init_project import init_project
from harness.models.base import MockModel, ModelSpec
from harness.runner import WorkflowRunner

from test_runner import scaffold_project, turn_tool


ROOT = Path(__file__).resolve().parents[1]


def _events(root, run_id):
    return [
        json.loads(line)
        for line in (root / "runs" / run_id / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]


def _one_phase(root):
    (root / "workflows" / "integrity.yaml").write_text(textwrap.dedent("""
        name: integrity
        phases:
          - name: plan
            agent: orchestrator
            task: "Report the plan for {goal}"
    """))


def _runner(root, run_id="integrity"):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    brain = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=[turn_tool("task_complete", {"report": "clean"})],
    )
    runner._models["mid"] = brain
    return runner, brain


def test_shipped_inward_manifest_verifies_and_covers_runtime_inputs():
    result = verify_inward_manifest(ROOT, ROOT / "INWARD_MANIFEST.yaml")

    assert result.ok, result.problems
    assert result.policy == "refuse"
    assert set(result.files) == set(discover_inward_files(ROOT))
    assert "agents/orchestrator.md" in result.files
    assert "config/models.yaml" in result.files
    assert "OWNERSHIP.yaml" in result.files


def test_cli_verify_inward_manifest(capsys):
    code = main(["--root", str(ROOT), "verify-inward-manifest"])
    out = capsys.readouterr().out

    assert code == 0
    assert "inward manifest OK" in out


def test_manifest_detects_tampered_prompt(tmp_path):
    scaffold_project(tmp_path)
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_text(render_inward_manifest(tmp_path), encoding="utf-8")
    (tmp_path / "agents" / "orchestrator.md").write_text(
        "# Orchestrator\nChanged.", encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert not result.ok
    assert any("sha256 mismatch for agents/orchestrator.md" in problem
               for problem in result.problems)


def test_manifest_detects_unpinned_new_config(tmp_path):
    scaffold_project(tmp_path)
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_text(render_inward_manifest(tmp_path), encoding="utf-8")
    (tmp_path / "config" / "new-policy.yaml").write_text(
        "enabled: true\n", encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert not result.ok
    assert any("unpinned inward file: config/new-policy.yaml" == problem
               for problem in result.problems)


def test_ownership_auto_claims_do_not_invalidate_static_policy(tmp_path):
    scaffold_project(tmp_path)
    ownership = tmp_path / "OWNERSHIP.yaml"
    ownership.write_text(
        "lanes:\n  agent: {}\n  collaborative: []\n  operator: []\n"
        "files: {}\n", encoding="utf-8")
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_text(render_inward_manifest(tmp_path), encoding="utf-8")
    ownership.write_text(
        "lanes:\n  agent: {}\n  collaborative: []\n  operator: []\n"
        "files:\n  generated.txt: implementer\n", encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert result.ok, result.problems


def test_ownership_lane_change_invalidates_static_policy(tmp_path):
    scaffold_project(tmp_path)
    ownership = tmp_path / "OWNERSHIP.yaml"
    ownership.write_text(
        "lanes:\n  agent: {}\n  collaborative: []\n  operator: []\n"
        "files: {}\n", encoding="utf-8")
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_text(render_inward_manifest(tmp_path), encoding="utf-8")
    ownership.write_text(
        "lanes:\n  agent: {}\n  collaborative: []\n"
        "  operator: ['protected/*']\nfiles: {}\n", encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert not result.ok
    assert any("sha256 mismatch for OWNERSHIP.yaml" in problem
               for problem in result.problems)


def test_present_malformed_manifest_fails_closed(tmp_path):
    scaffold_project(tmp_path)
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_text("files: [", encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert not result.ok
    assert result.policy == "refuse"
    assert any("not valid YAML" in problem for problem in result.problems)


def test_structurally_invalid_record_manifest_still_refuses(tmp_path):
    scaffold_project(tmp_path)
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    text = render_inward_manifest(tmp_path, policy="record").replace(
        "kind: harnessie-inward-manifest", "kind: unknown")
    manifest.write_text(text, encoding="utf-8")

    result = verify_inward_manifest(tmp_path, manifest)

    assert not result.ok
    assert result.policy == "refuse"
    assert f"manifest kind must be harnessie-inward-manifest" in result.problems


def test_missing_manifest_preserves_legacy_runner_behavior(tmp_path):
    scaffold_project(tmp_path)
    _one_phase(tmp_path)
    runner, brain = _runner(tmp_path, "legacy")

    outcomes = runner.run_workflow(
        tmp_path / "workflows" / "integrity.yaml", goal="g")

    assert [outcome.status for outcome in outcomes] == ["passed"]
    assert len(brain.calls) == 1
    assert "inward_manifest_verified" not in {
        event["kind"] for event in _events(tmp_path, "legacy")
    }


def test_init_project_writes_valid_fail_closed_manifest(tmp_path):
    written = init_project(tmp_path)

    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    assert manifest in written
    result = verify_inward_manifest(tmp_path, manifest)
    assert result.ok, result.problems
    assert result.policy == "refuse"


def test_refuse_policy_halts_before_model_dispatch_on_drift(tmp_path):
    scaffold_project(tmp_path)
    _one_phase(tmp_path)
    (tmp_path / "INWARD_MANIFEST.yaml").write_text(
        render_inward_manifest(tmp_path, policy="refuse"), encoding="utf-8")
    (tmp_path / "agents" / "orchestrator.md").write_text(
        "# Orchestrator\nDrifted.", encoding="utf-8")
    runner, brain = _runner(tmp_path, "refuse")

    outcomes = runner.run_workflow(
        tmp_path / "workflows" / "integrity.yaml", goal="g")

    assert [outcome.status for outcome in outcomes] == ["needs_human"]
    assert outcomes[0].phase == "(integrity)"
    assert "inward manifest divergence" in outcomes[0].report
    assert brain.calls == []
    events = _events(tmp_path, "refuse")
    assert [event["kind"] for event in events] == [
        "inward_manifest_refused",
    ]


def test_record_policy_runs_and_records_drift_before_workflow_start(tmp_path):
    scaffold_project(tmp_path)
    _one_phase(tmp_path)
    (tmp_path / "INWARD_MANIFEST.yaml").write_text(
        render_inward_manifest(tmp_path, policy="record"), encoding="utf-8")
    (tmp_path / "agents" / "orchestrator.md").write_text(
        "# Orchestrator\nIntentional local override.", encoding="utf-8")
    runner, brain = _runner(tmp_path, "record")

    outcomes = runner.run_workflow(
        tmp_path / "workflows" / "integrity.yaml", goal="g")

    assert [outcome.status for outcome in outcomes] == ["passed"]
    assert len(brain.calls) == 1
    events = _events(tmp_path, "record")
    kinds = [event["kind"] for event in events]
    assert "inward_manifest_divergence" in kinds
    assert kinds.index("inward_manifest_divergence") < kinds.index("workflow_start")


def test_clean_run_records_manifest_and_workflow_hash(tmp_path):
    scaffold_project(tmp_path)
    _one_phase(tmp_path)
    (tmp_path / "INWARD_MANIFEST.yaml").write_text(
        render_inward_manifest(tmp_path), encoding="utf-8")
    runner, _ = _runner(tmp_path, "clean")

    outcomes = runner.run_workflow(
        tmp_path / "workflows" / "integrity.yaml", goal="g")

    assert [outcome.status for outcome in outcomes] == ["passed"]
    events = _events(tmp_path, "clean")
    verified = next(
        event for event in events
        if event["kind"] == "inward_manifest_verified")
    started = next(event for event in events if event["kind"] == "workflow_start")
    assert len(verified["manifest_sha256"]) == 64
    assert verified["files"] == len(discover_inward_files(tmp_path))
    assert len(started["workflow_sha256"]) == 64
