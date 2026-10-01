from __future__ import annotations

import json
from pathlib import Path
import stat
import time

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_claude_code import AUTH_CLASS, CLI_STDIN_PROMPT, ClaudeCodePilot
from scripts.pilot_contract import CLAUDE_MODEL, CallAllowance, PilotLimits, PilotRefusal
from scripts.pilot_policy import (
    CLAUDE_MAX_HAIKU_CONTEXT,
    CLAUDE_MAX_HAIKU_OVERHEAD,
    CONTEXT_HAIKU_INPUT_PER_CALL,
    CONTEXT_HAIKU_OUTPUT_PER_CALL,
    HAIKU_MODEL,
    PilotPolicy,
    PolicyDecision,
)


CURRENT_OAUTH_OK = {"loggedIn": True, "authMethod": "oauth_token", "apiProvider": "firstParty"}
AUTH_OK = CURRENT_OAUTH_OK


def _result(envelope=None, *, model=CLAUDE_MODEL, usage=None):
    data = {"modelUsage": {model: {"inputTokens": 3, "outputTokens": 5,
                                     "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}
                            if usage is None else usage}}
    if envelope is not None:
        data["structured_output"] = envelope
    return data


def _fake(tmp_path: Path, auth=AUTH_OK, result=None, results=None, exit_code=0, noisy=0, sleep=0, log=None, orphan_pid=None, orphan_survived=None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "fake-claude"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys, time\n"
        f"AUTH = {auth!r}\nRESULT = {result!r}\nRESULTS = {results!r}\nEXIT = {exit_code!r}\nNOISY = {noisy!r}\nSLEEP = {sleep!r}\nLOG = {str(log) if log else None!r}\nORPHAN_PID = {str(orphan_pid) if orphan_pid else None!r}\nORPHAN_SURVIVED = {str(orphan_survived) if orphan_survived else None!r}\nCOUNT = {str(tmp_path / 'inference-count')!r}\nFABLE = {CLAUDE_MODEL!r}\n"
        "def emit(data):\n"
        "  if not isinstance(data,dict): print(json.dumps(data)); return\n"
        "  output=data.get('structured_output') if isinstance(data.get('structured_output'),dict) else {}\n"
        "  usage=data.get('modelUsage') if isinstance(data.get('modelUsage'),dict) else {}\n"
        "  model=next(iter(usage),FABLE)\n"
        "  session='fake-session'; tool='format-1'\n"
        "  events=[{'type':'system','subtype':'init','session_id':session,'tools':['StructuredOutput'],'mcp_servers':[],'model':model},{'type':'assistant','session_id':session,'parent_tool_use_id':None,'request_id':'request-1','message':{'role':'assistant','model':model,'id':'message-1','content':[{'type':'tool_use','id':tool,'name':'StructuredOutput','input':output}]}},{'type':'user','session_id':session,'parent_tool_use_id':None,'tool_use_result':'Structured output provided successfully','message':{'content':[{'type':'tool_result','tool_use_id':tool,'content':'Structured output provided successfully'}]}}]\n"
        "  terminal=dict(data); terminal.update({'type':'result','session_id':session,'is_error':data.get('is_error',False),'subtype':data.get('subtype','success'),'terminal_reason':data.get('terminal_reason','completed'),'modelUsage':usage,'structured_output':output,'result':json.dumps(output)})\n"
        "  events.append(terminal)\n"
        "  for event in events: print(json.dumps(event))\n"
        "if LOG:\n"
        "  config=sys.argv[sys.argv.index('--mcp-config')+1] if '--mcp-config' in sys.argv else None\n"
        "  with open(LOG,'a') as handle: handle.write(json.dumps({'argv':sys.argv[1:],'env':dict(os.environ),'stdin':sys.stdin.read(),'mcp_config':json.load(open(config)) if config else None})+'\\n')\n"
        "if 'auth' in sys.argv:\n"
        "  if sys.argv[1:] != ['auth','status','--json']: raise SystemExit(32)\n"
        "  print(json.dumps(AUTH)); raise SystemExit(0)\n"
        "if ORPHAN_PID:\n"
        "  import subprocess\n"
        "  child=subprocess.Popen([sys.executable,'-c',\"import os,sys,time;open(sys.argv[1],'w').write(str(os.getpid()));time.sleep(.45);open(sys.argv[2],'w').write('survived');time.sleep(5)\",ORPHAN_PID,ORPHAN_SURVIVED])\n"
        "if SLEEP: time.sleep(SLEEP)\n"
        "if NOISY: sys.stdout.write('x'*NOISY); sys.stdout.flush()\n"
        "elif RESULTS is not None:\n"
        "  n=int(open(COUNT).read()) if os.path.exists(COUNT) else 0\n"
        "  open(COUNT,'w').write(str(n+1)); emit(RESULTS[min(n,len(RESULTS)-1)])\n"
        "elif RESULT is not None: emit(RESULT)\n"
        "raise SystemExit(EXIT)\n",
        encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def _pilot(tmp_path, executable, *, calls=1, output=4096, timeout=1, env=None, policy=None,
           input_bytes=256_000, evidence_bytes=256_000):
    kwargs = {"env": env}
    if policy is not None:
        kwargs["policy"] = policy
    return ClaudeCodePilot(
        ModelSpec(name="pilot", provider="pilot", model_id=CLAUDE_MODEL), executable, tmp_path,
        allowance=CallAllowance(PilotLimits(
            max_calls=calls,
            timeout_s=timeout,
            max_input_bytes=input_bytes,
            max_evidence_bytes=evidence_bytes,
            max_output_bytes=output,
        )), **kwargs)


def _complete(pilot, tools=None):
    return pilot.complete([Message(role="user", content="hello")], tools=tools, effort="high")


def _usage(input_tokens=None, output_tokens=None, cache_creation=None, cache_read=None):
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
    }


def test_default_allowance_refuses_without_launch(tmp_path):
    log = tmp_path / "log"
    fake = _fake(tmp_path, log=log)
    pilot = _pilot(tmp_path, fake, calls=0)
    turn = _complete(pilot)
    assert turn.stop_reason == "error"
    assert turn.content == "pilot_refusal: live_allowance_exhausted"
    assert not log.exists()


def test_auth_must_be_first_party_max_before_inference(tmp_path):
    fake = _fake(tmp_path, auth={**AUTH_OK, "authMethod": "api_key"})
    pilot = _pilot(tmp_path, fake, calls=1)
    turn = _complete(pilot)
    assert turn.content == "pilot_refusal: auth_ineligible"
    assert pilot.allowance.used == 1
    assert pilot.receipts[-1].inference_started is False
    assert pilot.receipts[-1].auth_class is None


def test_current_first_party_oauth_status_is_eligible_without_claiming_max():
    assert ClaudeCodePilot._auth_class(CURRENT_OAUTH_OK) == "claude.ai:oauth:firstParty"
    assert ClaudeCodePilot._auth_class({
        "loggedIn": True, "authMethod": "claude.ai",
        "subscriptionType": "max", "apiProvider": "firstParty",
    }) == "claude.ai:max:firstParty"


@pytest.mark.parametrize("auth", [
    {"loggedIn": True, "authMethod": "api_key", "apiProvider": "firstParty"},
    {"loggedIn": True, "authMethod": "oauth_token", "apiProvider": "bedrock"},
    {"loggedIn": False, "authMethod": "oauth_token", "apiProvider": "firstParty"},
])
def test_api_key_third_party_and_logged_out_statuses_are_ineligible(auth):
    assert ClaudeCodePilot._auth_class(auth) is None


def test_bound_auth_class_drift_refuses_before_inference(tmp_path):
    log = tmp_path / "log"
    legacy = {"loggedIn": True, "authMethod": "claude.ai",
              "subscriptionType": "max", "apiProvider": "firstParty"}
    fake = _fake(tmp_path, auth=legacy,
                 result=_result({"content": "must not run", "tool_calls": [],
                                 "stop_reason": "end_turn"}), log=log)
    pilot = ClaudeCodePilot(
        ModelSpec(name="pilot", provider="pilot", model_id=CLAUDE_MODEL), fake, tmp_path,
        allowance=CallAllowance(PilotLimits(max_calls=1)),
        expected_auth_class="claude.ai:oauth:firstParty",
    )
    turn = _complete(pilot)
    assert turn.content == "pilot_refusal: auth_identity_drift"
    assert pilot.receipts[-1].inference_started is False
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert [entry["argv"] for entry in entries] == [["auth", "status", "--json"]]


def test_safe_argv_and_environment_are_isolated(tmp_path, monkeypatch):
    log = tmp_path / "log"
    blocked = {
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
        "AWS_ACCESS_KEY_ID", "AWS_PROFILE", "GOOGLE_APPLICATION_CREDENTIALS",
    }
    for name in blocked:
        monkeypatch.setenv(name, "must-not-cross")
    monkeypatch.setenv("USER", "retained-pilot-user")
    monkeypatch.setenv("FAKE_LOG", str(log))
    fake = _fake(tmp_path, result=_result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}), log=log)
    pilot = _pilot(tmp_path, fake, env={name: "also-not" for name in blocked} | {"AWS_REGION": "no"})
    assert _complete(pilot).content == "ok"
    auth_entry, inference_entry = [json.loads(line) for line in log.read_text().splitlines()]
    argv = inference_entry["argv"]
    assert "--safe-mode" in argv and "--strict-mcp-config" in argv
    assert "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    assert "--setting-sources" in argv and argv[argv.index("--setting-sources") + 1] == ""
    assert argv.count("--verbose") == 1 and argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--bare" not in argv
    assert argv[-2:] == ["--print", CLI_STDIN_PROMPT]
    assert blocked.isdisjoint(inference_entry["env"]) and "AWS_REGION" not in inference_entry["env"]
    assert inference_entry["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "4096"
    assert inference_entry["env"]["USER"] == "retained-pilot-user"
    assert inference_entry["mcp_config"] == {"mcpServers": {}}
    assert auth_entry["argv"] == ["auth", "status", "--json"]
    assert json.loads(inference_entry["stdin"])["messages"][0]["content"] == "hello"


def test_prepared_unicode_and_tool_result_bytes_are_exact_inference_stdin(tmp_path):
    log = tmp_path / "log"
    fake = _fake(
        tmp_path,
        result=_result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}),
        log=log,
    )
    pilot = _pilot(tmp_path, fake)
    messages = [
        Message(role="user", content="Read café ☕"),
        Message(role="assistant"),
        Message(role="tool", tool_call_id="read-1", name="read_file",
                content="résultat: 雪\nline two"),
    ]
    tools = [{"name": "read_file", "description": "read", "parameters": {"type": "object"}}]
    prepared = pilot.prepare_request(messages, tools, "high")

    assert prepared.transport == "claude-code-max-pilot"
    assert prepared.encoding == "claude_code_stdin_neutral_json"
    assert prepared.inner_prompt_bytes is None
    assert prepared.request == pilot._request_prompt(messages, tools).encode("utf-8")
    assert pilot.complete_prepared(prepared, tools, "high").content == "ok"
    _, inference_entry = [json.loads(line) for line in log.read_text().splitlines()]
    assert inference_entry["stdin"].encode("utf-8") == prepared.request


