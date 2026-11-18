"""Offline containment audit reproductions, fake data only, no model/network calls.

Run from the Harnessie checkout with its Python environment. A true vulnerable
observation describes the reviewed 6c053dd baseline, not a passing security gate.
All filesystem fixtures are temporary and removed before this script exits.
"""
import json
import os
import tempfile
from pathlib import Path

from harness.boundary import Boundary, StripMap
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.ownership import OwnershipLedger
from harness.quarantine import find_secrets
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def emit(name, **observed):
    print(json.dumps({"probe": name, **observed}, sort_keys=True))


def read_probe(root, text, name):
    ws = root / name
    ws.mkdir()
    (ws / "fixture.txt").write_text(text, encoding="utf-8")
    registry = ToolRegistry()
    register_builtin(registry, workspace=ws)
    model = MockModel(ModelSpec("audit-mock", "mock", "audit-mock"), script=[
        AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
            ToolCall("read", "read_file", {"path": "fixture.txt"})]),
        AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
            ToolCall("done", "task_complete", {"report": "done"})]),
    ])
    run_dir = root / (name + "-run")
    events = EventLog(run_dir, echo=False)
    try:
        result = AgentLoop(
            role="worker", model=model, registry=registry, events=events,
            boundary=Boundary(), strip_map=StripMap.open(root, name),
        ).run("system", "Inspect fixture.txt")
    finally:
        events.close()
    emit(name, stop=result.stop, raw_value_in_events=text in (
        run_dir / "events.jsonl").read_text(encoding="utf-8"),
        mock_model_calls=len(model.calls))


def main():
    with tempfile.TemporaryDirectory(prefix="harnessie-containment-audit-", dir="/private/tmp") as raw:
        root = Path(raw)
        read_probe(root, "pplx-" + "C" * 40, "credential_event_leak")
        read_probe(root, "audit-person@example.invalid", "pii_event_leak")
        ws = root / "links"
        (ws / "frozen").mkdir(parents=True)
        protected = ws / "frozen" / "value.txt"
        protected.write_text("original", encoding="utf-8")
        os.link(protected, ws / "alias.txt")
        external = root / "outside-workspace.txt"
        external.write_text("original", encoding="utf-8")
        os.link(external, ws / "external-alias.txt")
        registry = ToolRegistry()
        register_builtin(registry, workspace=ws, ledger=OwnershipLedger(
            path=root / "OWNERSHIP.yaml", operator=["frozen/*"]))
        results = []
        for alias in ("alias.txt", "external-alias.txt"):
            results.append(registry.dispatch("worker", "write_file", {
                "path": alias, "content": "changed by an otherwise allowed path",
            }, agent="audit-worker"))
        emit("preexisting_hardlink_alias", dispatches_ok=all(r.ok for r in results),
             operator_lane_changed=protected.read_text() != "original",
             outside_workspace_changed=external.read_text() != "original")
        overlapping_canary = "sk-ant-ABCD-" + "2222333344445555"
        recognized = bool(find_secrets(overlapping_canary))
        result = Boundary().guard_egress(overlapping_canary)
        emit("secret_pii_overlap", recognized_before_strip=recognized,
             guard_returned_without_halt=True, mapping_entries=len(result.mapping),
             rehydration_reconstructs_secret=Boundary.rehydrate(
                 result.stripped, result.mapping) == overlapping_canary)


if __name__ == "__main__":
    main()
