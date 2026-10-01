from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import time

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_contract import CallAllowance, PilotLimits, PilotRefusal, QWEN_MODEL
from scripts.pilot_qwen import QwenPilot
from scripts.pilot_request_metrics import PreparedPilotRequest
import scripts.pilot_qwen as pilot_qwen


HASH = "a" * 64
BASE = "http://127.0.0.1:11434"


def identity(digest="b" * 64):
    value = {"receipt_version": "harnessie-pilot/1", "client_version": "test", "ollama_base_url": BASE,
             "server_version": "x", "model": {"tag": QWEN_MODEL, "digest": "sha256:" + digest, "size": 1,
             "details": {}, "model_info": {}, "capabilities": [], "from_digests": ["sha256:" + "c" * 64]},
             "harness_identity": {"provider": "openai-compat", "model_id": QWEN_MODEL, "endpoint": BASE + "/v1",
             "prompt_sha256": HASH, "parser_version": "3", "sampling": {"temperature": 0.0}}}
    from scripts.pilot_contract import digest_json
    value["fingerprint"] = digest_json({key: value[key] for key in ("receipt_version", "client_version", "ollama_base_url", "server_version", "model", "harness_identity")})
    return value


def response(*, usage=None, model=QWEN_MODEL, envelope=None, finish="stop"):
    return json.dumps({"model": model, "choices": [{"finish_reason": finish, "message": {"content": json.dumps(envelope or {"content": "ok", "tool_calls": [], "stop_reason": "end_turn"})}}], "usage": usage if usage is not None else {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}).encode()


def pilot(capture=None, transport=None, calls=1, limits=None):
    return QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, BASE + "/v1"), identity(),
                     capture or identity,
                     CallAllowance(limits or PilotLimits(max_calls=calls, max_output_bytes=4096)),
                     transport or (lambda request, limits: response()))


def complete(value, tools=None):
    return value.complete([Message(role="user", content="hello")], tools=tools)


