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
        if "max_completion_tokens" in self.spec.extra and "max_tokens" not in self.spec.extra:
            # OpenAI's newest models reject max_tokens outright; a declared
            # max_completion_tokens takes its place unless both are explicit.
            del body["max_tokens"]

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
                payload = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            return AssistantTurn(content=f"provider_error {e.code}: {detail}",
                                 stop_reason="error", raw=detail)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return AssistantTurn(content=f"network_error: {e}", stop_reason="error")

        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise TypeError("top level must be an object")
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise TypeError("choices must be a non-empty array")
            choice = choices[0]
            if not isinstance(choice, dict):
                raise TypeError("choice must be an object")
            msg = choice.get("message")
            if not isinstance(msg, dict):
                raise TypeError("choice.message must be an object")
            content = msg.get("content")
            if content is None:
                content = ""
            if not isinstance(content, str):
                raise TypeError("message.content must be a string or null")
            raw_tool_calls = msg.get("tool_calls")
            if raw_tool_calls is None:
                raw_tool_calls = []
            if not isinstance(raw_tool_calls, list):
                raise TypeError("message.tool_calls must be an array")
            tool_calls: list[ToolCall] = []
            for i, tc in enumerate(raw_tool_calls):
                if not isinstance(tc, dict) or not isinstance(tc.get("function"), dict):
                    raise TypeError("tool calls must contain function objects")
                function = tc["function"]
                name = function.get("name")
                if not isinstance(name, str) or not name:
                    raise TypeError("tool function name must be a non-empty string")
                call_id = tc.get("id", f"call_{i}")
                if not isinstance(call_id, str) or not call_id:
                    raise TypeError("tool call id must be a non-empty string")
                tool_calls.append(ToolCall(
                    id=call_id,
                    name=name,
                    arguments=self._parse_args(function.get("arguments")),
                ))
            usage = data.get("usage")
            if usage is None:
                usage = {}
            if not isinstance(usage, dict):
                raise TypeError("usage must be an object")
            input_tokens = self._usage_count(usage, "prompt_tokens")
            output_tokens = self._usage_count(usage, "completion_tokens")
            finish = choice.get("finish_reason") or "stop"
            if not isinstance(finish, str):
                raise TypeError("finish_reason must be a string or null")
            stop = {"stop": "end_turn", "tool_calls": "tool_use",
                    "length": "max_tokens", "content_filter": "refusal"}.get(
                        finish, finish)
            if stop not in {"end_turn", "max_tokens", "tool_use", "refusal"}:
                raise ValueError("unsupported finish_reason")
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError,
                ValueError, AttributeError) as e:
            return AssistantTurn(
                content=("provider_response_error: malformed OpenAI-compatible "
                         f"response ({type(e).__name__})"),
                stop_reason="error")
        return AssistantTurn(
            content=content,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else stop,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=data,
        )

    @staticmethod
    def _usage_count(usage: dict, field: str) -> int:
        value = usage.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"usage.{field} must be a non-negative integer")
        return value

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
