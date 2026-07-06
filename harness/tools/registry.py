"""Tool registry: the single source of truth for capabilities AND policy.

Every tool declares:
  - a JSON-schema signature (what the model sees),
  - an effects class: "read" | "write" | "execute" (what it can do),
  - which roles may call it (deny by default),
  - whether a human must approve each call.

The registry enforces policy at dispatch time. An agent cannot call a tool it
was never granted, no matter what its prompt says — permissioning lives in the
harness, not in prompt cleverness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..quarantine import guard_result


class PermissionDenied(Exception):
    pass


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict                       # JSON schema for arguments
    fn: Callable[..., Any]
    effects: str = "read"                  # "read" | "write" | "execute"
    allowed_roles: frozenset[str] = frozenset({"orchestrator", "worker", "verifier"})
    requires_approval: bool = False
    role_aware: bool = False               # fn also receives _role=<calling role>
    quarantine: bool = False               # result runs the injection filter


@dataclass
class ToolResult:
    ok: bool
    content: str
    tool_name: str = ""
    flags: list[str] = field(default_factory=list)   # injection-filter findings


@dataclass
class ToolRegistry:
    tools: dict[str, ToolSpec] = field(default_factory=dict)
    # approval_handler decides interactive approvals. Default denies, so a
    # misconfigured headless run fails closed instead of mutating silently.
    approval_handler: Callable[[str, dict], bool] = field(
        default=lambda tool, args: False
    )

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self.tools:
            raise ValueError(f"Duplicate tool name: {spec.name}")
        if spec.effects not in ("read", "write", "execute"):
            raise ValueError(f"{spec.name}: bad effects class {spec.effects!r}")
        self.tools[spec.name] = spec

    def for_role(self, role: str) -> list[ToolSpec]:
        return [t for t in self.tools.values() if role in t.allowed_roles]

    def schemas(self, role: str) -> list[dict]:
        """Neutral tool schemas for the model adapter — only tools this role
        is permitted to call. The model never sees tools it cannot use."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.for_role(role)
        ]

    def dispatch(self, role: str, name: str, args: dict,
                 allow_network: bool = False) -> ToolResult:
        spec = self.tools.get(name)
        if spec is None:
            return ToolResult(ok=False, tool_name=name,
                              content=f"unknown tool {name!r}")
        if role not in spec.allowed_roles:
            raise PermissionDenied(f"role {role!r} may not call {name!r}")
        if "_malformed" in args:
            return ToolResult(ok=False, tool_name=name,
                              content=f"malformed tool arguments: {args['_malformed']!r}. "
                                      "Re-send with valid JSON matching the schema.")
        if spec.requires_approval and not self.approval_handler(name, args):
            return ToolResult(ok=False, tool_name=name,
                              content="approval denied by operator policy")
        try:
            out = (spec.fn(**args, _role=role, _allow_network=allow_network)
                   if spec.role_aware else spec.fn(**args))
        except TypeError as e:
            return ToolResult(ok=False, tool_name=name,
                              content=f"bad arguments: {e}")
        except Exception as e:  # tool bugs become observations, not crashes
            return ToolResult(ok=False, tool_name=name,
                              content=f"tool error: {type(e).__name__}: {e}")
        content, flags = str(out), []
        if spec.quarantine:
            # Registry-level, so no role prompt can opt out: flagged content
            # is invisibles-stripped and fenced as data-not-instructions.
            content, flags = guard_result(content, source=name)
        return ToolResult(ok=True, tool_name=name, content=content, flags=flags)
