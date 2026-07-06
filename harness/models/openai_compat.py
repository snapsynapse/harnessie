"""OpenAI-compatible chat/completions adapter (stdlib urllib).

One adapter covers most cheap and open-source brains: vLLM, Ollama, llama.cpp
server, Together, Groq, DeepSeek, GLM/Zhipu, Qwen/DashScope-compatible — any
endpoint speaking POST {base_url}/chat/completions.

Effort mapping: sent as reasoning_effort when supports_effort is true (o-series
and several OSS reasoning models accept it); otherwise effort is prompt-level
only (the role prompt states the expected depth), which is the honest fallback
for models with no reasoning knob.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import AssistantTurn, Message, ModelInterface, ToolCall


class OpenAICompatModel(ModelInterface):
    def complete(self, messages, tools=None, effort="medium") -> AssistantTurn:
        body: dict = {
            "model": self.spec.model_id,
            "messages": [self._msg_to_wire(m) for m in messages],
            "max_tokens": self.spec.max_tokens,
        }
        if tools:
            body["tools"] = [
                {"type": "function",
                 "function": {"name": t["name"], "description": t["description"],
                              "parameters": t["parameters"]}}
                for t in tools
            ]
        if self.spec.supports_effort:
            # collapse the 5-level dial onto the common 3-level scale
            body["reasoning_effort"] = {"xhigh": "high", "max": "high"}.get(effort, effort)
        body.update(self.spec.extra)

        base = self.spec.base_url.rstrip("/")
        if not base:
            return AssistantTurn(content="config_error: base_url required for openai-compat",
                                 stop_reason="error")
        headers = {"content-type": "application/json"}
        key = os.environ.get(self.spec.api_key_env, "") if self.spec.api_key_env else ""
        if key:
            headers["authorization"] = f"Bearer {key}"
        req = urllib.request.Request(f"{base}/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            return AssistantTurn(content=f"provider_error {e.code}: {detail}",
                                 stop_reason="error", raw=detail)
        except (urllib.error.URLError, TimeoutError) as e:
            return AssistantTurn(content=f"network_error: {e}", stop_reason="error")

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        tool_calls = [
            ToolCall(
                id=tc.get("id", f"call_{i}"),
                name=tc["function"]["name"],
                arguments=self._parse_args(tc["function"].get("arguments")),
            )
            for i, tc in enumerate(msg.get("tool_calls") or [])
        ]
        usage = data.get("usage", {})
        finish = choice.get("finish_reason") or "stop"
        stop = {"stop": "end_turn", "tool_calls": "tool_use",
                "length": "max_tokens"}.get(finish, finish)
        return AssistantTurn(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else stop,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )

    @staticmethod
    def _parse_args(raw) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            # Malformed args happen on weaker models; surface them to the loop
            # as a value the tool layer can reject with a useful error.
            return {"_malformed": raw}

    @staticmethod
    def _msg_to_wire(m: Message) -> dict:
        if m.role == "assistant" and m.tool_calls:
            return {
                "role": "assistant",
                "content": m.content or None,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name,
                                  "arguments": json.dumps(tc.arguments)}}
                    for tc in m.tool_calls
                ],
            }
        if m.role == "tool":
            return {"role": "tool", "tool_call_id": m.tool_call_id,
                    "name": m.name, "content": m.content}
        return {"role": m.role, "content": m.content}
