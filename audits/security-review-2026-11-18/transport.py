"""Offline model-adapter audit regressions; no sockets, providers or credentials."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.request import HTTPRedirectHandler, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from harness.models import ModelSpec, OpenAIResponsesModel, OpenAICompatModel, AnthropicModel

class Response:
    def __init__(self, data):
        self.data = json.dumps(data).encode()
        self.read_calls = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, *args):
        self.read_calls.append(args)
        return self.data

def model(cls):
    return cls(ModelSpec(name='audit', provider='synthetic', model_id='synthetic',
                         base_url='https://origin.invalid', api_key_env=''))

def call(cls, data):
    response = Response(data)
    with patch('urllib.request.urlopen', return_value=response):
        turn = model(cls).complete([])
    return turn, response

def main():
    blocked = [
        (OpenAICompatModel, {'choices': [{'message': {'content': '', 'tool_calls': [
            {'id': 'synthetic', 'function': {'name': 'task_complete', 'arguments': '{"report":"synthetic"}'}}
        ]}, 'finish_reason': 'content_filter'}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}),
        (AnthropicModel, {'content': [{'type': 'tool_use', 'id': 'synthetic',
            'name': 'task_complete', 'input': {'report': 'synthetic'}}], 'stop_reason': 'refusal',
            'usage': {'input_tokens': 1, 'output_tokens': 1}}),
        (OpenAIResponsesModel, {'status': 'failed', 'output': [{'type': 'function_call',
            'call_id': 'synthetic', 'name': 'task_complete', 'arguments': '{"report":"synthetic"}'}],
            'usage': {'input_tokens': 1, 'output_tokens': 1}}),
    ]
    status_results = {}
    usage_results = {}
    read_results = {}
    for cls, data in blocked:
        turn, response = call(cls, data)
        status_results[cls.__name__] = {
            'blocked_provider_result_becomes_tool_use': turn.stop_reason == 'tool_use',
            'task_complete_retained': any(tc.name == 'task_complete' for tc in turn.tool_calls)}
        read_results[cls.__name__] = {'unbounded_success_read': response.read_calls == [()]}
        clean = dict(data)
        clean.pop('usage')
        if cls is OpenAICompatModel:
            clean['choices'] = [{'message': {'content': 'synthetic'}, 'finish_reason': 'stop'}]
        elif cls is AnthropicModel:
            clean.update(content=[{'type': 'text', 'text': 'synthetic'}], stop_reason='end_turn')
        else:
            clean.update(status='completed', output=[])
        unknown, _ = call(cls, clean)
        usage_results[cls.__name__] = {'missing_usage_accepted': unknown.stop_reason != 'error',
            'missing_usage_counted_as_zero': unknown.input_tokens == unknown.output_tokens == 0}
    request = Request('https://origin.invalid/responses', data=b'{}',
        headers={'Authorization': 'Bearer synthetic-only', 'X-api-key': 'synthetic-only',
                 'Content-Type': 'application/json'})
    redirect = HTTPRedirectHandler().redirect_request(request, None, 302, 'Found', {},
                                                     'https://other.invalid/collect')
    headers = {key.lower() for key, _ in redirect.header_items()}
    result = {'schema': 'harnessie-offline-transport-audit/1', 'network_calls': 0,
              'provider_calls': 0, 'uses_real_credentials': False,
              'blocked_status': status_results, 'unknown_usage': usage_results,
              'unbounded_read': read_results, 'cross_origin_redirect': {
                  'changes_origin': redirect.host != request.host,
                  'retains_authorization': 'authorization' in headers,
                  'retains_x_api_key': 'x-api-key' in headers}}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
