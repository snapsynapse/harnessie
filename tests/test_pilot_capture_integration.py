"""Offline capture/adapter/ledger checks. No provider or network calls."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from harness.models.base import Message, ModelSpec
from scripts.pilot_capture import ResponseCaptureStore, ResponseCaptureReservation
from scripts.pilot_claude_code import ClaudeCodePilot, _RunResult
from scripts.pilot_contract import CLAUDE_MODEL, CallAllowance, PilotLimits, PilotRefusal
from scripts.pilot_live import execute_panel, _run_panel, ScriptedParticipant
from scripts.pilot_stream import parse_stream_json
from test_pilot_stream import _stream
from test_pilot_transport import AUTH_OK, _fake, _result
from test_pilot_live import prepared, identity_ready, approval
from test_pilot_integration import _claude_stream, _envelope, _qwen_payload
from scripts.pilot_execution import digest_json


def adapter(tmp_path, payload, *, failure=None, returncode=0, limit=128_000):
    directory = tmp_path.resolve()
    executable = _fake(directory)
    store = ResponseCaptureStore(directory / 'responses', limit)
    model = ClaudeCodePilot(ModelSpec('frontier', 'pilot', CLAUDE_MODEL), executable,
                            directory, CallAllowance(PilotLimits(max_calls=2, max_output_bytes=limit)),
                            capture_store=store)
    calls = []
    def run(argv, _stdin):
        if argv[1:] == ['auth', 'status', '--json']:
            return _RunResult(json.dumps(AUTH_OK).encode(), 0, None)
        calls.append('inference')
        return _RunResult(payload, returncode, failure)
    model._run = run
    return model, store, calls


@pytest.mark.parametrize('suffix', [b'', b'\n', b'not-json\n', b'\xff\n'])
def test_exact_response_saved_before_parse_and_linked_on_success_or_refusal(tmp_path, monkeypatch, suffix):
    payload = _stream() + suffix
    model, store, calls = adapter(tmp_path, payload)
    def observe_parse(raw):
        path = store.root / 'attempt-0001/stdout.bin'
        assert path.read_bytes() == raw == payload
        assert (path.parent / 'receipt.json').is_file()
        return parse_stream_json(raw)
    monkeypatch.setattr('scripts.pilot_claude_code.parse_stream_json', observe_parse)
    model.complete([Message('user', 'offline')])
    receipt = model.receipts[-1]
    assert receipt.response_capture['sha256'] == hashlib.sha256(payload).hexdigest()
    assert Path(receipt.response_capture['path']).read_bytes() == payload
    assert receipt.usage['input_tokens'] == 2
    assert 'offline' not in json.dumps(receipt.response_capture)
    assert calls == ['inference']
    if suffix:
        assert receipt.failure == 'stream_malformed'
        assert receipt.parser_diagnostic['reason']
        model.complete([Message('user', 'do not retry')])
        assert calls == ['inference']
        assert model.receipts[-1].response_capture is None
        assert model.receipts[-1].parser_diagnostic is None
    else:
        assert receipt.status == 'completed' and receipt.parser_diagnostic is None


def test_capture_reservation_failure_prevents_inference(tmp_path, monkeypatch):
    model, store, calls = adapter(tmp_path, _stream())
    monkeypatch.setattr(store, 'reserve', lambda _: (_ for _ in ()).throw(OSError('disk')))
    model.complete([Message('user', 'offline')])
    assert calls == []
    receipt = model.receipts[-1]
    assert receipt.failure == 'response_capture_failed' and not receipt.inference_started
    assert receipt.response_capture == {'status': 'failed', 'phase': 'before_inference'}


def test_capture_write_failure_keeps_usage_and_latches(tmp_path, monkeypatch):
    model, _, calls = adapter(tmp_path, _stream())
    monkeypatch.setattr(ResponseCaptureReservation, 'save',
                        lambda *a, **k: (_ for _ in ()).throw(PilotRefusal('response_capture_failed')))
    model.complete([Message('user', 'offline')])
    receipt = model.receipts[-1]
    assert receipt.failure == 'response_capture_failed'
    assert receipt.usage['input_tokens'] == 2 and receipt.inference_started
    assert receipt.response_capture['phase'] == 'after_inference'
    assert receipt.answer_model is None
    model.complete([Message('user', 'do not retry')])
    assert calls == ['inference']


@pytest.mark.parametrize('payload,failure,returncode,limit', [
    (b'partial', 'process_timeout', None, 20),
    (b'x' * 21, 'output_limit_exceeded', None, 20),
    (b'error', None, 2, 20),
    (None, 'process_start_failed', None, 20),
])
def test_failed_process_bytes_are_retained_and_never_accepted(tmp_path, payload, failure, returncode, limit):
    model, _, calls = adapter(tmp_path, payload, failure=failure, returncode=returncode, limit=limit)
    model.complete([Message('user', 'offline')])
    receipt = model.receipts[-1]
    capture = receipt.response_capture
    assert receipt.status == 'refused'
    if payload is not None:
        assert Path(capture['path']).read_bytes() == payload
    else:
        assert capture['path'] is None
    assert capture['capture_complete'] is (failure is None)
    assert calls == ['inference']


def test_real_fake_process_capture_excludes_auth_and_stderr(tmp_path):
    directory = tmp_path.resolve()
    executable = _fake(directory, result=_result({'content': 'ok', 'tool_calls': [], 'stop_reason': 'end_turn'}))
    store = ResponseCaptureStore(directory / 'responses', 128_000)
    model = ClaudeCodePilot(ModelSpec('frontier', 'pilot', CLAUDE_MODEL), executable,
                            directory, CallAllowance(PilotLimits(max_calls=1)), capture_store=store)
    assert model.complete([Message('user', 'offline')]).content == 'ok'
    payload = Path(model.receipts[-1].response_capture['path']).read_bytes()
    assert b'loggedIn' not in payload
    assert parse_stream_json(payload).failure is None
    assert len(list(store.root.iterdir())) == 1


def test_live_entry_wires_private_capture_and_keeps_it_out_of_export(tmp_path, monkeypatch):
    root, execution = prepared(tmp_path.resolve())
    identity_ready(root, execution)
    monkeypatch.setattr('scripts.pilot_preflight.claude_metadata', lambda _: execution['identities']['claude'])
    monkeypatch.setattr('scripts.pilot_preflight.local_qwen_identity', lambda *_: execution['identities']['qwen'])
    calls = {'claude': 0, 'qwen': 0}
    def fake_run(self, argv, stdin):
        if argv[1:] == ['auth', 'status', '--json']:
            return _RunResult(json.dumps(AUTH_OK).encode(), 0, None)
        calls['claude'] += 1
        return _RunResult(_claude_stream(_envelope('claude', calls['claude'])), 0, None)
    def fake_qwen(*_):
        calls['qwen'] += 1
        return _qwen_payload(_envelope('qwen', calls['qwen']))
    monkeypatch.setattr(ClaudeCodePilot, '_run', fake_run)
    monkeypatch.setattr('scripts.pilot_qwen._child_transport', fake_qwen)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        outcome = execute_panel(root, execution, approval(execution), digest_json(execution))
    assert outcome['status'] == 'needs_arbitration', outcome
    assert calls == {'claude': 4, 'qwen': 4}
    assert outcome['resume_calls'] == 0
    operator = root / execution['outputs']['ledger']
    rows = [json.loads(line) for line in (operator / 'ledger.jsonl').read_text().splitlines()]
    receipts = [r['data']['receipt'] for r in rows if r['kind'] == 'receipt' and r['data']['participant'] == 'claude']
    assert len(receipts) == 4
    for r in receipts:
        c = r['response_capture']; assert c['status'] == 'retained'
        payload = Path(c['path']).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == c['sha256']
        assert parse_stream_json(payload).failure is None
    export_root = root / 'runs' / execution['run_id'] / 'open-export'
    assert not list(export_root.rglob('stdout.bin'))


def test_capture_failure_receipt_is_durable_and_stops_other_participant(tmp_path, monkeypatch):
    root, execution = prepared(tmp_path.resolve())
    model, _, calls = adapter(tmp_path.resolve(), _stream())
    monkeypatch.setattr(ResponseCaptureReservation, 'save',
                        lambda *a, **k: (_ for _ in ()).throw(PilotRefusal('response_capture_failed')))
    outcome = _run_panel(root, execution, {'claude': lambda: model,
                         'qwen': lambda: ScriptedParticipant('qwen')}, offline=True)
    assert outcome['status'] == 'incomplete'
    assert calls == ['inference']
    assert outcome['ledger']['calls'] == {'claude': 1, 'qwen': 0}
    assert outcome['ledger']['usage']['input_tokens'] == 2
    rows = [json.loads(line) for line in (root / execution['outputs']['ledger'] / 'ledger.jsonl').read_text().splitlines()]
    receipt = next(r['data']['receipt'] for r in rows if r['kind'] == 'receipt')
    assert receipt['failure'] == 'response_capture_failed'
    assert receipt['response_capture']['status'] == 'failed'
