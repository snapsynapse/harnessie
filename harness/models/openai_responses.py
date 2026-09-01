"""OpenAI Responses API adapter with reasoning and function-tool support.

The generic ``openai-compat`` adapter intentionally targets Chat Completions.
Current OpenAI reasoning models require Responses for reasoning plus function
tools, so this adapter owns that provider-specific wire contract.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import AssistantTurn, Message, ModelInterface, ToolCall


class OpenAIResponsesModel(ModelInterface):
    """Stateful Responses adapter that replays output items between turns."""

    def __init__(self, spec) -> None:
        super().__init__(spec)
        self._input_items: list[dict] = []
        self._messages_seen = 0
        self._instructions = ""
        self._conversation: list[Message] | None = None

    def complete(self, messages, tools=None, effort="medium") -> AssistantTurn:
        # Runner instances reuse one model object across phases. Each AgentLoop
        # owns a distinct message list, so identity is the conversation boundary
        # even when two phases happen to have the same message count.
        if messages is not self._conversation:
            self._input_items = []
            self._messages_seen = 0
            self._instructions = ""
            self._conversation = messages

        delta, instructions = self._new_input(messages)
        input_items = [*self._input_items, *delta]
        body: dict = {
            "model": self.spec.model_id,
            "input": input_items,
            "max_output_tokens": self.spec.max_tokens,
            # Stateless replay keeps provider retention off while preserving
            # reasoning items returned as encrypted content.
            "store": False,
            "include": ["reasoning.encrypted_content"],
        }
        if instructions:
            body["instructions"] = instructions
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
                for t in tools
            ]
        if self.spec.supports_effort:
            body["reasoning"] = {"effort": effort}
        body.update(self.spec.extra)

        base = self.spec.base_url.rstrip("/")
        if not base:
            return AssistantTurn(
                content="config_error: base_url required for openai-responses",
                stop_reason="error")
        headers = {"content-type": "application/json"}
        key = os.environ.get(self.spec.api_key_env, "") if self.spec.api_key_env else ""
        if key:
            headers["authorization"] = f"Bearer {key}"
        req = urllib.request.Request(
            f"{base}/responses", data=json.dumps(body).encode(), headers=headers)
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
            output = data.get("output")
            if not isinstance(output, list):
                raise TypeError("output must be an array")
            status = data.get("status", "completed")
            if not isinstance(status, str):
                raise TypeError("status must be a string")

            text_parts: list[str] = []
            refusals: list[str] = []
            tool_calls: list[ToolCall] = []
            for item in output:
                if not isinstance(item, dict):
                    raise TypeError("output items must be objects")
                item_type = item.get("type")
                if item_type == "function_call":
                    name = item.get("name")
                    call_id = item.get("call_id")
                    if not isinstance(name, str) or not name:
                        raise TypeError("function call name must be a non-empty string")
                    if not isinstance(call_id, str) or not call_id:
                        raise TypeError("function call call_id must be a non-empty string")
                    tool_calls.append(ToolCall(
                        id=call_id,
                        name=name,
                        arguments=self._parse_args(item.get("arguments")),
                    ))
                elif item_type == "message":
                    content = item.get("content", [])
                    if not isinstance(content, list):
                        raise TypeError("message content must be an array")
                    for block in content:
                        if not isinstance(block, dict):
                            raise TypeError("message content blocks must be objects")
                        if block.get("type") == "output_text":
                            text = block.get("text")
                            if not isinstance(text, str):
                                raise TypeError("output_text text must be a string")
                            text_parts.append(text)
                        elif block.get("type") == "refusal":
                            refusal = block.get("refusal")
                            if not isinstance(refusal, str):
                                raise TypeError("refusal text must be a string")
                            refusals.append(refusal)

            usage = data.get("usage")
            if usage is None:
                usage = {}
            if not isinstance(usage, dict):
                raise TypeError("usage must be an object")
            input_tokens = self._usage_count(usage, "input_tokens")
            output_tokens = self._usage_count(usage, "output_tokens")

            if refusals:
                stop = "refusal"
            elif tool_calls:
                stop = "tool_use"
            elif status == "completed":
                stop = "end_turn"
            elif status == "incomplete":
                detail = data.get("incomplete_details") or {}
                stop = ("max_tokens" if isinstance(detail, dict)
                        and detail.get("reason") == "max_output_tokens" else "error")
            elif status in {"failed", "cancelled"}:
                stop = "error"
            else:
                raise ValueError("unsupported response status")
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError,
                ValueError, AttributeError) as e:
            return AssistantTurn(
                content=("provider_response_error: malformed OpenAI Responses "
                         f"response ({type(e).__name__})"),
                stop_reason="error")

        # Preserve every model output item, including encrypted reasoning, for
        # the next stateless turn. Commit state only after full validation.
        self._input_items = [*input_items, *output]
        self._messages_seen = len(messages)
        self._instructions = instructions
        content = "\n".join(refusals or text_parts)
        return AssistantTurn(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=data,
        )

    def _new_input(self, messages: list[Message]) -> tuple[list[dict], str]:
        instructions = self._instructions
        items: list[dict] = []
        for message in messages[self._messages_seen:]:
            if message.role == "system":
                instructions = message.content
            elif message.role == "assistant":
                # The corresponding raw response output is already retained.
                continue
            elif message.role == "tool":
                items.append({
                    "type": "function_call_output",
                    "call_id": message.tool_call_id,
                    "output": message.content,
                })
            elif message.role in {"user", "developer"}:
                items.append({"role": message.role, "content": message.content})
            else:
                raise ValueError(f"unsupported message role: {message.role}")
        return items, instructions

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
            return {"_malformed": raw}
