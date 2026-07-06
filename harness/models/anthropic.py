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
import urllib.error
import urllib.request

from .base import AssistantTurn, Message, ModelInterface, ToolCall

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


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
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            return AssistantTurn(content=f"provider_error {e.code}: {detail}",
                                 stop_reason="error", raw=detail)
        except (urllib.error.URLError, TimeoutError) as e:
            return AssistantTurn(content=f"network_error: {e}", stop_reason="error")

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(id=block["id"], name=block["name"],
                                           arguments=block.get("input") or {}))
        usage = data.get("usage", {})
        stop = data.get("stop_reason") or "end_turn"
        return AssistantTurn(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else stop,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            raw=data,
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
