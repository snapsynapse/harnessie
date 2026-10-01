"""Offline authority, integration, failure and export checks; no live providers."""
from datetime import timedelta
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from harness.models.base import AssistantTurn
from scripts.pilot_claude_code import AUTH_CONTRACT_ID
from scripts.pilot_contract import PilotRefusal
from scripts.pilot_execution import (proposal, validate_proposal, validate_authority, digest_json,
                                     utc_now, load_json)
from scripts.pilot_live import rehearse_panel, execute_panel, _run_panel, ScriptedParticipant
from scripts.pilot_prepare import prepare_packet
from scripts.pilot_identity import capture_identity
from scripts.pilot_policy import (CLAUDE_MAX_HAIKU_CONTEXT, CONTEXT_HAIKU_INPUT_PER_RUN,
                                  CONTEXT_HAIKU_OUTPUT_PER_RUN, CONTEXT_TOTAL_TOKENS_PER_RUN)

REPO = Path(__file__).resolve().parents[1]


def prepared(tmp_path):
    root = tmp_path / 'candidate'
    packet = prepare_packet(REPO, root, live_candidate=True)
    return root, proposal(root, packet['manifest_sha256'], 'pilot-offline-test')


def approval(data):
    return {'manifest_sha256': digest_json(data), 'approved_by': 'Sam Rogers',
            'approved_at': utc_now().isoformat(), 'expires_at': data['expires_at'],
            'action': 'execute_live_panel'}


def identity_ready(root, data):
    from scripts.pilot_prepare import verify_packet
    declared = verify_packet(root, data['packet_sha256'])['participants']['qwen']['declared_harness_identity']
    def metadata(method, path, payload=None):
        return {'/api/version': {'version': 'fixture'},
                '/api/tags': {'models': [{'name': 'qwen3.8:latest', 'digest': 'a'*64, 'size': 1}]},
                '/api/show': {'details': {}, 'model_info': {}, 'capabilities': [], 'modelfile': 'FROM sha256-'+'b'*64}}[path]
    q = capture_identity(client_version='fixture', harness_identity=declared, fetch_json=metadata)
    executable = Path(sys.executable).resolve()
    c = {'model_id': 'claude-fable-5-1', 'auth_contract': AUTH_CONTRACT_ID,
         'auth_class': 'claude.ai:oauth:firstParty', 'cli_version': 'fixture',
         'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
         'checked_at': utc_now().isoformat()}
    data['identities'] = {'claude': c, 'qwen': q}
    data['billing'] = {'requirement': 'included_allowance_only', 'verified': True,
                       'included_fable_allowance': True, 'usage_credits_enabled': False,
                       'checked_at': utc_now().isoformat(), 'evidence': 'SYNTHETIC TEST ONLY'}
    return data


def test_proposal_does_not_grant_calls_and_binds_exact_inputs(tmp_path):
    root, data = prepared(tmp_path)
    assert data['policy'] == CLAUDE_MAX_HAIKU_CONTEXT.as_dict()
    assert data['limits'] == {
        'calls': {'claude': 8, 'qwen': 8}, 'calls_per_stage': 4,
        'total_tokens': CONTEXT_TOTAL_TOKENS_PER_RUN,
        'haiku_input_tokens': CONTEXT_HAIKU_INPUT_PER_RUN,
        'haiku_output_tokens': CONTEXT_HAIKU_OUTPUT_PER_RUN,
    }
    assert validate_proposal(data, root) == digest_json(data)
    with patch('scripts.pilot_preflight.claude_metadata', side_effect=AssertionError('no metadata')):
        for auth, confirm in [(None, None), (approval(data), None), (None, digest_json(data))]:
            with pytest.raises(PilotRefusal, match='live_authority_required'):
                execute_panel(root, data, auth, confirm)
    assert not (root / 'runs').exists()
    with pytest.raises(PilotRefusal, match='included_allowance_unverified'):
        validate_authority(data, root, approval(data), digest_json(data))