def test_input_limit_accepts_exact_bytes_and_refuses_plus_one_before_launch(tmp_path):
    messages = [Message(role="user", content="x")]
    size = len(ClaudeCodePilot._request_prompt(messages, []).encode("utf-8"))

    accepted_dir = tmp_path / "accepted"
    accepted_log = accepted_dir / "log"
    accepted = _pilot(
        accepted_dir,
        _fake(accepted_dir, result=_result({"content": "ok", "tool_calls": [],
                                            "stop_reason": "end_turn"}), log=accepted_log),
        input_bytes=size,
    )
    assert accepted.complete(messages).content == "ok"
    assert accepted.allowance.used == 1

    refused_dir = tmp_path / "refused"
    refused_log = refused_dir / "log"
    refused = _pilot(refused_dir, _fake(refused_dir, log=refused_log), input_bytes=size)
    assert refused.complete([Message(role="user", content="xx")]).content == \
        "pilot_refusal: input_limit_exceeded"
    assert refused.allowance.used == 0
    assert not refused_log.exists()
    assert refused.receipts[-1].attempt is None
    assert refused.receipts[-1].inference_started is False


def test_evidence_limit_accepts_exact_bytes_and_refuses_plus_one_before_launch(tmp_path):
    evidence = "résultat"
    evidence_bytes = len(evidence.encode("utf-8"))
    messages = [Message(role="tool", tool_call_id="read-1", name="read_file", content=evidence)]

    accepted_dir = tmp_path / "accepted"
    accepted = _pilot(
        accepted_dir,
        _fake(accepted_dir, result=_result({"content": "ok", "tool_calls": [],
                                            "stop_reason": "end_turn"})),
        evidence_bytes=evidence_bytes,
    )
    assert accepted.complete(messages).content == "ok"
    assert accepted.allowance.used == 1

    refused_dir = tmp_path / "refused"
    refused_log = refused_dir / "log"
    refused = _pilot(
        refused_dir,
        _fake(refused_dir, log=refused_log),
        evidence_bytes=evidence_bytes,
    )
    refused_messages = [Message(role="tool", tool_call_id="read-1", name="read_file",
                                content=evidence + "x")]
    assert refused.complete(refused_messages).content == "pilot_refusal: evidence_limit_exceeded"
    assert refused.allowance.used == 0
    assert not refused_log.exists()
    assert refused.receipts[-1].attempt is None
    assert refused.receipts[-1].inference_started is False


