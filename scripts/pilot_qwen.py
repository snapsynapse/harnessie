"""Bounded local Qwen pilot adapter.  It has no provider fallback."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from harness.models.base import AssistantTurn, Message, ModelInterface, ModelSpec
from scripts.pilot_claude_code import ClaudeCodePilot
from scripts.pilot_contract import CallAllowance, PilotLimits, PilotRefusal, QWEN_MODEL
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_request_metrics import PreparedPilotRequest

_BASE_URL = "http://127.0.0.1:11434/v1"
_CHAT_URL = _BASE_URL + "/chat/completions"
_CHILD_TIMEOUT_S = 120.0
_ACCOUNTING_CONVENTION = "cache_tokens_zero: included_in_prompt_tokens"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


@dataclass(frozen=True)
class QwenPilotReceipt:
    status: str
    failure: str | None
    answer_model: str | None
    usage: dict[str, int | None]
    model_usage: dict[str, dict[str, int | None]]
    dollar_cost: None
    before_identity: dict | None
    after_identity: dict | None
    raw_provider_usage: dict | None
    inference_started: bool
    accounting_convention: str = _ACCOUNTING_CONVENTION

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class QwenPilot(ModelInterface):
    """One local OpenAI-compatible call with pre/post identity receipts."""

    def __init__(self, spec: ModelSpec, expected_identity: dict,
                 identity_capture: Callable[[], dict], allowance: CallAllowance | None = None,
                 transport: Callable[[bytes, PilotLimits], bytes] | None = None) -> None:
        super().__init__(spec)
        if (spec.model_id != QWEN_MODEL or spec.provider != "openai-compat"
                or spec.base_url != _BASE_URL or spec.api_key_env or spec.extra):
            raise PilotRefusal("unsupported_pilot_model")
        if not callable(identity_capture):
            raise PilotRefusal("invalid_identity_capture")
        # Validates the supplied sealed identity before a request can be built.
        sealed = copy.deepcopy(expected_identity)
        assert_same_identity(sealed, sealed)
        if (sealed["model"]["tag"] != QWEN_MODEL
                or sealed["harness_identity"]["model_id"] != QWEN_MODEL
                or sealed["harness_identity"]["endpoint"] != _BASE_URL):
            raise PilotRefusal("unsupported_expected_identity")
        if sealed["harness_identity"]["sampling"] != {"temperature": 0.0}:
            raise PilotRefusal("unsupported_sampling_configuration")
        self.expected_identity = sealed
        self.identity_capture = identity_capture
        self.allowance = allowance or CallAllowance()
        self.transport = transport or _child_transport
        self.receipts: list[QwenPilotReceipt] = []
        self._failed = False

    def complete(self, messages: list[Message], tools: list[dict] | None = None,
                 effort: str = "medium") -> AssistantTurn:
        if self._failed:
            return self._refuse("transport_latched", None)
        offered_tools = tools or []
        try:
            prepared = self.prepare_request(messages, offered_tools, effort)
        except (TypeError, ValueError, PilotRefusal):
            return self._refuse("invalid_request", None)
        if len(prepared.request) > self.allowance.limits.max_input_bytes:
            return self._refuse("input_limit_exceeded", None)
        evidence_bytes = sum(len(message.content.encode("utf-8")) for message in messages
                             if message.role == "tool")
        if evidence_bytes > self.allowance.limits.max_evidence_bytes:
            return self._refuse("evidence_limit_exceeded", None)
        return self.complete_prepared(prepared, offered_tools)

    def prepare_request(self, messages: list[Message], tools: list[dict] | None = None,
                        effort: str = "medium") -> PreparedPilotRequest:
        """Build the exact immutable request bytes without reserving or dispatching."""
        del effort  # Sampling is sealed in expected_identity, never caller-selected.
        prompt = ClaudeCodePilot._request_prompt(messages, tools or [])
        request = self._request_bytes(prompt)
        return PreparedPilotRequest(
            request=request,
            transport="ollama-loopback-openai-compat",
            encoding="openai-compatible-json-with-neutral-json-string",
            inner_prompt_bytes=len(prompt.encode("utf-8")),
        )

    def complete_prepared(self, prepared: PreparedPilotRequest,
                          offered_tools: list[dict], effort: str = "medium") -> AssistantTurn:
        """Dispatch request bytes that have already passed external admission."""
        del effort
        if self._failed:
            return self._refuse("transport_latched", None)
        if (type(prepared) is not PreparedPilotRequest
                or prepared.transport != "ollama-loopback-openai-compat"
                or prepared.encoding != "openai-compatible-json-with-neutral-json-string"
                or not isinstance(prepared.request, bytes)):
            return self._refuse("invalid_request", None)
        if len(prepared.request) > self.allowance.limits.max_input_bytes:
            return self._refuse("input_limit_exceeded", None)
        try:
            self.allowance.reserve()
        except PilotRefusal as exc:
            return self._refuse(exc.code, None)

        before: dict | None = None
        after: dict | None = None
        raw_usage: dict | None = None
        usage = _unknown_usage()
        answer_model: str | None = None
        failure: str | None = None
        turn: tuple[str, list, str] | None = None
        request_started = False
        try:
            before = self.identity_capture()
            assert_same_identity(self.expected_identity, before)
        except Exception:
            failure = "identity_before_invalid"

        if failure is None:
            try:
                request_started = True
                output = self.transport(prepared.request, self.allowance.limits)
                if not isinstance(output, bytes) or len(output) > self.allowance.limits.max_output_bytes:
                    raise PilotRefusal("output_limit_exceeded")
                data = _json_object(output)
                raw_usage = data.get("usage") if isinstance(data, dict) and isinstance(data.get("usage"), dict) else None
                usage = _usage(raw_usage)
                answer_model, envelope = _response_envelope(data)
                turn = ClaudeCodePilot._turn({"structured_output": envelope}, offered_tools)
            except PilotRefusal as exc:
                failure = exc.code
            except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                failure = "malformed_response"
            except Exception:
                # Transport implementations must not disclose arbitrary provider text.
                failure = "transport_failed"

        # A request may be malformed or refused, but it still needs a post-call
        # identity capture before we retain its receipt.
        if request_started:
            try:
                after = self.identity_capture()
                assert_same_identity(self.expected_identity, after)
            except Exception:
                failure = "identity_drift"

        if failure is not None:
            return self._refuse(failure, before, after, usage, answer_model, raw_usage,
                                request_started)
        assert turn is not None
        receipt = QwenPilotReceipt(
            status="completed", failure=None, answer_model=answer_model, usage=usage,
            model_usage={QWEN_MODEL: usage}, dollar_cost=None, before_identity=before,
            after_identity=after, raw_provider_usage=raw_usage, inference_started=True,
        )
        self.receipts.append(receipt)
        return AssistantTurn(content=turn[0], tool_calls=turn[1], stop_reason=turn[2],
                             input_tokens=usage["input_tokens"] or 0,
                             output_tokens=usage["output_tokens"] or 0)

    def _request_bytes(self, prompt: str) -> bytes:
        payload = {
            "model": QWEN_MODEL,
            "messages": [
                {"role": "system", "content": "Return only the strict neutral structured response. Do not execute tools."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "harnessie_neutral_turn", "strict": True,
                "schema": ClaudeCodePilot._output_schema(),
            }},
            "max_tokens": self.allowance.limits.max_output_tokens,
            "temperature": 0.0,
            "stream": False,
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

    def _refuse(self, code: str, before: dict | None,
                after: dict | None = None, usage: dict[str, int | None] | None = None,
                answer_model: str | None = None, raw_usage: dict | None = None,
                inference_started: bool = False) -> AssistantTurn:
        self._failed = True
        normalized = usage or _unknown_usage()
        self.receipts.append(QwenPilotReceipt(
            status="refused", failure=code, answer_model=answer_model, usage=normalized,
            model_usage={QWEN_MODEL: normalized}, dollar_cost=None, before_identity=before,
            after_identity=after, raw_provider_usage=raw_usage,
            inference_started=inference_started,
        ))
        return AssistantTurn(content=f"pilot_refusal: {code}", stop_reason="error",
                             input_tokens=normalized["input_tokens"] or 0,
                             output_tokens=normalized["output_tokens"] or 0)


def _unknown_usage() -> dict[str, int | None]:
    return {"input_tokens": None, "output_tokens": None,
            "cache_creation_input_tokens": None, "cache_read_input_tokens": None}


def _usage(raw: dict | None) -> dict[str, int | None]:
    if type(raw) is not dict:
        raise PilotRefusal("model_usage_missing")
    values = []
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = raw.get(name)
        if type(value) is not int or value < 0:
            raise PilotRefusal("model_usage_incomplete")
        values.append(value)
    if values[2] != values[0] + values[1]:
        raise PilotRefusal("model_usage_inconsistent")
    # OpenAI's prompt_tokens includes any cached input. This receipt records
    # that complete count as input and reports no separate cache totals.
    return {"input_tokens": values[0], "output_tokens": values[1],
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


def _strict_json(raw: str | bytes) -> object:
    def reject_constant(_value: str) -> None:
        raise ValueError("nonfinite json")
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate json key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid json") from exc
    def finite(item: object) -> None:
        if isinstance(item, float) and (item == float("inf") or item == float("-inf") or item != item):
            raise ValueError("nonfinite json")
        if type(item) is dict:
            for child in item.values():
                finite(child)
        elif type(item) is list:
            for child in item:
                finite(child)
    try:
        finite(value)
    except RecursionError as exc:
        raise ValueError("invalid json") from exc
    return value


def _json_object(raw: bytes) -> dict:
    if not isinstance(raw, bytes):
        raise ValueError("not bytes")
    value = _strict_json(raw)
    if type(value) is not dict:
        raise ValueError("not object")
    return value


def _response_envelope(data: dict) -> tuple[str, dict]:
    if data.get("model") != QWEN_MODEL:
        raise PilotRefusal("model_identity_mismatch")
    choices = data.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise PilotRefusal("choices_invalid")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise PilotRefusal("provider_finish_not_stop")
    message = choice.get("message")
    if type(message) is not dict or not isinstance(message.get("content"), str):
        raise PilotRefusal("malformed_response")
    if message.get("tool_calls"):
        raise PilotRefusal("native_tool_calls_denied")
    envelope = _strict_json(message["content"])
    if type(envelope) is not dict:
        raise PilotRefusal("malformed_response")
    return data["model"], envelope


def _child_transport(payload: bytes, limits: PilotLimits) -> bytes:
    if not isinstance(payload, bytes) or len(payload) > limits.max_input_bytes:
        raise PilotRefusal("input_limit_exceeded")
    root = Path(__file__).resolve().parents[1]
    input_file = tempfile.TemporaryFile()
    input_file.write(payload)
    input_file.seek(0)
    process = subprocess.Popen([sys.executable, __file__, "--request-child"], stdin=input_file,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                               env={"PYTHONPATH": str(root)}, cwd=root)
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    selector.register(process.stderr, selectors.EVENT_READ)
    chunks: list[bytes] = []
    total = 0
    deadline = time.monotonic() + min(limits.timeout_s, _CHILD_TIMEOUT_S)
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PilotRefusal("process_timeout")
            for key, _ in selector.select(remaining):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                total += len(block)
                if total > limits.max_output_bytes:
                    raise PilotRefusal("output_limit_exceeded")
                if key.fileobj is process.stdout:
                    chunks.append(block)
        try:
            returncode = process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            raise PilotRefusal("process_timeout") from exc
        if returncode != 0:
            raise PilotRefusal("transport_failed")
        return b"".join(chunks)
    finally:
        selector.close()
        if process.poll() is None:
            _kill_child_group(process)
        input_file.close()


def _kill_child_group(process: subprocess.Popen[bytes]) -> None:
    """Bounded cleanup for a child that may have inherited stream handles."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (AttributeError, OSError):
        if process.poll() is None:
            process.kill()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def _request_child() -> int:
    raw = sys.stdin.buffer.read()
    if len(raw) > PilotLimits().max_input_bytes:
        return 2
    try:
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 2
    request = Request(_CHAT_URL, data=raw, method="POST", headers={"Content-Type": "application/json"})
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=_CHILD_TIMEOUT_S) as response:
            length = response.headers.get("Content-Length")
            if length is not None and (not length.isdigit() or int(length) > PilotLimits().max_output_bytes):
                return 2
            body = response.read(PilotLimits().max_output_bytes + 1)
    except (HTTPError, URLError, OSError, ValueError):
        return 2
    if len(body) > PilotLimits().max_output_bytes:
        return 2
    sys.stdout.buffer.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(_request_child() if sys.argv[1:] == ["--request-child"] else 2)
