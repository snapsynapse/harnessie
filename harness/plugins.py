"""Explicit, operator-trusted tool plugin admission.

Only installed ``harnessie.tools.v1`` entry points named by the operator are
loaded. There is deliberately no project-directory discovery and no untrusted
in-process mode.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from importlib import metadata
from typing import Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .tools.registry import ToolRegistry, ToolSpec

ENTRY_POINT_GROUP = "harnessie.tools.v1"
PLUGIN_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
PLUGIN_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


class PluginError(ValueError):
    """A selected plugin could not be admitted safely."""


@dataclass(frozen=True)
class PluginDeclaration:
    name: str
    version: str
    tools: tuple[ToolSpec, ...]


@dataclass(frozen=True)
class AdmittedPlugin:
    name: str
    version: str
    entry_point: str
    tools: tuple[ToolSpec, ...]
    contract_sha256: str = ""

    def receipt(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "entry_point": self.entry_point,
            "tools": [tool.name for tool in self.tools],
            "contract_sha256": self.contract_sha256,
            "trust": "operator-trusted-in-process",
        }


def _entry_points() -> list[metadata.EntryPoint]:
    points = metadata.entry_points()
    selected = (points.select(group=ENTRY_POINT_GROUP)
                if hasattr(points, "select")
                else points.get(ENTRY_POINT_GROUP, []))
    return sorted(selected, key=lambda point: (point.name, point.value))


def discover_plugins() -> dict[str, metadata.EntryPoint]:
    discovered: dict[str, metadata.EntryPoint] = {}
    for point in _entry_points():
        if point.name in discovered:
            raise PluginError(
                f"duplicate {ENTRY_POINT_GROUP} entry point {point.name!r}")
        discovered[point.name] = point
    return discovered


def _declaration(point: metadata.EntryPoint) -> PluginDeclaration:
    try:
        loaded = point.load()
        value = loaded() if callable(loaded) else loaded
    except Exception as exc:
        raise PluginError(
            f"plugin {point.name!r} failed to load: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, PluginDeclaration):
        raise PluginError(
            f"plugin {point.name!r} must return PluginDeclaration")
    return value


def _admit(point: metadata.EntryPoint) -> AdmittedPlugin:
    declaration = _declaration(point)
    if not PLUGIN_NAME.fullmatch(declaration.name):
        raise PluginError(f"plugin name {declaration.name!r} is invalid")
    if declaration.name != point.name:
        raise PluginError(
            f"plugin declaration name {declaration.name!r} does not match "
            f"entry point {point.name!r}")
    if not isinstance(declaration.version, str) \
            or not PLUGIN_VERSION.fullmatch(declaration.version):
        raise PluginError(
            f"plugin {point.name!r} has an invalid immutable version")
    if not isinstance(declaration.tools, tuple) or not declaration.tools:
        raise PluginError(f"plugin {point.name!r} must declare at least one tool")

    tools: list[ToolSpec] = []
    validator = ToolRegistry()
    for spec in declaration.tools:
        if not isinstance(spec, ToolSpec):
            raise PluginError(f"plugin {point.name!r} contains a non-ToolSpec tool")
        if not TOOL_NAME.fullmatch(spec.name):
            raise PluginError(
                f"plugin {point.name!r} tool name {spec.name!r} is invalid")
        public_name = f"{point.name}__{spec.name}"
        if len(public_name) > 64:
            raise PluginError(f"plugin tool name {public_name!r} exceeds 64 characters")
        admitted_spec = replace(
            spec,
            name=public_name,
            provenance=f"plugin:{point.name}@{declaration.version}",
        )
        if not callable(admitted_spec.fn):
            raise PluginError(f"plugin tool {public_name!r} has no callable")
        if not isinstance(admitted_spec.description, str) \
                or not admitted_spec.description.strip():
            raise PluginError(f"plugin tool {public_name!r} has no description")
        if not isinstance(admitted_spec.allowed_roles, frozenset):
            raise PluginError(
                f"plugin tool {public_name!r} allowed_roles must be a frozenset")
        for field_name in ("requires_approval", "role_aware", "quarantine"):
            if not isinstance(getattr(admitted_spec, field_name), bool):
                raise PluginError(
                    f"plugin tool {public_name!r} {field_name} must be boolean")
        try:
            validator.register(admitted_spec)
        except (TypeError, ValueError) as exc:
            raise PluginError(
                f"plugin tool {public_name!r} is invalid: {exc}") from exc
        try:
            Draft202012Validator.check_schema(admitted_spec.parameters)
        except SchemaError as exc:
            raise PluginError(
                f"plugin tool {public_name!r} has an invalid parameter schema: "
                f"{exc.message}") from exc
        tools.append(admitted_spec)
    try:
        contract = json.dumps([
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "effects": tool.effects,
                "allowed_roles": sorted(tool.allowed_roles),
                "requires_approval": tool.requires_approval,
                "role_aware": tool.role_aware,
                "quarantine": tool.quarantine,
            }
            for tool in tools
        ], sort_keys=True, separators=(",", ":"), ensure_ascii=True,
           allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PluginError(
            f"plugin {point.name!r} declaration is not JSON-serializable") from exc
    return AdmittedPlugin(
        name=point.name,
        version=declaration.version,
        entry_point=point.value,
        tools=tuple(tools),
        contract_sha256=hashlib.sha256(contract.encode("utf-8")).hexdigest(),
    )


def resolve_plugins(names: Iterable[str]) -> tuple[AdmittedPlugin, ...]:
    requested = tuple(names)
    if len(set(requested)) != len(requested):
        raise PluginError("a plugin may be selected only once")
    if not requested:
        return ()
    wanted = set(requested)
    points = _entry_points()
    discovered: dict[str, metadata.EntryPoint] = {}
    for point in points:
        if point.name not in wanted:
            continue
        if point.name in discovered:
            raise PluginError(
                f"duplicate {ENTRY_POINT_GROUP} entry point {point.name!r}")
        discovered[point.name] = point
    missing = [name for name in requested if name not in discovered]
    if missing:
        raise PluginError(
            f"unknown plugin(s) {missing!r}; available: "
            f"{sorted({point.name for point in points})}")
    return tuple(_admit(discovered[name]) for name in sorted(requested))


def register_plugins(registry: ToolRegistry,
                     plugins: Iterable[AdmittedPlugin]) -> None:
    for plugin in plugins:
        for tool in plugin.tools:
            registry.register(tool)


def plugin_receipts(plugins: Iterable[AdmittedPlugin]) -> list[dict]:
    return [plugin.receipt() for plugin in plugins]


def verify_resume_plugins(events_path, plugins: Iterable[AdmittedPlugin]) -> None:
    """Refuse plugin-set drift before a resumed run dispatches a model."""
    if not events_path.exists():
        return
    recorded = None
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("kind") == "plugin_set_admitted":
            recorded = event.get("plugins", [])
    current = plugin_receipts(plugins)
    # Runs predating this contract implicitly used no plugins.
    if recorded is None:
        recorded = []
    if recorded != current:
        raise PluginError(
            "resume plugin set differs from the original run: "
            f"recorded={recorded!r}, current={current!r}")
