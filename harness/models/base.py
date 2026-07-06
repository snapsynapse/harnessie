"""Brain-agnostic model interface.

The whole harness talks to models through ModelInterface.complete(). Provider
differences (message shape, tool-call encoding, effort/reasoning knobs) live in
adapters. Swapping Fable 5 for GLM, Qwen, or a local vLLM endpoint changes
config, not harness code.

Effort is a first-class request parameter because it is the main quality/cost
dial on frontier Claude models. Adapters map it to whatever their provider
supports (thinking budget, reasoning_effort, or nothing).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Callable

# Matches the official Claude 5 effort scale (output_config.effort). Other
# providers map coarser; adapters own the translation.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


@dataclass
class ModelSpec:
    """One named model endpoint from config/models.yaml."""

    name: str                    # config key, e.g. "frontier"
    provider: str                # "anthropic" | "openai-compat" | "mock"
    model_id: str                # e.g. "claude-fable-5", "glm-5.2", "qwen3-coder"
    base_url: str = ""           # required for openai-compat
    api_key_env: str = ""        # env var holding the key; never store keys in config
    max_tokens: int = 8192
    supports_effort: bool = True
    cost_per_mtok_in: float = 0.0    # USD, for budget accounting
    cost_per_mtok_out: float = 0.0
    extra: dict = field(default_factory=dict)  # provider-specific passthrough


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: str                    # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""       # set on role="tool" results
    name: str = ""               # tool name on role="tool" results


@dataclass
class AssistantTurn:
    """Normalized model response: text, tool calls, and usage accounting."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # "end_turn" | "tool_use" | "max_tokens" | "error"
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ModelInterface(abc.ABC):
    """The one seam between harness and brain."""

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec

    @abc.abstractmethod
    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        effort: str = "medium",
    ) -> AssistantTurn:
        """One model call. `tools` is a list of JSON-schema tool definitions in
        the neutral format produced by ToolRegistry.schemas(). Adapters convert
        to provider wire format. Must never raise on model refusals or soft
        errors — encode those in stop_reason so the loop's retry policy owns
        the decision."""


class MockModel(ModelInterface):
    """Deterministic model for tests and dry runs.

    Feed it a script: a list of AssistantTurn (or a callable messages->turn).
    Exhausting the script returns a plain 'done' turn, so loops terminate.
    """

    def __init__(self, spec: ModelSpec, script: list[AssistantTurn] | None = None,
                 fn: Callable[[list[Message]], AssistantTurn] | None = None) -> None:
        super().__init__(spec)
        self.script = list(script or [])
        self.fn = fn
        self.calls: list[dict] = []   # recorded for assertions

    def complete(self, messages, tools=None, effort="medium") -> AssistantTurn:
        self.calls.append({"messages": messages, "tools": tools, "effort": effort})
        if self.fn:
            return self.fn(messages)
        if self.script:
            return self.script.pop(0)
        return AssistantTurn(content="done", stop_reason="end_turn")
