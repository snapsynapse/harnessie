"""Deterministic offline replay race; synthetic conversations, no sockets."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
from unittest.mock import patch
from harness.models import Message, ModelSpec, OpenAIResponsesModel

class Response:
    def __init__(self, label):
        self.label = label
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return json.dumps({'status': 'completed', 'output': [{'type': 'message',
            'role': 'assistant', 'content': [{'type': 'output_text', 'text': self.label}]}],
            'usage': {'input_tokens': 1, 'output_tokens': 1}}).encode()

def main():
    model = OpenAIResponsesModel(ModelSpec(name='mid', provider='openai-responses',
        model_id='synthetic', base_url='https://origin.invalid'))
    a = [Message('system', 'synthetic_A_system'), Message('user', 'synthetic_A_private')]
    b = [Message('system', 'synthetic_B_system'), Message('user', 'synthetic_B_private')]
    a_entered = threading.Event()
    b_finished = threading.Event()
    calls = []
    lock = threading.Lock()
    def fake_urlopen(request, timeout):
        body = json.loads(request.data)
        with lock:
            calls.append(body)
            index = len(calls)
        if index == 1:
            a_entered.set()
            assert b_finished.wait(5), 'fixture deadline'
        return Response(f'synthetic_output_{index}')
    def run_b():
        try:
            return model.complete(b)
        finally:
            b_finished.set()
    with patch('urllib.request.urlopen', side_effect=fake_urlopen):
        with ThreadPoolExecutor(max_workers=2) as pool:
            fa = pool.submit(model.complete, a)
            assert a_entered.wait(5), 'fixture deadline'
            fb = pool.submit(run_b)
            fa.result(timeout=5)
            fb.result(timeout=5)
        b.append(Message('user', 'synthetic_B_followup'))
        model.complete(b)
    third = json.dumps(calls[2])
    print(json.dumps({'schema': 'harnessie-responses-race-audit/1', 'network_calls': 0,
        'provider_calls': 0, 'parallel_calls': 2,
        'b_followup_contains_a_private_input': 'synthetic_A_private' in third,
        'b_followup_omits_b_original_input': 'synthetic_B_private' not in third,
        'b_followup_present': 'synthetic_B_followup' in third,
        'instructions_still_b': calls[2]['instructions'] == 'synthetic_B_system'},
        indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