@pytest.mark.parametrize('field', ['policy','implementation_sha256','disclosure','response_capture'])
def test_contract_drift_refuses_before_runner(tmp_path, field):
    root, data = prepared(tmp_path)
    data[field] = {}
    with patch('scripts.pilot_live.PilotWorkflow', side_effect=AssertionError('no runner')):
        with pytest.raises(PilotRefusal):
            rehearse_panel(root, data)


def test_stale_zero_and_overlarge_limits_refuse(tmp_path):
    root, original = prepared(tmp_path)
    variants = []
    expired = copy.deepcopy(original); expired['expires_at'] = (utc_now() - timedelta(seconds=1)).isoformat(); variants.append(expired)
    for key, value in [('total_tokens', 0), ('total_tokens', CONTEXT_TOTAL_TOKENS_PER_RUN + 1),
                       ('haiku_input_tokens', CONTEXT_HAIKU_INPUT_PER_RUN + 1),
                       ('haiku_output_tokens', CONTEXT_HAIKU_OUTPUT_PER_RUN + 1),
                       ('calls_per_stage', 5),
                       ('calls_per_stage', True)]:
        data = copy.deepcopy(original); data['limits'][key] = value; variants.append(data)
    for participant in ('claude', 'qwen'):
        data = copy.deepcopy(original); data['limits']['calls'][participant] = 9; variants.append(data)
    for data in variants:
        with pytest.raises(PilotRefusal):
            rehearse_panel(root, data)


def test_lower_call_limits_remain_valid(tmp_path):
    root, data = prepared(tmp_path)
    data['limits']['calls'] = {'claude': 7, 'qwen': 6}
    data['limits']['calls_per_stage'] = 3
    assert validate_proposal(data, root) == digest_json(data)


@pytest.mark.parametrize('agree', [False, True])
def test_four_stage_real_runner_export_and_resume_are_offline(tmp_path, agree):
    root, data = prepared(tmp_path)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        result = rehearse_panel(root, data, agree=agree)
    assert result['status'] == 'needs_arbitration', result
    assert result['resume_calls'] == 0 and result['resume_status'] == 'needs_arbitration'
    assert result['ledger']['calls'] == {'claude': 4, 'qwen': 4}
    assert len(result['ledger']['calls_per_stage']) == 4
    assert result['ledger']['accounting_complete']
    assert result['ledger_integrity']['integrity'] == 'valid'
    assert result['runner_chain']['ok']
    assert 'SCRIPTED ONLY' in (root / result['export_path']).read_text()
    with pytest.raises(PilotRefusal, match='pilot_run_exists'):
        rehearse_panel(root, data)


def test_transport_failure_cannot_retry_or_start_next_participant(tmp_path):
    root, data = prepared(tmp_path)
    calls = []
    class Failed(ScriptedParticipant):
        def complete(self, *args, **kwargs):
            calls.append(self.participant)
            raise OSError('simulated uncertain result')
    result = _run_panel(root, data, {'claude': lambda: Failed('claude'),
                                    'qwen': lambda: Failed('qwen')}, offline=True)
    assert result['status'] == 'incomplete'
    assert calls == ['claude']
    assert result['ledger']['active_attempt']['state'] == 'dispatched'
    assert result['ledger']['accounting_complete'] is False
    assert result['ledger']['usage'] is None
    with pytest.raises(PilotRefusal, match='pilot_run_exists'):
        rehearse_panel(root, data)


def test_reported_failure_usage_is_preserved_and_stage_does_not_advance(tmp_path):
    root, data = prepared(tmp_path)
    class Refused(ScriptedParticipant):
        def complete(self, *args, **kwargs):
            super().complete(*args, **kwargs)
            self.receipts[-1]['status'] = 'refused'
            return AssistantTurn('refused', stop_reason='error')
    result = _run_panel(root, data, {'claude': lambda: Refused('claude'),
                                    'qwen': lambda: ScriptedParticipant('qwen')}, offline=True)
    assert result['status'] == 'incomplete'
    assert result['ledger']['calls'] == {'claude': 1, 'qwen': 0}
    assert result['ledger']['known_usage']['input_tokens'] == 10