def test_request_is_fixed_neutral_openai_shape_and_receipt_is_complete():
    requests = []
    item = pilot(transport=lambda request, limits: requests.append(json.loads(request)) or response())
    assert complete(item).content == "ok"
    request = requests[0]
    assert request["model"] == QWEN_MODEL and request["temperature"] == 0.0 and request["stream"] is False
    assert request["response_format"]["json_schema"]["strict"] is True
    receipt = item.receipts[-1].as_dict()
    assert receipt["status"] == "completed" and receipt["dollar_cost"] is None
    assert receipt["inference_started"] is True
    assert receipt["usage"] == {"input_tokens": 2, "output_tokens": 3, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    assert receipt["accounting_convention"] == "cache_tokens_zero: included_in_prompt_tokens"


def test_prepare_request_returns_exact_hash_ready_outer_bytes():
    item = pilot()
    messages = [Message(role="user", content='quote: "hello"; unicode: café ☕')]
    tools = [{"name": "read_file", "parameters": {
        "type": "object", "properties": {"path": {"type": "string"}}}}]
    prepared = item.prepare_request(messages, tools, "medium")
    prompt = pilot_qwen.ClaudeCodePilot._request_prompt(messages, tools)
    expected = item._request_bytes(prompt)
    assert prepared == PreparedPilotRequest(
        request=expected,
        transport="ollama-loopback-openai-compat",
        encoding="openai-compatible-json-with-neutral-json-string",
        inner_prompt_bytes=len(prompt.encode("utf-8")),
    )
    assert json.loads(prepared.request)["messages"][1]["content"] == prompt
    assert hashlib.sha256(prepared.request).hexdigest() == (
        "edb09ce7d8fe5dc1053e1adbdee429e1ff521a46f284409951322d80dadbe4a1"
    )


def test_complete_prepared_passes_the_exact_prepared_bytes_to_transport():
    requests = []
    item = pilot(transport=lambda request, limits: requests.append(request) or response())
    prepared = item.prepare_request([Message(role="user", content="hello")], [], "medium")
    assert item.complete_prepared(prepared, []).content == "ok"
    assert requests == [prepared.request]
    assert requests[0] is prepared.request


def test_direct_input_limit_accepts_exact_size_and_refuses_plus_one_before_dispatch():
    messages = [Message(role="user", content="hello")]
    request_size = len(pilot().prepare_request(messages, [], "medium").request)
    accepted_calls = []
    accepted = pilot(capture=lambda: accepted_calls.append("identity") or identity(),
                     transport=lambda request, limits: accepted_calls.append("transport") or response(),
                     limits=PilotLimits(max_calls=1, max_input_bytes=request_size,
                                        max_output_bytes=4096))
    assert accepted.complete(messages).content == "ok"
    assert accepted_calls == ["identity", "transport", "identity"]

    refused_calls = []
    refused = pilot(capture=lambda: refused_calls.append("identity") or identity(),
                    transport=lambda request, limits: refused_calls.append("transport") or response(),
                    limits=PilotLimits(max_calls=1, max_input_bytes=request_size - 1,
                                       max_output_bytes=4096))
    assert refused.complete(messages).content == "pilot_refusal: input_limit_exceeded"
    assert refused.allowance.used == 0 and refused_calls == []
    assert refused.receipts[-1].inference_started is False
    assert refused.complete(messages).content == "pilot_refusal: transport_latched"


def test_direct_evidence_limit_accepts_exact_size_and_refuses_plus_one_before_dispatch():
    accepted_messages = [Message(role="tool", content="é", tool_call_id="one", name="read_file")]
    refused_messages = [Message(role="tool", content="éx", tool_call_id="one", name="read_file")]
    calls = []
    accepted = pilot(capture=lambda: calls.append("identity") or identity(),
                     transport=lambda request, limits: calls.append("transport") or response(),
                     limits=PilotLimits(max_calls=1, max_output_bytes=4096, max_evidence_bytes=2))
    assert accepted.complete(accepted_messages).content == "ok"
    assert calls == ["identity", "transport", "identity"]

    calls = []
    refused = pilot(capture=lambda: calls.append("identity") or identity(),
                    transport=lambda request, limits: calls.append("transport") or response(),
                    limits=PilotLimits(max_calls=1, max_output_bytes=4096, max_evidence_bytes=2))
    assert refused.complete(refused_messages).content == "pilot_refusal: evidence_limit_exceeded"
    assert refused.allowance.used == 0 and calls == []
    assert refused.receipts[-1].inference_started is False


def test_zero_allowance_never_captures_or_transports():
    calls = []
    item = pilot(capture=lambda: calls.append("identity") or identity(), transport=lambda *_: calls.append("transport") or b"", calls=0)
    assert complete(item).content == "pilot_refusal: live_allowance_exhausted"
    assert calls == []


def test_identity_drift_and_provider_failure_latch_with_receipts():
    before, after = identity(), identity("d" * 64)
    captures = iter([before, after])
    item = pilot(capture=lambda: next(captures))
    assert complete(item).content == "pilot_refusal: identity_drift"
    assert item.receipts[-1].before_identity == before and item.receipts[-1].after_identity == after
    assert complete(item).content == "pilot_refusal: transport_latched"


@pytest.mark.parametrize("usage,expected", [
    ({}, "model_usage_incomplete"), ({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, None),
    ({"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 3}, "model_usage_inconsistent"),
])
def test_usage_missing_zero_and_inconsistent_are_distinct(usage, expected):
    item = pilot(transport=lambda *_: response(usage=usage))
    result = complete(item)
    assert (result.content.split(": ", 1)[1] if expected else result.content) == (expected or "ok")
    assert item.receipts[-1].raw_provider_usage == usage


def test_malformed_tools_and_stop_refuse_but_preserve_usage():
    envelope = {"content": "", "tool_calls": [{"id": "1", "name": "nope", "arguments": {}}], "stop_reason": "tool_use"}
    item = pilot(transport=lambda *_: response(envelope=envelope))
    assert complete(item, [{"name": "read", "parameters": {"type": "object"}}]).content == "pilot_refusal: tool_not_offered"
    assert item.receipts[-1].usage["input_tokens"] == 2
    stopped = pilot(transport=lambda *_: response(finish="length"))
    assert complete(stopped).content == "pilot_refusal: provider_finish_not_stop"


def test_native_provider_tool_calls_are_refused_without_losing_usage():
    raw = json.dumps({"model": QWEN_MODEL, "choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}),
        "tool_calls": [{"id": "native", "function": {"name": "ignored"}}],
    }}], "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}).encode()
    item = pilot(transport=lambda *_: raw)
    assert complete(item).content == "pilot_refusal: native_tool_calls_denied"
    assert item.receipts[-1].usage["output_tokens"] == 3


def test_unknown_usage_never_fabricates_cache_counters():
    item = pilot(transport=lambda *_: b"not-json")
    assert complete(item).content == "pilot_refusal: malformed_response"
    assert item.receipts[-1].usage == {"input_tokens": None, "output_tokens": None,
                                       "cache_creation_input_tokens": None, "cache_read_input_tokens": None}


def test_constructor_rejects_nonlocal_or_keyed_specs():
    with pytest.raises(PilotRefusal):
        QwenPilot(ModelSpec("x", "openai-compat", QWEN_MODEL, "http://localhost:11434/v1"), identity(), identity)
    with pytest.raises(PilotRefusal):
        QwenPilot(ModelSpec("x", "openai-compat", QWEN_MODEL, BASE + "/v1", api_key_env="KEY"), identity(), identity)


def test_sealed_sampling_must_match_the_fixed_wire_request():
    sealed = identity()
    sealed["harness_identity"]["sampling"] = {"temperature": 1.0}
    from scripts.pilot_contract import digest_json
    sealed["fingerprint"] = digest_json({key: sealed[key] for key in ("receipt_version", "client_version", "ollama_base_url", "server_version", "model", "harness_identity")})
    with pytest.raises(PilotRefusal, match="unsupported_sampling_configuration"):
        QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, BASE + "/v1"), sealed, identity)


def test_input_and_injected_output_bounds_refuse_and_latch():
    allowance = CallAllowance(PilotLimits(max_calls=1, max_input_bytes=20, max_output_bytes=10))
    item = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, BASE + "/v1"), identity(), identity,
                     allowance, lambda *_: b"x" * 11)
    assert complete(item).content == "pilot_refusal: input_limit_exceeded"
    assert item.allowance.used == 0
    item = pilot(transport=lambda *_: b"x" * 5000)
    assert complete(item).content == "pilot_refusal: output_limit_exceeded"
    assert complete(item).content == "pilot_refusal: transport_latched"


