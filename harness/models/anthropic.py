"""Anthropic Messages API adapter (stdlib urllib; no SDK dependency).

Effort mapping: on the Claude 5 family, effort is the primary
intelligence/latency/cost dial and is sent as output_config.effort
(low|medium|high|xhigh|max); thinking is adaptive-only, so no thinking
parameter is sent. For pre-5 Claude models set supports_effort: false and, if
wanted, pass a thinking budget through spec.extra.
"""

from __future__ import annotations

import json
import os
import urllib.request

from . import _transport
from .base import AssistantTurn, Message, ModelInterface, ToolCall

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def _error_kind(error) -> str:
    kind = error.get("type") if isinstance(error, dict) else None
    return kind[:100] if isinstance(kind, str) and kind else "error envelope"


class AnthropicModel(ModelInterface):
    def complete(self, messages, tools=None, effort="medium") -> AssistantTurn:
        system, wire_messages = self._to_wire(messages)
        body: dict = {
            "model": self.spec.model_id,
            "max_tokens": self.spec.max_tokens,
            "messages": wire_messages,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]
        if self.spec.supports_effort:
            body["output_config"] = {"effort": effort}
        body.update(self.spec.extra)

        api_key = os.environ.get(self.spec.api_key_env or "ANTHROPIC_API_KEY", "")
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": API_VERSION,
            },
        )
        reply = _transport.post(req)
        if not reply.ok:
            return reply.error_turn()

        usage = _transport.Usage()
        try:
            data = json.loads(reply.body)
            usage = _transport.parse_usage(data, "input_tokens", "output_tokens")
            if usage.malformed:
                raise ValueError("usage counters must be non-negative integers")
            if not isinstance(data, dict):
                raise TypeError("top level must be an object")
            envelope = data.get("type", "message")
            if envelope == "error":
                # An error envelope on a 2xx status is a failed call, whatever
                # else it carries: nothing in it is dispatched.
                return AssistantTurn(
                    content=f"provider_error: {_error_kind(data.get('error'))}",
                    stop_reason="error", input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens, raw=data,
                    usage_known=usage.known)
            if envelope != "message":
                raise ValueError("unsupported response type")

            blocks = data.get("content", [])
            if not isinstance(blocks, list):
                raise TypeError("content must be an array")
            text_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            for block in blocks:
                if not isinstance(block, dict):
                    raise TypeError("content blocks must be objects")
                if block.get("type") == "text":
                    if not isinstance(block.get("text"), str):
                        raise TypeError("text block text must be a string")
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    if not isinstance(block.get("id"), str) or not block["id"]:
                        raise TypeError("tool_use id must be a non-empty string")
                    if not isinstance(block.get("name"), str) or not block["name"]:
                        raise TypeError("tool_use name must be a non-empty string")
                    arguments = block.get("input")
                    if arguments is None:
                        arguments = {}
                    if not isinstance(arguments, dict):
                        raise TypeError("tool_use input must be an object")
                    tool_calls.append(ToolCall(id=block["id"], name=block["name"],
                                               arguments=arguments))
            stop = data.get("stop_reason") or "end_turn"
            if not isinstance(stop, str):
                raise TypeError("stop_reason must be a string")
            stop = {"stop_sequence": "end_turn"}.get(stop, stop)
            if stop not in {"end_turn", "max_tokens", "tool_use", "refusal"}:
                raise ValueError("unsupported stop_reason")
            # The stop reason is authoritative: refused or truncated tool_use
            # blocks are never dispatched, and tool_use must carry a call.
            if stop in {"refusal", "max_tokens"}:
                tool_calls = []
            elif (stop == "tool_use") != bool(tool_calls):
                raise ValueError("stop_reason contradicts tool_use blocks")
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError,
                ValueError, AttributeError) as e:
            return _transport.malformed_turn("Anthropic", e, usage)
        return AssistantTurn(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            raw=data,
            usage_known=usage.known,
        )

    @staticmethod
    def _to_wire(messages: list[Message]) -> tuple[str, list[dict]]:
        """Neutral messages -> Anthropic wire format. System messages hoist to
        the top-level system field; tool results become tool_result blocks."""
        system_parts: list[str] = []
        wire: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "assistant":
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id,
                                   "name": tc.name, "input": tc.arguments})
                wire.append({"role": "assistant", "content": blocks or m.content})
            elif m.role == "tool":
                wire.append({
                    "role": "user",
                    "content": [{"type": "tool_result",
                                 "tool_use_id": m.tool_call_id,
                                 "content": m.content}],
                })
            else:
                wire.append({"role": "user", "content": m.content})
        return "\n\n".join(system_parts), wire
