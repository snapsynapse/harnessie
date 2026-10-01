"""Fail-closed parser for the pilot's Claude Code ``stream-json`` output.

The parser is deliberately offline and accepts only bytes captured from one
CLI process.  It never invokes a provider or reads a run directory.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any


USAGE_FIELDS = {
    "input_tokens": ("inputTokens",),
    "output_tokens": ("outputTokens",),
    "cache_creation_input_tokens": ("cacheCreationInputTokens",),
    "cache_read_input_tokens": ("cacheReadInputTokens",),
}


@dataclass(frozen=True)
class StreamCapture:
    structured_output: dict[str, Any] | None
    answer_model: str | None
    model_usage: dict[str, dict[str, int | None]]
    usage_totals: dict[str, int | None]
    failure: str | None
    # One raw map per terminal result, preserved without normalizing away cost,
    # provider, or canonical-model metadata. Multiple terminals are refused.
    reported_model_usages: tuple[dict[str, Any], ...] = ()
    # Stable parser evidence only: never raw provider output.
    diagnostic: dict[str, str | int] | None = None


def unknown_usage() -> dict[str, int | None]:
    return {field: None for field in USAGE_FIELDS}


def parse_stream_json(payload: bytes) -> StreamCapture:
    """Bind one StructuredOutput exchange to one terminal success result."""
    empty = StreamCapture(None, None, {}, unknown_usage(), "stream_malformed", (),
                          {"reason": "empty_stream"})
    lines = payload.splitlines(keepends=True)
    if not lines:
        return empty
    events: list[dict[str, Any]] = []
    event_lines: dict[int, int] = {}
    malformed: dict[str, str | int] | None = None
    offset = 0
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip(b"\r\n")
        lexical = {"line": line_number, "byte_offset": offset}
        offset += len(raw_line)
        if not line.strip():
            malformed = malformed or {"reason": "blank_line", **lexical}
            continue
        try:
            event = _loads(line.decode("utf-8"))
        except UnicodeDecodeError:
            malformed = malformed or {"reason": "invalid_utf8", **lexical}
            continue
        except (json.JSONDecodeError, ValueError, RecursionError, OverflowError):
            malformed = malformed or {"reason": "invalid_json", **lexical}
            continue
        if isinstance(event, dict):
            events.append(event)
            event_lines[id(event)] = line_number
        else:
            malformed = malformed or {"reason": "non_object_event", **lexical}

    result_events = [event for event in events if event.get("type") == "result"]
    raw_usages = tuple(_raw_model_usage(event.get("modelUsage")) for event in result_events)
    preserved_raw = raw_usages[-1] if len(raw_usages) == 1 else {}
    preserved_models, preserved_totals, _ = _model_usage(preserved_raw)
    def diagnostic(reason: str, event: dict[str, Any] | None = None) -> dict[str, str | int]:
        value: dict[str, str | int] = {"reason": reason}
        if event is not None:
            value["event"] = event_lines.get(id(event), 0)
        return value
    def fail(code: str, answer_model: str | None = None,
             detail: dict[str, str | int] | None = None) -> StreamCapture:
        return StreamCapture(None, answer_model, preserved_models, preserved_totals, code, raw_usages, detail)
    if malformed:
        return fail("stream_malformed", detail=malformed)
    if any(not isinstance(event.get("type"), str) for event in events):
        event = next(event for event in events if not isinstance(event.get("type"), str))
        return fail("stream_malformed", detail=diagnostic("missing_type", event))

    init = [event for event in events if event.get("type") == "system" and event.get("subtype") == "init"]
    terminal = result_events
    if not terminal:
        return fail("stream_truncated", detail=diagnostic("missing_terminal_result"))
    if len(init) != 1:
        return fail("stream_malformed", detail=diagnostic("init_cardinality"))
    if len(terminal) != 1:
        return fail("stream_malformed", detail=diagnostic("terminal_cardinality"))
    if events[-1] is not terminal[0]:
        return fail("stream_malformed", detail=diagnostic("terminal_not_last", terminal[0]))
    session_id = init[0].get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return fail("stream_malformed", detail=diagnostic("missing_session", init[0]))
    if any(event.get("type") in {"assistant", "user", "result"}
           and event.get("session_id") != session_id for event in events):
        return fail("stream_session_mismatch", detail=diagnostic("session_mismatch"))
    tools = init[0].get("tools")
    if not isinstance(tools, list) or any(not isinstance(name, str) for name in tools):
        return fail("stream_malformed", detail=diagnostic("invalid_init_tools", init[0]))
    if tools != ["StructuredOutput"]:
        return fail("native_tool_unapproved", detail=diagnostic("tools_not_structured_output", init[0]))
    if init[0].get("mcp_servers") != []:
        return fail("mcp_configuration_unapproved", detail=diagnostic("mcp_servers_not_empty", init[0]))

    terminal_event = terminal[0]
    model_usage, totals, usage_failure = _model_usage(terminal_event.get("modelUsage"))
    subtype = terminal_event.get("subtype")
    if not isinstance(subtype, str):
        return StreamCapture(None, None, model_usage, totals, "terminal_not_successful", raw_usages,
                             diagnostic("terminal_subtype_missing", terminal_event))
    if terminal_event.get("is_error") is True or subtype == "error":
        return StreamCapture(None, None, model_usage, totals, "provider_result_error", raw_usages,
                             diagnostic("provider_terminal_error", terminal_event))
    if subtype in {"max_turns", "max-turns"}:
        return StreamCapture(None, None, model_usage, totals, "provider_result_max_turns", raw_usages,
                             diagnostic("provider_terminal_max_turns", terminal_event))
    if (terminal_event.get("is_error") is not False or subtype != "success"
            or terminal_event.get("terminal_reason") != "completed"):
        return StreamCapture(None, None, model_usage, totals, "terminal_not_successful", raw_usages,
                             diagnostic("terminal_not_completed", terminal_event))
    if usage_failure is not None:
        return StreamCapture(None, None, model_usage, totals, usage_failure, raw_usages,
                             diagnostic("model_usage_invalid", terminal_event))
    if any(value is None for usage in model_usage.values() for value in usage.values()):
        return StreamCapture(None, None, model_usage, totals, "model_usage_incomplete", raw_usages,
                             diagnostic("model_usage_incomplete", terminal_event))

    blocks: list[tuple[str, str, str, dict[str, Any], int]] = []
    for event_index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        if "parent_tool_use_id" not in event or event["parent_tool_use_id"] is not None:
            return StreamCapture(None, None, model_usage, totals, "assistant_parent_invalid", raw_usages,
                                 diagnostic("assistant_parent_invalid", event))
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                 diagnostic("invalid_assistant_message", event))
        model = message.get("model")
        message_id = message.get("id")
        request_id = event.get("request_id")
        content = message.get("content")
        if not all(isinstance(value, str) and value for value in (model, message_id, request_id)) or not isinstance(content, list):
            return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                 diagnostic("invalid_assistant_content", event))
        for block in content:
            if not isinstance(block, dict):
                return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                     diagnostic("invalid_content_block", event))
            if block.get("type") == "tool_use":
                if block.get("name") != "StructuredOutput":
                    return StreamCapture(None, None, model_usage, totals, "native_tool_unapproved", raw_usages,
                                         diagnostic("native_tool_block", event))
                tool_id = block.get("id")
                tool_input = block.get("input")
                if not isinstance(tool_id, str) or not tool_id or not isinstance(tool_input, dict):
                    return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                         diagnostic("invalid_structured_output_block", event))
                blocks.append((model, message_id, request_id, {"id": tool_id, "input": tool_input}, event_index))
            elif block.get("type") == "thinking":
                # Observed opaque metadata: it is neither an answer nor a tool
                # request. Do not inspect or validate signature semantics.
                if (set(block) != {"type", "thinking", "signature"}
                        or not isinstance(block.get("thinking"), str)
                        or not isinstance(block.get("signature"), str)
                        or not block["signature"]):
                    return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                         diagnostic("invalid_thinking_block", event))
            elif block.get("type") != "text" or not isinstance(block.get("text"), str):
                return StreamCapture(None, None, model_usage, totals, "stream_malformed", raw_usages,
                                     diagnostic("invalid_text_block", event))
    if len(blocks) != 1:
        return StreamCapture(None, None, model_usage, totals, "structured_output_binding_missing", raw_usages,
                             diagnostic("structured_output_block_cardinality"))
    answer_model, message_id, request_id, tool, tool_event_index = blocks[0]
    if init[0].get("model") not in (None, answer_model):
        return StreamCapture(None, answer_model, model_usage, totals, "conflicting_model_evidence", raw_usages,
                             diagnostic("init_model_conflict", init[0]))
    # Repeated assistant blocks may share message/request IDs.  They are valid
    # only when every assistant block supports the same answer-model evidence.
    assistant_identity = {
        (event["message"].get("model"), event["message"].get("id"), event.get("request_id"))
        for event in events
        if event.get("type") == "assistant" and isinstance(event.get("message"), dict)
    }
    if assistant_identity != {(answer_model, message_id, request_id)}:
        return StreamCapture(None, answer_model, model_usage, totals, "conflicting_model_evidence", raw_usages,
                             diagnostic("assistant_model_evidence_conflict"))

    links = []
    for event_index, event in enumerate(events):
        if event.get("type") != "user":
            continue
        if ("parent_tool_use_id" not in event or event["parent_tool_use_id"] is not None
                or event_index <= tool_event_index):
            return StreamCapture(None, answer_model, model_usage, totals, "tool_result_binding_invalid", raw_usages,
                                 diagnostic("tool_result_order_or_parent_invalid", event))
        content = event.get("message", {}).get("content") if isinstance(event.get("message"), dict) else None
        if not isinstance(content, list):
            return StreamCapture(None, answer_model, model_usage, totals, "stream_malformed", raw_usages,
                                 diagnostic("invalid_tool_result_content", event))
        for block in content:
            if (isinstance(block, dict) and block.get("type") == "tool_result"
                    and block.get("tool_use_id") == tool["id"] and block.get("is_error") is not True):
                links.append((event, block))
    if len(links) != 1 or links[0][0].get("tool_use_result") != "Structured output provided successfully":
        return StreamCapture(None, answer_model, model_usage, totals, "structured_output_binding_missing", raw_usages,
                             diagnostic("structured_output_result_link_missing"))

    structured = terminal_event.get("structured_output")
    raw_result = terminal_event.get("result")
    try:
        decoded_result = _loads(raw_result) if isinstance(raw_result, str) else None
    except (json.JSONDecodeError, ValueError, RecursionError, OverflowError):
        decoded_result = None
    if not isinstance(structured, dict) or structured != tool["input"] or decoded_result != structured:
        return StreamCapture(None, answer_model, model_usage, totals, "structured_output_binding_conflict", raw_usages,
                             diagnostic("terminal_structured_output_conflict", terminal_event))
    return StreamCapture(structured, answer_model, model_usage, totals, None, raw_usages)


def _raw_model_usage(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def _loads(text: str) -> Any:
    def no_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"non-finite JSON number: {value}")
        return parsed
    return json.loads(text, parse_constant=no_constant, parse_float=finite_float,
                      object_pairs_hook=no_duplicates)


def _model_usage(raw: object) -> tuple[dict[str, dict[str, int | None]], dict[str, int | None], str | None]:
    if not isinstance(raw, dict) or not raw:
        return {}, unknown_usage(), "model_usage_missing"
    models: dict[str, dict[str, int | None]] = {}
    for model, values in raw.items():
        if not isinstance(model, str) or not model or not isinstance(values, dict):
            return models, unknown_usage(), "model_usage_malformed"
        entry: dict[str, int | None] = {}
        for field, names in USAGE_FIELDS.items():
            value = next((values.get(name) for name in names if name in values), None)
            entry[field] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        models[model] = entry
    return models, _totals(models), None


def _totals(models: dict[str, dict[str, int | None]]) -> dict[str, int | None]:
    totals = unknown_usage()
    for field in totals:
        values = [usage[field] for usage in models.values()]
        totals[field] = sum(values) if values and all(value is not None for value in values) else None
    return totals
