"""Offline v6 shape diagnosis, not approval of a wider stream contract.

All content and identifiers below are synthetic. No captured private content is
retained. Assertions characterize current refusal and accounting behavior;
they do not specify or authorize a broader acceptance contract.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_claude_code import ClaudeCodePilot, _RunResult
from scripts.pilot_contract import CLAUDE_MODEL, CallAllowance, PilotLimits
from scripts.pilot_stream import parse_stream_json


def synthetic_v6_events():
    output = {'content': '', 'tool_calls': [{'id': 'done-synthetic', 'name': 'task_complete',
              'arguments': {'report': '{"stance":"recommend","summary":"SYNTHETIC ONLY"}'}}],
              'stop_reason': 'tool_use'}
    assistant = {'type': 'assistant', 'session_id': 'session-synthetic',
                 'parent_tool_use_id': None, 'request_id': 'request-one',
                 'message': {'role': 'assistant', 'model': CLAUDE_MODEL, 'id': 'message-one',
                             'content': [{'type': 'text', 'text': 'Synthetic preliminary answer.'}]}}
    formatter = copy.deepcopy(assistant)
    formatter['request_id'] = 'request-two'
    formatter['message']['id'] = 'message-two'
    formatter['message']['content'] = [{'type': 'tool_use', 'id': 'format-synthetic',
                                       'name': 'StructuredOutput', 'input': output}]
    return [
        {'type': 'system', 'subtype': 'init', 'session_id': 'session-synthetic',
         'tools': ['StructuredOutput'], 'mcp_servers': [], 'model': CLAUDE_MODEL},
        assistant,
        {'type': 'user', 'session_id': 'session-synthetic', 'parent_tool_use_id': None,
         'isSynthetic': True, 'message': {'role': 'user', 'content': [
             {'type': 'text', 'text': 'Synthetic formatting request.'}]}},
        formatter,
        {'type': 'user', 'session_id': 'session-synthetic', 'parent_tool_use_id': None,
         'tool_use_result': 'Structured output provided successfully',
         'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'format-synthetic',
                                  'content': 'Structured output provided successfully'}]}},
        {'type': 'result', 'session_id': 'session-synthetic', 'is_error': False,
         'subtype': 'success', 'terminal_reason': 'completed',
         'modelUsage': {CLAUDE_MODEL: {'inputTokens': 1, 'outputTokens': 6740,
                        'cacheCreationInputTokens': 0, 'cacheReadInputTokens': 0}},
         'structured_output': output, 'result': json.dumps(output)},
    ]


def encode(events):
    return b''.join(json.dumps(event).encode() + b'\n' for event in events)


def test_characterize_full_v6_shape_refuses_identity_conflict():
    assert parse_stream_json(encode(synthetic_v6_events())).failure == 'conflicting_model_evidence'


def single_identity_events(*, include_synthetic_user=False):
    events = synthetic_v6_events()
    events[3]['request_id'] = events[1]['request_id']
    events[3]['message']['id'] = events[1]['message']['id']
    if not include_synthetic_user:
        events.pop(2)
    return events


@pytest.mark.parametrize('mutation, expected', [
    ('none', None),
    ('message_id', 'conflicting_model_evidence'),
    ('request_id', 'conflicting_model_evidence'),
    ('synthetic_user', 'tool_result_binding_invalid'),
])
def test_characterize_one_variable_against_single_identity_control(mutation, expected):
    events = single_identity_events(include_synthetic_user=mutation == 'synthetic_user')
    if mutation == 'message_id':
        events[2]['message']['id'] = 'message-two'
    if mutation == 'request_id':
        events[2]['request_id'] = 'request-two'
    capture = parse_stream_json(encode(events))
    assert capture.failure == expected
    assert capture.usage_totals['output_tokens'] == 6740


def test_characterize_identity_only_normalization_exposes_next_refusal():
    capture = parse_stream_json(encode(single_identity_events(include_synthetic_user=True)))
    assert capture.failure == 'tool_result_binding_invalid'
    assert capture.diagnostic['reason'] == 'tool_result_order_or_parent_invalid'


def test_characterize_removing_only_synthetic_user_does_not_fix_identity_conflict():
    events = synthetic_v6_events()
    events.pop(2)
    assert parse_stream_json(encode(events)).failure == 'conflicting_model_evidence'


def test_characterize_replacing_preliminary_text_with_opaque_thinking():
    events = synthetic_v6_events()
    events[1]['message']['content'] = [{'type': 'thinking', 'thinking': 'SYNTHETIC ONLY',
                                       'signature': 'synthetic-signature'}]
    assert parse_stream_json(encode(events)).failure == 'conflicting_model_evidence'


class InjectedOutput(ClaudeCodePilot):
    """Uses the real adapter admission path with no subprocess or provider."""

    def __init__(self, root, response):
        super().__init__(ModelSpec('diagnosis', 'pilot', CLAUDE_MODEL),
                         Path(sys.executable).resolve(), root,
                         CallAllowance(PilotLimits(max_calls=1, max_output_tokens=4096)))
        self.response = response
        self.inferences = 0

    def _run(self, argv, stdin):
        if argv[1:] == ['auth', 'status', '--json']:
            return _RunResult(json.dumps({'loggedIn': True, 'authMethod': 'oauth_token',
                                         'apiProvider': 'firstParty'}).encode(), 0, None)
        self.inferences += 1
        return _RunResult(self.response, 0, None)


def test_characterize_output_request_is_not_post_response_token_cap(tmp_path):
    # Current behavior, not an assertion that over-limit acceptance is desirable.
    adapter = InjectedOutput(tmp_path, encode(single_identity_events()))
    assert adapter._sanitized_env()['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] == '4096'
    tools = [{'name': 'task_complete', 'parameters': {'type': 'object',
              'properties': {'report': {'type': 'string'}}, 'required': ['report']}}]
    turn = adapter.complete([Message(role='user', content='SYNTHETIC ONLY')], tools)
    assert turn.stop_reason == 'tool_use'
    assert turn.output_tokens == 6740
    assert adapter.receipts[-1].status == 'completed'
    assert adapter.receipts[-1].usage['output_tokens'] == 6740
    assert adapter.inferences == 1
