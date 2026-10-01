"""Rehearse a frozen pilot with scripted models. No live execution mode exists.

Uses the real runner, journal, export and reference lint. Scripted positions
exercise mechanics only and cannot become evidence for the decision itself.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from harness.aidr_export import export_aidr
from harness.audit import verify_chain
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner
from scripts.pilot_contract import PilotRefusal, QUESTION, RECEIPT_VERSION
from scripts.pilot_prepare import verify_packet

RUN_ID = "pilot-rehearsal"
EXPORT_NAME = "AIDR-9999-scripted-pilot-rehearsal.md"


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PilotRefusal(code)


def _forbidden(*args, **kwargs):
    raise PilotRefusal("live_execution_forbidden")


def _mock(root: Path, seal: str, tier: str, agree: bool = False) -> MockModel:
    position = json.dumps({"stance": "recommend" if tier == "frontier" or agree else "oppose",
                           "summary": "SCRIPTED fixture position, not a live opinion."})
    objection = json.dumps({"objections": [] if agree else ["SCRIPTED: demonstrate dissent preservation."],
                            "no_new_objection": agree})
    reports = ["SCRIPTED ONLY. See evidence/tests/test_bidding.py.\n" + position,
               "SCRIPTED ONLY. See evidence/harness/routing.py.\n" + objection]
    calls = 0

    def respond(messages):
        nonlocal calls
        verify_packet(root, seal)
        calls += 1
        if calls > 4:
            raise PilotRefusal("mock_call_limit")
        if calls % 2:
            return AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
                ToolCall(f"{tier}-{calls}", "read_file", {"path": "evidence-index.json"})])
        _require(any(m.role == "tool" and m.name == "read_file" for m in messages), "missing_tool_roundtrip")
        return AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
            ToolCall(f"{tier}-{calls}", "task_complete", {"report": reports[calls // 2 - 1]})])

    return MockModel(ModelSpec(tier, "mock", "scripted-" + tier), fn=respond)


def _review(root: Path, seal: str, *, resume: bool = False, agree: bool = False) -> tuple[str, int]:
    verify_packet(root, seal)
    # Cover construction too: later preflight changes must not add provider I/O.
    with patch("harness.runner.build_model", _forbidden), \
            patch("socket.socket.connect", _forbidden), patch("socket.create_connection", _forbidden):
        runner = WorkflowRunner(root, run_id=RUN_ID, echo=False)
        models = {name: _mock(root, seal, name, agree) for name in ("frontier", "local")}
        if resume:
            for model in models.values():
                model.fn = _forbidden
        runner._models.update(models)
        try:
            outcomes = runner.run_workflow(root / "workflows/review.yaml", goal=QUESTION)
            _require(len(outcomes) == 1, "unexpected_phase_count")
            return outcomes[0].status, sum(len(m.calls) for m in models.values())
        finally:
            runner.events.close()


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def rehearse(root: Path, seal: str, *, agree: bool = False) -> dict:
    root = root.absolute()
    verify_packet(root, seal)
    run_dir = root / "runs" / RUN_ID
    if run_dir.exists():
        raise PilotRefusal("rehearsal_exists")
    status, calls = _review(root, seal, agree=agree)
    _require(status == "needs_arbitration", "human_halt_missing")
    verify_packet(root, seal)
    before = _snapshot(run_dir)
    # Export into its own root below runtime output, preserving the sealed input inventory.
    export_root = run_dir / "export-rehearsal"
    copied = export_root / "runs" / RUN_ID
    shutil.copytree(run_dir, copied, ignore=shutil.ignore_patterns("export-rehearsal"))
    (export_root / "decisions").mkdir()
    copied_before = _snapshot(copied)
    exported = export_aidr(export_root, RUN_ID, "decide", "decisions/" + EXPORT_NAME, "Sam Rogers")
    _require(exported["status"] == "exported", "export_failed")
    _require(_snapshot(copied) == copied_before, "export_changed_source")
    original_after = {name: digest for name, digest in _snapshot(run_dir).items()
                      if not name.startswith("export-rehearsal/")}
    _require(before == original_after, "export_changed_original")
    output = export_root / "decisions" / EXPORT_NAME
    text = output.read_text()
    _require(not text.split("## Arbitration\n")[1].split("## Evidence")[0].strip(), "arbitration_not_empty")
    # Reuse the shipped demo's pinned reference verification, not an unpinned external linter.
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("pilot_reference_demo", repo / "examples/aidr-export/demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    lint = demo.check_reference(repo / "tests/fixtures/aidr-0.1.0")
    node = shutil.which("node")
    _require(node is not None, "reference_lint_unavailable")
    result = subprocess.run([node, str(lint), str(output)], capture_output=True, text=True, timeout=20)
    _require(result.returncode == 0 and "PASS " in result.stdout, "reference_lint_failed")
    record_bytes = (run_dir / "decisions/DR-decide.md").read_bytes()
    resumed, resume_calls = _review(root, seal, resume=True)
    _require(resumed == "needs_arbitration" and resume_calls == 0, "resume_bypassed_human")
    _require(record_bytes == (run_dir / "decisions/DR-decide.md").read_bytes(), "resume_changed_record")
    verify_packet(root, seal)
    chain = verify_chain(run_dir)
    _require(chain["ok"], "invalid_chain")
    events = (run_dir / "events.jsonl").read_text().splitlines()
    receipt = {"schema": RECEIPT_VERSION, "status": "passed", "mode": "scripted_mock_only",
               "live_model_calls": 0, "mock_model_calls": calls, "resume_model_calls": resume_calls,
               "initial_status": status, "resume_status": resumed, "manifest_sha256": seal,
               "input_hashes_unchanged": True, "chain": chain,
               "chain_head": hashlib.sha256(events[-1].encode()).hexdigest(),
               "export_path": output.relative_to(root).as_posix(),
               "export_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
               "reference_lint": "passed", "agreement_fixture": agree,
               "cost_usd": None, "usage_evidence": "scripted calls, no provider usage",
               "limitations": ["no live participant opinions", "no model entitlement proof",
                               "no human arbitration", "no public Claude transport support"]}
    (run_dir / "preparation-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seal", required=True)
    args = parser.parse_args()
    try:
        result = rehearse(args.root, args.seal)
    except PilotRefusal as exc:
        print(json.dumps({"status": "refused", "code": exc.code}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