def test_malformed_request_remains_a_stable_prelaunch_refusal(tmp_path):
    log = tmp_path / "log"
    pilot = _pilot(tmp_path, _fake(tmp_path, log=log))
    turn = pilot.complete([object()])  # type: ignore[list-item]
    assert turn.content == "pilot_refusal: invalid_request"
    assert pilot.allowance.used == 0
    assert not log.exists()
    assert pilot.receipts[-1].attempt is None
    assert pilot.receipts[-1].inference_started is False


def test_tool_round_trip_is_structured_and_harness_owned(tmp_path):
    fake = _fake(tmp_path, result=_result({"content": "", "tool_calls": [
        {"id": "call_1", "name": "read_file", "arguments": {"path": "README.md"}}], "stop_reason": "tool_use"}))
    pilot = _pilot(tmp_path, fake)
    turn = _complete(pilot, [{"name": "read_file", "description": "read", "parameters": {"type": "object"}}])
    assert turn.stop_reason == "tool_use"
    assert [(call.name, call.arguments) for call in turn.tool_calls] == [("read_file", {"path": "README.md"})]
    assert pilot.receipts[-1].auth_class == AUTH_CLASS
    assert pilot.receipts[-1].dollar_cost is None


def test_neutral_read_then_task_complete_round_trip(tmp_path):
    tools = [
        {"name": "read_file", "description": "read", "parameters": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}},
        {"name": "task_complete", "description": "finish", "parameters": {"type": "object", "required": ["report"], "properties": {"report": {"type": "string"}}}},
    ]
    fake = _fake(tmp_path, results=[
        _result({"content": "", "tool_calls": [{"id": "read_1", "name": "read_file", "arguments": {"path": "README.md"}}], "stop_reason": "tool_use"}),
        _result({"content": "", "tool_calls": [{"id": "done_1", "name": "task_complete", "arguments": {"report": "checked"}}], "stop_reason": "tool_use"}),
    ])
    pilot = _pilot(tmp_path, fake, calls=2)
    first = _complete(pilot, tools)
    second = pilot.complete([
        Message(role="user", content="read then finish"),
        Message(role="assistant", tool_calls=first.tool_calls),
        Message(role="tool", tool_call_id="read_1", name="read_file", content="contents"),
    ], tools=tools)
    assert first.tool_calls[0].name == "read_file"
    assert second.tool_calls[0].name == "task_complete"
    assert pilot.allowance.used == 2
    assert [receipt.status for receipt in pilot.receipts] == ["completed", "completed"]


