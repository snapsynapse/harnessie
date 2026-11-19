"""SEC-20261118-007: tool results are contained before ANY event emission or
model input. A recognized credential or structured PII in a read_file,
read_evidence, plugin or run_shell result must reach no run artifact and no
captured model request; refusal events carry safe kind labels only.

Canaries are synthetic. Every artifact under the run directory and every
message the mock model received is inspected, not only the stop status.
"""

import json
from types import MappingProxyType

import pytest

from harness.boundary import Boundary, StripMap
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
import harness.tools.builtin as builtin
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRefusal, ToolRegistry, ToolSpec
from harness.verify_evidence import EvidenceBundle, register_evidence_reader

SECRET = "pplx-" + "SYNTHETICCANARY" * 3
PII = "canary-person@example.invalid"
OFFSETS = [0, 150, 290]


def _payload(canary: str, offset: int) -> str:
    return "x" * offset + canary + " trailing ordinary text\n"


def _script(tool: str, args: dict) -> list[AssistantTurn]:
    return [
        AssistantTurn(content="", stop_reason="tool_use",
                      tool_calls=[ToolCall("c1", tool, args)]),
        AssistantTurn(content="", stop_reason="tool_use",
                      tool_calls=[ToolCall("c2", "task_complete",
                                           {"report": "done"})]),
    ]


def _run(tmp_path, registry, tool, args, role="worker", boundary=True):
    model = MockModel(ModelSpec("m", "mock", "m"), script=_script(tool, args))
    run_dir = tmp_path / "run"
    events = EventLog(run_dir, echo=False)
    try:
        result = AgentLoop(
            role=role, model=model, registry=registry, events=events,
            boundary=Boundary() if boundary else None,
            strip_map=StripMap.open(tmp_path / "op", "r") if boundary else None,
        ).run("system", "inspect the input")
    finally:
        events.close()
    artifacts = "".join(p.read_text(encoding="utf-8", errors="replace")
                        for p in run_dir.rglob("*") if p.is_file())
    model_inputs = "\n".join(m.content for call in model.calls
                             for m in call["messages"])
    records = [json.loads(line) for line in
               (run_dir / "events.jsonl").read_text().splitlines()]
    return result, artifacts, model_inputs, records


def _workspace_registry(tmp_path, text):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "fixture.txt").write_text(text, encoding="utf-8")
    reg = ToolRegistry()
    register_builtin(reg, workspace=ws)
    return reg


def _evidence_registry(tmp_path, text):
    path = tmp_path / "evidence.txt"
    path.write_text(text, encoding="utf-8")
    reg = ToolRegistry()
    register_evidence_reader(reg, EvidenceBundle(
        source=tmp_path / "bundle.yaml", evidence_root=tmp_path, data={},
        files={"ev1": path},
        snapshots=MappingProxyType({"ev1": path.read_bytes()})))
    return reg


def _plugin_registry(tmp_path, text):
    reg = ToolRegistry()
    reg.register(ToolSpec(
        name="lookup", description="plugin lookup",
        parameters={"type": "object", "properties": {}},
        fn=lambda: text, provenance="plugin:audit-fixture@0.0.1"))
    return reg


SOURCES = {
    "read_file": (_workspace_registry, "read_file", {"path": "fixture.txt"}, "worker"),
    "read_evidence": (_evidence_registry, "read_evidence", {"evidence_id": "ev1"},
                      "verifier"),
    "plugin": (_plugin_registry, "lookup", {}, "worker"),
}


@pytest.mark.parametrize("offset", OFFSETS)
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_secret_result_halts_without_reaching_events_or_model(tmp_path, source, offset):
    make, tool, args, role = SOURCES[source]
    reg = make(tmp_path, _payload(SECRET, offset))
    result, artifacts, model_inputs, records = _run(tmp_path, reg, tool, args, role)
    assert result.stop == "secret_egress"
    assert SECRET not in artifacts
    assert SECRET not in model_inputs
    assert SECRET not in result.report
    tool_results = [r for r in records if r["kind"] == "tool_result"]
    assert tool_results and tool_results[0].get("withheld") == "secret_egress"
    halts = [r for r in records if r["kind"] == "secret_egress_halt"]
    assert halts and halts[0]["kinds"] == ["perplexity_key"]


