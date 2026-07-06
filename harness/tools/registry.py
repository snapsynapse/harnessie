"""Tool registry: the single source of truth for capabilities AND policy.

Every tool declares:
  - a JSON-schema signature (what the model sees),
  - an effects class: "read" | "write" | "execute" (what it can do),
  - which roles may call it (deny by default),
  - whether a human must approve each call.

The registry enforces policy at dispatch time. An agent cannot call a tool it
was never granted, no matter what its prompt says — permissioning lives in the
harness, not in prompt cleverness.

v0.2 additions, both enforced here so no role prompt can opt out:
  - consent lock: when a dispatch arrives with side_effects_locked=True (a
    consent-gated phase before accept_task), write/execute tools are refused
    with an explanatory observation. Read tools still run: informed consent
    requires the agent can inspect the workspace before agreeing.
  - agent identity: dispatch carries the agent NAME (e.g. "implementer")
    alongside the role KIND, so ownership checks in tools can tell agents
    apart. role_aware tools receive _role, _agent, and _allow_network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..quarantine import guard_result


class PermissionDenied(Exception):
    def __init__(self, message: str, refusal: "Refusal | None" = None):
        super().__init__(message)
        self.refusal = refusal


@dataclass(frozen=True)
class Refusal:
    error: str
    boundary: str
    detail: str
    why: str

    def content(self) -> str:
        return json.dumps({
            "error": self.error,
            "boundary": self.boundary,
            "detail": self.detail,
            "why": self.why,
        }, separators=(",", ":"))


class ToolRefusal(Exception):
    def __init__(self, error: str, boundary: str, detail: str, why: str):
        self.refusal = Refusal(error=error, boundary=boundary,
                               detail=detail, why=why)
        super().__init__(detail)


def refusal_result(error: str, boundary: str, detail: str, why: str,
                   tool_name: str = "", ok: bool = False) -> "ToolResult":
    refusal = Refusal(error=error, boundary=boundary, detail=detail, why=why)
    return ToolResult(ok=ok, tool_name=tool_name,
                      content=refusal.content(), refusal=refusal)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict                       # JSON schema for arguments
    fn: Callable[..., Any]
    effects: str = "read"                  # "read" | "write" | "execute"
    allowed_roles: frozenset[str] = frozenset({"orchestrator", "worker", "verifier"})
    requires_approval: bool = False
    role_aware: bool = False               # fn also receives _role/_agent/_allow_network
    quarantine: bool = False               # result runs the injection filter


@dataclass
class ToolResult:
    ok: bool
    content: str
    tool_name: str = ""
    flags: list[str] = field(default_factory=list)   # injection-filter findings
    refusal: Refusal | None = None


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

    def side_effect_tools(self) -> frozenset[str]:
        return frozenset(t.name for t in self.tools.values()
                         if t.effects in ("write", "execute"))

    def dispatch(self, role: str, name: str, args: dict,
                 allow_network: bool = False, agent: str = "",
                 side_effects_locked: bool = False) -> ToolResult:
        spec = self.tools.get(name)
        if spec is None:
            return refusal_result(
                "action_unsupported", "allowlist",
                f"Unknown tool {name!r}. Use one of the tools granted to this role.",
                "Tool availability is enforced by the harness, not by model choice.",
                tool_name=name)
        if role not in spec.allowed_roles:
            refusal = Refusal(
                "authority_insufficient", "role",
                f"Role {role!r} may not call {name!r}.",
                "Role permissions keep read, write, and verification authority separate.")
            raise PermissionDenied(refusal.detail, refusal=refusal)
        if side_effects_locked and spec.effects in ("write", "execute"):
            # Consent lock: the task packet is an offer, not a command. Side
            # effects unlock only after accept_task; declining is decline_task.
            return refusal_result(
                "consent_required", "consent",
                f"{name!r} has side effects and this task has not been accepted. "
                "Inspect with read tools if needed, then call accept_task or decline_task.",
                "Task packets are offers; mutation requires explicit worker consent.",
                tool_name=name)
        if "_malformed" in args:
            return refusal_result(
                "malformed_arguments", "phase",
                f"Malformed tool arguments: {args['_malformed']!r}. "
                "Re-send valid JSON matching the schema.",
                "Tool arguments must be machine-parseable before dispatch.",
                tool_name=name)
        if spec.requires_approval and not self.approval_handler(name, args):
            return refusal_result(
                "approval_required", "approval",
                "Operator approval was not granted for this tool call.",
                "Approval-gated tools fail closed unless the operator authorizes them.",
                tool_name=name)
        try:
            out = (spec.fn(**args, _role=role, _agent=agent,
                           _allow_network=allow_network)
                   if spec.role_aware else spec.fn(**args))
        except ToolRefusal as e:
            return ToolResult(ok=False, tool_name=name,
                              content=e.refusal.content(), refusal=e.refusal)
        except TypeError as e:
            return refusal_result(
                "bad_arguments", "phase",
                f"Bad arguments for {name!r}: {e}",
                "Schema-shaped calls still need to match the Python tool signature.",
                tool_name=name)
        except Exception as e:  # tool bugs become observations, not crashes
            return refusal_result(
                "tool_exception", "phase",
                f"Tool {name!r} raised {type(e).__name__}: {e}",
                "Tool failures are surfaced as observations so the loop can fail closed.",
                tool_name=name)
        if isinstance(out, Refusal):
            return ToolResult(ok=True, tool_name=name,
                              content=out.content(), refusal=out)
        content, flags = str(out), []
        if spec.quarantine:
            # Registry-level, so no role prompt can opt out: flagged content
            # is invisibles-stripped and fenced as data-not-instructions.
            content, flags = guard_result(content, source=name)
        return ToolResult(ok=True, tool_name=name, content=content, flags=flags)