def test_transport_timeout_refusal_is_receipted_and_latched():
    def timed_out(*_args):
        raise PilotRefusal("process_timeout")
    item = pilot(transport=timed_out)
    assert complete(item).content == "pilot_refusal: process_timeout"
    assert item.receipts[-1].failure == "process_timeout"
    assert complete(item).content == "pilot_refusal: transport_latched"


def test_identity_callback_exceptions_are_sanitized_without_transport():
    calls = []
    item = pilot(capture=lambda: (_ for _ in ()).throw(OSError("private path")),
                 transport=lambda *_: calls.append("transport") or response())
    assert complete(item).content == "pilot_refusal: identity_before_invalid"
    assert calls == []
    assert item.receipts[-1].before_identity is None


def test_post_identity_failure_preserves_known_usage_and_the_sealed_identity_is_copied():
    sealed = identity()
    captures = iter([identity(), OSError("unavailable")])
    item = pilot(capture=lambda: next(captures))
    sealed_item = QwenPilot(ModelSpec("local", "openai-compat", QWEN_MODEL, BASE + "/v1"), sealed, identity,
                            CallAllowance(PilotLimits(max_calls=1)), lambda *_: response())
    sealed["model"]["tag"] = "changed-after-construction"
    assert complete(item).content == "pilot_refusal: identity_drift"
    assert item.receipts[-1].usage["input_tokens"] == 2
    assert item.receipts[-1].raw_provider_usage["total_tokens"] == 5
    assert complete(sealed_item).content == "ok"


@pytest.mark.parametrize("raw", [
    b'{"model":"qwen3.8:latest","model":"qwen3.8:latest"}',
    b'{"model":1e999}',
])
def test_outer_strict_json_refuses_duplicate_or_nonfinite_values(raw):
    item = pilot(transport=lambda *_: raw)
    assert complete(item).content == "pilot_refusal: malformed_response"


def test_structured_content_uses_the_same_strict_json_loader_and_keeps_usage():
    raw = json.dumps({"model": QWEN_MODEL, "choices": [{"finish_reason": "stop", "message": {"content": '{"content":"a","content":"b","tool_calls":[],"stop_reason":"end_turn"}'}}],
                      "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}).encode()
    item = pilot(transport=lambda *_: raw)
    assert complete(item).content == "pilot_refusal: malformed_response"
    assert item.receipts[-1].raw_provider_usage["total_tokens"] == 5


def test_supervised_child_imports_in_its_private_environment_before_network():
    with pytest.raises(PilotRefusal, match="transport_failed"):
        pilot_qwen._child_transport(b"not-json", PilotLimits(max_calls=1, timeout_s=2))


def test_child_closing_streams_cannot_extend_the_supervisor_deadline(monkeypatch):
    actual_popen = subprocess.Popen
    def sleeping_fixture(_argv, **kwargs):
        return actual_popen([sys.executable, "-c", "import os,time; os.close(1); os.close(2); time.sleep(10)"], **kwargs)
    monkeypatch.setattr(pilot_qwen.subprocess, "Popen", sleeping_fixture)
    started = time.monotonic()
    with pytest.raises(PilotRefusal, match="process_timeout"):
        pilot_qwen._child_transport(b"{}", PilotLimits(max_calls=1, timeout_s=0.05))
    assert time.monotonic() - started < 1.0