@pytest.mark.parametrize("offset", OFFSETS)
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_pii_result_is_stripped_before_events_and_model(tmp_path, source, offset):
    make, tool, args, role = SOURCES[source]
    reg = make(tmp_path, _payload(PII, offset))
    result, artifacts, model_inputs, _ = _run(tmp_path, reg, tool, args, role)
    assert result.stop == "complete"
    assert PII not in artifacts
    assert PII not in model_inputs
    assert "[EMAIL_1]" in model_inputs


@pytest.mark.parametrize("offset", OFFSETS)
def test_shell_output_secret_and_pii_never_logged(tmp_path, monkeypatch, offset):
    monkeypatch.setattr(builtin, "sandbox_wrap",
                        lambda argv, workspace, allow_network=False: argv)
    reg = _workspace_registry(tmp_path, _payload(SECRET + " " + PII, offset))
    result, artifacts, model_inputs, _ = _run(
        tmp_path, reg, "run_shell", {"command": "cat fixture.txt"})
    assert result.stop == "complete"
    for canary in (SECRET, PII):
        assert canary not in artifacts
        assert canary not in model_inputs


@pytest.mark.parametrize("canary", [SECRET, PII])
def test_refusal_detail_is_contained_before_refusal_event(tmp_path, canary):
    def refuse():
        raise ToolRefusal("plugin_refused", "plugin",
                          f"upstream said: {canary}", "fixture refusal")
    reg = ToolRegistry()
    reg.register(ToolSpec(name="lookup", description="plugin lookup",
                          parameters={"type": "object", "properties": {}},
                          fn=refuse, provenance="plugin:audit-fixture@0.0.1"))
    result, artifacts, model_inputs, records = _run(tmp_path, reg, "lookup", {})
    assert canary not in artifacts
    assert canary not in model_inputs
    refusals = [r for r in records if r["kind"] == "refusal"]
    assert refusals and refusals[0]["error"] == "plugin_refused"
    assert refusals[0]["boundary"] == "plugin"


def test_tool_exception_message_is_contained(tmp_path):
    def boom():
        raise ValueError(f"config value {SECRET}")
    reg = ToolRegistry()
    reg.register(ToolSpec(name="lookup", description="plugin lookup",
                          parameters={"type": "object", "properties": {}},
                          fn=boom, provenance="plugin:audit-fixture@0.0.1"))
    result, artifacts, model_inputs, records = _run(tmp_path, reg, "lookup", {})
    assert result.stop == "secret_egress"
    assert SECRET not in artifacts
    assert SECRET not in model_inputs
    refusals = [r for r in records if r["kind"] == "refusal"]
    assert refusals and refusals[0]["error"] == "tool_exception"


@pytest.mark.parametrize("source", sorted(SOURCES))
def test_boundary_off_still_keeps_secrets_out_of_events_and_model(tmp_path, source):
    make, tool, args, role = SOURCES[source]
    reg = make(tmp_path, _payload(SECRET, 10))
    result, artifacts, model_inputs, _ = _run(
        tmp_path, reg, tool, args, role, boundary=False)
    assert result.stop == "complete"
    assert SECRET not in artifacts
    assert SECRET not in model_inputs
    assert "[REDACTED-SECRET]" in model_inputs


def test_boundary_off_keeps_pii_byte_identical(tmp_path):
    reg = _workspace_registry(tmp_path, _payload(PII, 0))
    result, artifacts, model_inputs, _ = _run(
        tmp_path, reg, "read_file", {"path": "fixture.txt"}, boundary=False)
    assert result.stop == "complete"
    assert PII in model_inputs          # boundary off: PII is not stripped


def test_clean_result_reaches_model_unchanged(tmp_path):
    text = "ordinary project notes\nnothing sensitive here\n"
    reg = _workspace_registry(tmp_path, text)
    result, artifacts, model_inputs, records = _run(
        tmp_path, reg, "read_file", {"path": "fixture.txt"})
    assert result.stop == "complete"
    assert text in model_inputs
    tool_results = [r for r in records if r["kind"] == "tool_result"]
    assert tool_results[0]["content"] == text[:300]
    assert "withheld" not in tool_results[0]
