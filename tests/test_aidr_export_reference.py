"""Acceptance against the pinned AIDR reference, using real mock-run records."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest
import yaml

from harness.evals import _run_scripted_workflow, _scaffold_eval_project


REFERENCE = Path(__file__).parent / "fixtures" / "aidr-0.1.0"


def test_pinned_reference_bytes():
    provenance = json.loads((REFERENCE / "provenance.json").read_text())
    assert provenance["revision"] == "a67c41d339d3e70bc3baaf07e652f9cf9d13a5bb"
    assert provenance["spec_version"] == "0.1.0"
    for name, digest in provenance["files"].items():
        assert hashlib.sha256((REFERENCE / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("stance", ["recommend", "oppose"])
def test_actual_runner_record_exports_with_reference_lint(tmp_path, monkeypatch, stance):
    from harness.aidr_export import export_aidr
    from harness.runner import WorkflowRunner

    _scaffold_eval_project(tmp_path, max_attempts=1, adversarial=True)
    first = 'FIRST_POSITION\n{"stance":"recommend","summary":"Proceed."}'
    second = 'SECOND_POSITION\n' + json.dumps({"stance": stance, "summary": "Second."})
    objection = "Specific risk: resuming could lose evidence."
    reports = [first, second,
               json.dumps({"objections": [], "no_new_objection": True}),
               json.dumps({"objections": [objection], "no_new_objection": False})]
    script = [{"tool": "task_complete", "args": {"report": r}} for r in reports]
    assert _run_scripted_workflow(tmp_path, "R", script,
                                 "Adopt the proposed export contract?",
                                 workflow="adv.yaml") == ["needs_arbitration"]
    (tmp_path / "decisions").mkdir()
    before = {p.relative_to(tmp_path): p.read_bytes()
              for p in (tmp_path / "runs").rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("export attempted network or runner construction")

    with monkeypatch.context() as m:
        m.setattr(WorkflowRunner, "__init__", forbidden)
        m.setattr(socket.socket, "connect", forbidden)
        result = export_aidr(root=tmp_path, run_id="R", phase="decide",
                             output="decisions/AIDR-9999-synthetic-export.md",
                             arbiter="synthetic-human-tester")
    output = tmp_path / result["output"]
    text = output.read_text()
    assert result["status"] == "exported"
    assert result["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert first in text and second in text and objection in text
    assert "- agent: implementer\n" in text
    assert "- agent: implementer-2\n" in text
    assert yaml.safe_load(text.split("---\n", 2)[1])["status"] == "open"
    assert "decided_by:" not in text
    assert text.split("## Arbitration\n", 1)[1].split("## Evidence", 1)[0].strip() == ""
    assert {p.relative_to(tmp_path): p.read_bytes()
            for p in (tmp_path / "runs").rglob("*") if p.is_file()} == before
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("Node is required for pinned-reference acceptance in CI")
        pytest.skip("Node unavailable: pinned-reference acceptance not established")
    checked = subprocess.run([node, str(REFERENCE / "tools/aidr-lint.mjs"), str(output)],
                             text=True, capture_output=True, check=False)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "PASS" in checked.stdout
    assert "human-arbitrated" not in checked.stdout

    # Export never unlocks the original run. Resume still halts and preserves it.
    assert _run_scripted_workflow(tmp_path, "R", [],
                                 "Adopt the proposed export contract?",
                                 workflow="adv.yaml") == ["needs_arbitration"]
    record = Path("runs/R/decisions/DR-decide.md")
    assert (tmp_path / record).read_bytes() == before[record]
