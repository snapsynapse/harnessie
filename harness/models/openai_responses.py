"""OpenAI Responses API adapter with reasoning and function-tool support.

The generic ``openai-compat`` adapter intentionally targets Chat Completions.
Current OpenAI reasoning models require Responses for reasoning plus function
tools, so this adapter owns that provider-specific wire contract.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import urllib.request

from . import _transport
from .base import AssistantTurn, Message, ModelInterface, ToolCall


class OpenAIResponsesModel(ModelInterface):
    """Stateful Responses adapter that replays output items between turns."""

    def __init__(self, spec) -> None:
        super().__init__(spec)
        self._input_items: list[dict] = []
        self._messages_seen = 0
        self._instructions = ""
        self._conversation: list[Message] | None = None
        self._state_lock = threading.Lock()

    def for_conversation(self) -> "OpenAIResponsesModel":
        fresh = copy.copy(self)
        fresh._input_items = []
        fresh._messages_seen = 0
        fresh._instructions = ""
        fresh._conversation = None
        fresh._state_lock = threading.Lock()
        return fresh

    def complete(self, messages, tools=None, effort="medium") -> AssistantTurn:
        # The runner gives each AgentLoop its own instance (for_conversation).
        # A directly shared instance still treats message-list identity as the
        # conversation boundary, and only commits replay state below when this
        # call's conversation still owns the instance, so an interleaved call
        # can never install a foreign history.
        with self._state_lock:
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
                    if item.get("status", "completed") != "completed":
                        raise ValueError("function call item is not completed")
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

            # Terminal response status takes precedence over everything in
            # the output; only a completed response can carry callable tools,
            # and a reported error object overrides even a completed status.
            if data.get("error") is not None or status in {"failed", "cancelled"}:
                stop = "error"
            elif status == "incomplete":
                detail = data.get("incomplete_details") or {}
                stop = ("max_tokens" if isinstance(detail, dict)
                        and detail.get("reason") == "max_output_tokens" else "error")
            elif status != "completed":
                raise ValueError("unsupported response status")
            elif refusals:
                stop = "refusal"
            elif tool_calls:
                stop = "tool_use"
            else:
                stop = "end_turn"
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError,
                ValueError, AttributeError) as e:
            return _transport.malformed_turn("OpenAI Responses", e, usage)

        if stop not in {"end_turn", "tool_use"}:
            # Not committed to replay state: the next request must not carry
            # unanswered calls from a response that was never acted on.
            return AssistantTurn(
                content=("\n".join(refusals) if stop == "refusal"
                         else f"provider_status: {status}"
                         + (" with provider error" if data.get("error") is not None
                            else "") if stop == "error"
                         else "\n".join(text_parts)),
                stop_reason=stop,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                raw=data,
                usage_known=usage.known,
            )

        # Preserve every model output item, including encrypted reasoning, for
        # the next stateless turn. Commit state only after full validation.
        with self._state_lock:
            if messages is self._conversation:
                self._input_items = [*input_items, *output]
                self._messages_seen = len(messages)
                self._instructions = instructions
        content = "\n".join(refusals or text_parts)
        return AssistantTurn(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            raw=data,
            usage_known=usage.known,
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
    def _parse_args(raw) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"_malformed": raw}