def test_malformed_nonzero_and_latched_failures_do_not_retry(tmp_path):
    fake = _fake(tmp_path, result={"modelUsage": {CLAUDE_MODEL: {"inputTokens": 7}}}, exit_code=7)
    pilot = _pilot(tmp_path, fake)
    first = _complete(pilot)
    second = _complete(pilot)
    assert first.content == "pilot_refusal: process_failed"
    assert second.content == "pilot_refusal: transport_latched"
    assert pilot.allowance.used == 1
    assert pilot.receipts[0].inference_started is True
    assert pilot.receipts[0].usage == _usage(7, None)


def test_unknown_mismatch_fallback_and_invalid_arguments_refuse(tmp_path):
    cases = [
        (_result({"content": "", "tool_calls": [], "stop_reason": "end_turn"}, model="other"), "model_identity_mismatch"),
        ({"structured_output": {"content": "", "tool_calls": [], "stop_reason": "end_turn"}}, "model_usage_missing"),
        ({"modelUsage": {CLAUDE_MODEL: {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}, "fallback": {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}}, "structured_output": {"content": "", "tool_calls": [], "stop_reason": "end_turn"}}, "additional_model_usage_unapproved"),
        (_result({"content": "", "tool_calls": [{"id": "1", "name": "other", "arguments": {}}], "stop_reason": "tool_use"}), "tool_not_offered"),
        (_result({"content": "", "tool_calls": [{"id": "1", "name": "read", "arguments": "{"}], "stop_reason": "tool_use"}), "malformed_tool_arguments"),
    ]
    for idx, (result, expected) in enumerate(cases):
        case_dir = tmp_path / str(idx)
        case_dir.mkdir()
        pilot = _pilot(case_dir, _fake(case_dir, result=result))
        turn = _complete(pilot, [{"name": "read", "parameters": {"type": "object"}}])
        assert turn.content == f"pilot_refusal: {expected}"


