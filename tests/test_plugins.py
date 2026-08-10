import json

import pytest

from harness import plugins
from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.plugins import (AdmittedPlugin, PluginDeclaration, PluginError,
                             register_plugins, resolve_plugins,
                             verify_resume_plugins)
from harness.tools.registry import PermissionDenied, ToolRegistry, ToolSpec
from harness.runner import WorkflowRunner
from test_runner import scaffold_project


class FakeEntryPoint:
    group = plugins.ENTRY_POINT_GROUP

    def __init__(self, name, value, loaded):
        self.name = name
        self.value = value
        self._loaded = loaded
        self.loads = 0

    def load(self):
        self.loads += 1
        return self._loaded


def declaration(name="acme", version="1.0.0", **tool_overrides):
    values = {
        "name": "lookup",
        "description": "lookup",
        "parameters": {"type": "object", "properties": {}},
        "fn": lambda: "ok",
        "allowed_roles": frozenset({"worker"}),
    }
    values.update(tool_overrides)
    return PluginDeclaration(
        name=name,
        version=version,
        tools=(ToolSpec(**values),),
    )


def test_only_explicitly_selected_entry_point_loads(monkeypatch):
    acme = FakeEntryPoint("acme", "acme:plugin", declaration())
    idle = FakeEntryPoint("idle", "idle:plugin", declaration(name="idle"))
    monkeypatch.setattr(plugins, "_entry_points", lambda: [acme, idle])

    admitted = resolve_plugins(["acme"])

    assert [plugin.name for plugin in admitted] == ["acme"]
    assert acme.loads == 1
    assert idle.loads == 0


def test_no_selection_does_not_enumerate_installed_entry_points(monkeypatch):
    def unexpected_discovery():
        raise AssertionError("installed plugins must not affect an unextended run")

    monkeypatch.setattr(plugins, "_entry_points", unexpected_discovery)
    assert resolve_plugins([]) == ()


def test_admission_namespaces_tool_and_loader_supplies_provenance(monkeypatch):
    point = FakeEntryPoint("acme", "acme:plugin", declaration())
    monkeypatch.setattr(plugins, "_entry_points", lambda: [point])
    registry = ToolRegistry()

    register_plugins(registry, resolve_plugins(["acme"]))

    assert registry.dispatch("worker", "acme__lookup", {}).content == "ok"
    assert registry.provenance_for("acme__lookup") == "plugin:acme@1.0.0"
    with pytest.raises(PermissionDenied):
        registry.dispatch("verifier", "acme__lookup", {})


def test_plugin_invocation_audits_loader_supplied_provenance(monkeypatch, tmp_path):
    point = FakeEntryPoint("acme", "acme:plugin", declaration())
    monkeypatch.setattr(plugins, "_entry_points", lambda: [point])
    registry = ToolRegistry()
    register_plugins(registry, resolve_plugins(["acme"]))
    model = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=[
            AssistantTurn(content="", tool_calls=[ToolCall(
                "p", "acme__lookup", {})]),
            AssistantTurn(content="", tool_calls=[ToolCall(
                "d", "task_complete", {"report": "done"})]),
        ],
    )
    events = EventLog(tmp_path / "run", echo=False)

    AgentLoop("worker", model, registry, events, max_steps=3).run("system", "task")

    rows = [json.loads(line) for line in
            (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    result = next(row for row in rows
                  if row.get("kind") == "tool_result"
                  and row.get("tool") == "acme__lookup")
    assert result["provenance"] == "plugin:acme@1.0.0"


@pytest.mark.parametrize("selected,error", [
    (["missing"], "unknown plugin"),
    (["acme", "acme"], "selected only once"),
])
def test_unknown_or_duplicate_selection_fails_closed(monkeypatch, selected, error):
    point = FakeEntryPoint("acme", "acme:plugin", declaration())
    monkeypatch.setattr(plugins, "_entry_points", lambda: [point])
    with pytest.raises(PluginError, match=error):
        resolve_plugins(selected)


def test_malformed_declaration_fails_closed(monkeypatch):
    point = FakeEntryPoint("acme", "acme:plugin", declaration(name="renamed"))
    monkeypatch.setattr(plugins, "_entry_points", lambda: [point])
    with pytest.raises(PluginError, match="does not match"):
        resolve_plugins(["acme"])


def test_invalid_parameter_schema_fails_closed(monkeypatch):
    point = FakeEntryPoint(
        "acme", "acme:plugin",
        declaration(parameters={"type": "object", "properties": []}))
    monkeypatch.setattr(plugins, "_entry_points", lambda: [point])
    with pytest.raises(PluginError, match="invalid parameter schema"):
        resolve_plugins(["acme"])


def test_registry_rejects_plugin_without_object_schema():
    plugin = AdmittedPlugin(
        name="acme", version="1", entry_point="acme:plugin",
        tools=(ToolSpec(
            name="acme__bad", description="bad", parameters={},
            fn=lambda: "bad", provenance="plugin:acme@1"),),
    )
    with pytest.raises(ValueError, match="JSON object schema"):
        register_plugins(ToolRegistry(), [plugin])


def test_resume_requires_exact_recorded_plugin_receipt(tmp_path):
    events = tmp_path / "events.jsonl"
    plugin = AdmittedPlugin(
        name="acme", version="1", entry_point="acme:plugin",
        tools=(ToolSpec(
            name="acme__lookup", description="lookup",
            parameters={"type": "object"}, fn=lambda: "ok",
            provenance="plugin:acme@1"),),
    )
    events.write_text(json.dumps({
        "kind": "plugin_set_admitted",
        "plugins": [plugin.receipt()],
    }) + "\n", encoding="utf-8")

    verify_resume_plugins(events, [plugin])
    changed = AdmittedPlugin(
        name="acme", version="2", entry_point="acme:plugin", tools=plugin.tools)
    with pytest.raises(PluginError, match="differs from the original"):
        verify_resume_plugins(events, [changed])


def test_runner_records_plugin_set_and_registers_selected_tools(tmp_path):
    scaffold_project(tmp_path)
    plugin = AdmittedPlugin(
        name="acme", version="1", entry_point="acme:plugin",
        tools=(ToolSpec(
            name="acme__lookup", description="lookup",
            parameters={"type": "object"}, fn=lambda: "ok",
            allowed_roles=frozenset({"worker"}),
            provenance="plugin:acme@1"),),
    )

    runner = WorkflowRunner(
        project_root=tmp_path, run_id="plugin-run", echo=False,
        plugins=(plugin,))

    assert runner.registry.dispatch("worker", "acme__lookup", {}).content == "ok"
    rows = [json.loads(line) for line in
            (tmp_path / "runs" / "plugin-run" / "events.jsonl")
            .read_text().splitlines()]
    assert rows[0]["kind"] == "plugin_set_admitted"
    assert rows[0]["plugins"] == [plugin.receipt()]