def test_budget_is_shared_across_stages(tmp_path):
    root, data = prepared(tmp_path)
    data['limits']['total_tokens'] = 45
    result = rehearse_panel(root, data)
    assert result['status'] == 'incomplete'
    assert sum(result['ledger']['calls'].values()) == 3
    assert result['ledger']['known_usage']['input_tokens'] == 30


def test_enabled_credits_block_even_if_verified_flag_claims_success(tmp_path):
    root, data = prepared(tmp_path)
    data['billing'] = {'requirement': 'included_allowance_only', 'verified': True,
                       'included_fable_allowance': True, 'usage_credits_enabled': True,
                       'checked_at': utc_now().isoformat(), 'evidence': 'synthetic account check'}
    with pytest.raises(PilotRefusal, match='included_allowance_unverified'):
        validate_authority(data, root, approval(data), digest_json(data))


def test_first_party_oauth_never_substitutes_for_separate_billing_evidence(tmp_path):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    data['billing']['verified'] = False
    data['billing']['included_fable_allowance'] = None
    data['billing']['usage_credits_enabled'] = None
    with pytest.raises(PilotRefusal, match='included_allowance_unverified'):
        validate_authority(data, root, approval(data), digest_json(data))


def test_operator_json_rejects_duplicates_and_nonfinite(tmp_path):
    p = tmp_path / 'operator.json'
    for raw in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}']:
        p.write_text(raw)
        with pytest.raises(PilotRefusal):
            load_json(p)


def test_explicit_authority_needs_fresh_billing_exact_code_and_qwen_configuration(tmp_path):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    assert validate_authority(data, root, approval(data), digest_json(data)) == digest_json(data)
    data['billing']['checked_at'] = (utc_now() - timedelta(minutes=16)).isoformat()
    with pytest.raises(PilotRefusal, match='billing_evidence_stale'):
        validate_authority(data, root, approval(data), digest_json(data))
    identity_ready(root, data)
    data['identities']['claude']['sha256'] = '0'*64
    with pytest.raises(PilotRefusal, match='claude_executable_drift'):
        validate_authority(data, root, approval(data), digest_json(data))


@pytest.mark.parametrize(('field', 'value'), [
    ('auth_contract', 'claude-code-unknown/v1'),
    ('auth_class', 'anthropic:api-key'),
])
def test_unapproved_claude_auth_contract_or_class_refuses(field, value, tmp_path):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    data['identities']['claude'][field] = value
    with pytest.raises(PilotRefusal, match='claude_identity_unverified'):
        validate_authority(data, root, approval(data), digest_json(data))


def test_both_provider_identities_checked_before_any_panel_dispatch(tmp_path, monkeypatch):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    observed = []
    monkeypatch.setattr('scripts.pilot_preflight.claude_metadata', lambda _: observed.append('claude') or data['identities']['claude'])
    def drift(*_):
        observed.append('qwen')
        raise PilotRefusal('identity_drift')
    monkeypatch.setattr('scripts.pilot_preflight.local_qwen_identity', drift)
    monkeypatch.setattr('scripts.pilot_live._run_panel', lambda *_args, **_kwargs: pytest.fail('no dispatch'))
    with pytest.raises(PilotRefusal, match='identity_drift'):
        execute_panel(root, data, approval(data), digest_json(data))
    assert observed == ['claude','qwen']
    assert not (root / 'runs').exists()


def test_receipt_write_failure_halts_without_retry(tmp_path, monkeypatch):
    root, data = prepared(tmp_path)
    from scripts.pilot_ledger import RunLedger
    original = RunLedger._append
    def fail_receipt(self, kind, payload):
        if kind == 'receipt':
            self._halted = True
            raise PilotRefusal('ledger_io_failure')
        return original(self, kind, payload)
    monkeypatch.setattr(RunLedger, '_append', fail_receipt)
    result = rehearse_panel(root, data)
    assert result['status'] == 'incomplete'
    assert result['ledger']['calls'] == {'claude': 1, 'qwen': 0}
    assert result['ledger']['active_attempt']['state'] == 'dispatched'
    assert result['ledger']['accounting_complete'] is False