def test_missing_and_zero_usage_are_distinct(tmp_path):
    missing = _pilot(tmp_path / "missing", _fake(tmp_path / "missing", result=_result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}, usage={})))
    assert _complete(missing).content == "pilot_refusal: model_usage_incomplete"
    assert missing.receipts[-1].usage == _usage()
    zero_dir = tmp_path / "zero"
    zero_dir.mkdir()
    zero = _pilot(zero_dir, _fake(zero_dir, result=_result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}, usage={"inputTokens": 0, "outputTokens": 0, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0})))
    assert _complete(zero).content == "ok"
    assert zero.receipts[-1].usage == _usage(0, 0, 0, 0)


def test_timeout_and_output_overflow_kill_the_attempt(tmp_path):
    slow_dir = tmp_path / "slow"
    slow_dir.mkdir()
    slow = _pilot(slow_dir, _fake(slow_dir, result=_result(), sleep=0.3), timeout=0.05)
    assert _complete(slow).content == "pilot_refusal: process_timeout"
    loud_dir = tmp_path / "loud"
    loud_dir.mkdir()
    loud = _pilot(loud_dir, _fake(loud_dir, noisy=10000), output=100)
    assert _complete(loud).content == "pilot_refusal: output_limit_exceeded"


def test_malformed_response_and_input_bound_are_sanitized(tmp_path):
    malformed_dir = tmp_path / "malformed"
    malformed = _pilot(malformed_dir, _fake(malformed_dir, result={"modelUsage": {CLAUDE_MODEL: {"inputTokens": 11, "outputTokens": 1, "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0}}}))
    assert _complete(malformed).content == "pilot_refusal: malformed_response"
    assert malformed.receipts[-1].usage == _usage(11, 1, 0, 0)
    bounded_dir = tmp_path / "bounded"
    fake = _fake(bounded_dir, result=_result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}))
    pilot = ClaudeCodePilot(
        ModelSpec(name="pilot", provider="pilot", model_id=CLAUDE_MODEL), fake, bounded_dir,
        allowance=CallAllowance(PilotLimits(max_calls=1, max_input_bytes=20)),
    )
    assert pilot.complete([Message(role="user", content="x" * 100)]).content == "pilot_refusal: input_limit_exceeded"


def test_success_requires_primary_usage_and_preserves_cache_usage(tmp_path):
    result = _result(
        {"content": "ok", "tool_calls": [], "stop_reason": "end_turn"},
        usage={"inputTokens": 2, "outputTokens": 3,
               "cacheCreationInputTokens": 5, "cacheReadInputTokens": 7},
    )
    pilot = _pilot(tmp_path, _fake(tmp_path, result=result))
    turn = _complete(pilot)
    assert turn.content == "ok"
    assert pilot.receipts[-1].usage == _usage(2, 3, 5, 7)


def test_extra_model_usage_refuses_but_preserves_account_totals_and_raw_metadata(tmp_path):
    result = _result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"})
    result["modelUsage"] = {
        CLAUDE_MODEL: {"inputTokens": 2, "outputTokens": 135,
                       "cacheCreationInputTokens": 585, "cacheReadInputTokens": 3706,
                       "costUSD": 0.0193965, "canonicalModel": CLAUDE_MODEL},
        "claude-haiku-4-5-20251001": {"inputTokens": 989, "outputTokens": 16,
                                        "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0,
                                        "costUSD": 0.001069, "canonicalModel": "claude-haiku-4-5"},
    }
    pilot = _pilot(tmp_path, _fake(tmp_path, result=result))
    turn = _complete(pilot)
    receipt = pilot.receipts[-1]
    assert turn.content == "pilot_refusal: additional_model_usage_unapproved"
    assert receipt.answer_model == CLAUDE_MODEL
    assert receipt.usage == _usage(991, 151, 585, 3706)
    assert receipt.reported_model_usages[0]["claude-haiku-4-5-20251001"]["costUSD"] == 0.001069


def test_opt_in_policy_accepts_only_bounded_unclassified_haiku(tmp_path):
    result = _result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"})
    result["modelUsage"] = {
        CLAUDE_MODEL: {"inputTokens": 2, "outputTokens": 135, "cacheCreationInputTokens": 585,
                       "cacheReadInputTokens": 3706, "provider": "firstParty"},
        HAIKU_MODEL: {"inputTokens": 989, "outputTokens": 16, "cacheCreationInputTokens": 0,
                      "cacheReadInputTokens": 0, "webSearchRequests": 0, "provider": "firstParty"},
    }
    default = _pilot(tmp_path / "default", _fake(tmp_path / "default", result=result))
    assert _complete(default).content == "pilot_refusal: additional_model_usage_unapproved"
    accepted_dir = tmp_path / "accepted"
    accepted = _pilot(accepted_dir, _fake(accepted_dir, result=result), policy=CLAUDE_MAX_HAIKU_OVERHEAD)
    assert _complete(accepted).content == "ok"
    receipt = accepted.receipts[-1]
    assert receipt.answer_model == CLAUDE_MODEL
    assert receipt.policy_id == "claude-max-haiku-overhead/v1"
    assert receipt.policy_disposition == "unclassified"
    assert receipt.policy_bounds == {"haiku_input_with_cache_limit": 4096, "haiku_output_limit": 256}


def test_opt_in_overage_refuses_latches_and_keeps_raw_usage(tmp_path):
    result = _result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"})
    result["modelUsage"] = {
        CLAUDE_MODEL: {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0,
                       "cacheReadInputTokens": 0, "provider": "firstParty"},
        HAIKU_MODEL: {"inputTokens": 4097, "outputTokens": 256, "cacheCreationInputTokens": 0,
                      "cacheReadInputTokens": 0, "webSearchRequests": 0, "provider": "firstParty"},
    }
    pilot = _pilot(tmp_path, _fake(tmp_path, result=result), calls=2, policy=CLAUDE_MAX_HAIKU_OVERHEAD)
    assert _complete(pilot).content == "pilot_refusal: additional_model_usage_bound_exceeded"
    assert _complete(pilot).content == "pilot_refusal: transport_latched"
    assert pilot.allowance.used == 1
    assert pilot.receipts[0].reported_model_usages[0][HAIKU_MODEL]["inputTokens"] == 4097
    assert pilot.receipts[0].policy_disposition == "refused_bound"


def test_context_policy_accepts_exact_limits_and_refuses_one_token_over(tmp_path):
    def result(haiku_input, haiku_output):
        value = _result({"content": "ok", "tool_calls": [], "stop_reason": "end_turn"})
        value["modelUsage"] = {
            CLAUDE_MODEL: {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 0,
                           "cacheReadInputTokens": 0, "provider": "firstParty"},
            HAIKU_MODEL: {"inputTokens": haiku_input, "outputTokens": haiku_output,
                          "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0,
                          "webSearchRequests": 0, "provider": "firstParty"},
        }
        return value

    exact_dir = tmp_path / "exact"
    exact = _pilot(exact_dir, _fake(exact_dir, result=result(
        CONTEXT_HAIKU_INPUT_PER_CALL, CONTEXT_HAIKU_OUTPUT_PER_CALL)),
        policy=CLAUDE_MAX_HAIKU_CONTEXT)
    assert _complete(exact).content == "ok"
    assert exact.receipts[-1].policy_id == "claude-max-haiku-context/v2"
    assert exact.receipts[-1].policy_disposition == "unclassified"

    over_dir = tmp_path / "over"
    over = _pilot(over_dir, _fake(over_dir, result=result(
        CONTEXT_HAIKU_INPUT_PER_CALL + 1, CONTEXT_HAIKU_OUTPUT_PER_CALL)),
        policy=CLAUDE_MAX_HAIKU_CONTEXT)
    assert _complete(over).content == "pilot_refusal: additional_model_usage_bound_exceeded"
    assert over.receipts[-1].reported_model_usages[0][HAIKU_MODEL]["inputTokens"] == (
        CONTEXT_HAIKU_INPUT_PER_CALL + 1)


def test_opt_in_zero_allowance_does_not_launch(tmp_path):
    log = tmp_path / "log"
    pilot = _pilot(tmp_path, _fake(tmp_path, log=log), calls=0, policy=CLAUDE_MAX_HAIKU_OVERHEAD)
    assert _complete(pilot).content == "pilot_refusal: live_allowance_exhausted"
    assert not log.exists()


def test_policy_subclass_cannot_relax_the_frozen_selector_before_launch(tmp_path):
    class Relaxed(PilotPolicy):
        def evaluate(self, requested_model, raw_usage, normalized_usage):
            return PolicyDecision("unclassified", None)

    log = tmp_path / "log"
    with pytest.raises(PilotRefusal, match="invalid_pilot_policy"):
        _pilot(tmp_path, _fake(tmp_path, log=log), policy=Relaxed())
    assert not log.exists()


def test_invalid_offered_schema_refuses_before_any_subprocess(tmp_path):
    log = tmp_path / "log"
    pilot = _pilot(tmp_path, _fake(tmp_path, log=log))
    turn = _complete(pilot, [{"name": "bad", "parameters": {"type": "not-a-json-schema-type"}}])
    assert turn.content == "pilot_refusal: invalid_request"
    assert not log.exists()


def test_result_status_and_terminal_stop_cannot_dispatch_tools(tmp_path):
    envelope = {"content": "", "tool_calls": [{"id": "one", "name": "read", "arguments": {}}], "stop_reason": "tool_use"}
    cases = [
        ({**_result(envelope), "is_error": True}, "provider_result_error"),
        ({**_result(envelope), "subtype": "error"}, "provider_result_error"),
        ({**_result(envelope), "subtype": "max_turns"}, "provider_result_max_turns"),
        (_result({**envelope, "stop_reason": "max_tokens"}), "tool_calls_with_terminal_stop"),
        (_result({**envelope, "stop_reason": "refusal"}), "tool_calls_with_terminal_stop"),
    ]
    for index, (result, expected) in enumerate(cases):
        case_dir = tmp_path / str(index)
        pilot = _pilot(case_dir, _fake(case_dir, result=result))
        turn = _complete(pilot, [{"name": "read", "parameters": {"type": "object"}}])
        assert turn.content == f"pilot_refusal: {expected}"


def test_tool_schema_and_duplicate_call_ids_are_rejected(tmp_path):
    tools = [{"name": "read", "parameters": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}}]
    bad_schema = _result({"content": "", "tool_calls": [{"id": "same", "name": "read", "arguments": {}}], "stop_reason": "tool_use"})
    duplicate = _result({"content": "", "tool_calls": [
        {"id": "same", "name": "read", "arguments": {"path": "a"}},
        {"id": "same", "name": "read", "arguments": {"path": "b"}},
    ], "stop_reason": "tool_use"})
    for index, (result, expected) in enumerate(((bad_schema, "tool_arguments_invalid"), (duplicate, "duplicate_tool_call_id"))):
        case_dir = tmp_path / str(index)
        pilot = _pilot(case_dir, _fake(case_dir, result=result))
        assert _complete(pilot, tools).content == f"pilot_refusal: {expected}"


def test_timeout_kills_child_when_parent_already_exited(tmp_path):
    pid_file = tmp_path / "child-pid"
    survived = tmp_path / "survived"
    pilot = _pilot(tmp_path, _fake(tmp_path, orphan_pid=pid_file, orphan_survived=survived), timeout=0.3)
    assert _complete(pilot).content == "pilot_refusal: process_timeout"
    assert pid_file.exists()
    time.sleep(0.25)
    assert not survived.exists(), "inherited-stdout child survived pilot timeout"
