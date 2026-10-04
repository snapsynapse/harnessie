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
                                     utc_now, load_json, EXTENDED_TIMING_POLICY, validate_start_authority)
from scripts.pilot_live import rehearse_panel, execute_panel, _run_panel, ScriptedParticipant, GuardedModel
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


def extended_ready(tmp_path):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    data['timing_policy'] = dict(EXTENDED_TIMING_POLICY)
    now = utc_now()
    auth = approval(data)
    auth['approved_at'] = now.isoformat()
    auth['expires_at'] = (now + timedelta(hours=1)).isoformat()
    return root, data, auth, now


def test_extended_policy_constructor_opt_in_is_sealed_and_legacy_unchanged(tmp_path):
    root, legacy = prepared(tmp_path)
    assert 'timing_policy' not in legacy
    extended = proposal(root, legacy['packet_sha256'], legacy['run_id'],
                        timing_policy=EXTENDED_TIMING_POLICY)
    assert extended['timing_policy'] == EXTENDED_TIMING_POLICY
    assert validate_proposal(extended, root) == digest_json(extended)
    assert extended['process_limits'] == legacy['process_limits']
    assert extended['limits'] == legacy['limits']
    assert extended['live_allowance'] == {'claude': 0, 'qwen': 0}


@pytest.mark.parametrize('policy', [None, {}, [],
    {**EXTENDED_TIMING_POLICY, 'observation_max_age_s': True},
    {**EXTENDED_TIMING_POLICY, 'observation_max_age_s': 3600.0},
    {**EXTENDED_TIMING_POLICY, 'initial_observation_max_age_s': '900'},
    {**EXTENDED_TIMING_POLICY, 'approval_max_duration_s': 3601},
    {**EXTENDED_TIMING_POLICY, 'start_margin_s': 0},
    {**EXTENDED_TIMING_POLICY, 'schema': 'harnessie-pilot-timing/2'},
    {**EXTENDED_TIMING_POLICY, 'extra': 1},
])
def test_malformed_extended_timing_policy_refuses(tmp_path, policy):
    root, data = prepared(tmp_path)
    data['timing_policy'] = policy
    with pytest.raises(PilotRefusal, match='invalid_timing_policy'):
        validate_proposal(data, root)


@pytest.mark.parametrize('field', ['billing', 'claude'])
@pytest.mark.parametrize(('age_minutes', 'expected'), [(16, None), (61, 'stale'), (-1, 'stale')])
def test_extended_runtime_observation_window(tmp_path, monkeypatch, field, age_minutes, expected):
    root, data, auth, now = extended_ready(tmp_path)
    target = data['billing'] if field == 'billing' else data['identities']['claude']
    target['checked_at'] = (now - timedelta(minutes=age_minutes)).isoformat()
    auth['manifest_sha256'] = digest_json(data)
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: now)
    if expected:
        with pytest.raises(PilotRefusal, match=expected):
            validate_authority(data, root, auth, digest_json(data))
    else:
        assert validate_authority(data, root, auth, digest_json(data)) == digest_json(data)
        with pytest.raises(PilotRefusal, match='initial_observation_stale'):
            validate_start_authority(data, root, auth, digest_json(data))


@pytest.mark.parametrize('field', ['billing', 'claude'])
def test_legacy_observation_at_16_minutes_still_refuses(tmp_path, monkeypatch, field):
    root, data = prepared(tmp_path)
    identity_ready(root, data)
    now = utc_now()
    target = data['billing'] if field == 'billing' else data['identities']['claude']
    target['checked_at'] = (now - timedelta(minutes=16)).isoformat()
    auth = approval(data)
    auth['approved_at'] = now.isoformat()
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: now)
    with pytest.raises(PilotRefusal, match='stale'):
        validate_authority(data, root, auth, digest_json(data))


def test_extended_approval_cannot_exceed_one_hour(tmp_path):
    root, data, auth, now = extended_ready(tmp_path)
    auth['expires_at'] = (now + timedelta(hours=1, seconds=1)).isoformat()
    with pytest.raises(PilotRefusal, match='invalid_approval_duration'):
        validate_authority(data, root, auth, digest_json(data))


@pytest.mark.parametrize('deadline', ['approval', 'proposal', 'observation'])
def test_insufficient_start_runway_blocks_before_metadata_or_provider(tmp_path, monkeypatch, deadline):
    root, data, auth, now = extended_ready(tmp_path)
    if deadline == 'approval':
        auth['expires_at'] = (now + timedelta(seconds=2219)).isoformat()
    elif deadline == 'proposal':
        data['expires_at'] = (now + timedelta(seconds=2219)).isoformat()
        auth['expires_at'] = data['expires_at']
    else:
        # Observation expiry wins over an otherwise fresh one-hour approval;
        # start freshness is checked first and refuses without metadata.
        data['billing']['checked_at'] = (now - timedelta(seconds=1381)).isoformat()
    auth['manifest_sha256'] = digest_json(data)
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: now)
    with patch('scripts.pilot_preflight.claude_metadata', side_effect=AssertionError('no metadata')), \
         patch('scripts.pilot_preflight.local_qwen_identity', side_effect=AssertionError('no metadata')), \
         patch('scripts.pilot_live._run_panel', side_effect=AssertionError('no provider')):
        with pytest.raises(PilotRefusal, match='initial_observation_stale' if deadline == 'observation'
                           else 'insufficient_start_runway'):
            execute_panel(root, data, auth, digest_json(data))
    assert not (root / 'runs').exists()


def test_exact_worst_case_runway_is_accepted(tmp_path, monkeypatch):
    root, data, auth, now = extended_ready(tmp_path)
    auth['expires_at'] = (now + timedelta(seconds=16 * 120 + 300)).isoformat()
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: now)
    assert validate_start_authority(data, root, auth, digest_json(data)) == digest_json(data)


def test_runway_rechecked_after_metadata_before_first_dispatch(tmp_path, monkeypatch):
    from scripts.pilot_ledger import RunLedger
    root, data, auth, now = extended_ready(tmp_path)
    auth['expires_at'] = (now + timedelta(seconds=2220)).isoformat()
    clock = [now]
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: clock[0])
    validate_start_authority(data, root, auth, digest_json(data))
    clock[0] += timedelta(seconds=1)  # metadata / runner setup took time
    participant = ScriptedParticipant('claude')
    with RunLedger(tmp_path / 'operator', digest_json(data), data['limits']) as ledger:
        guarded = GuardedModel(participant, 'claude', ledger, lambda: 'claude:position',
            lambda: validate_authority(data, root, auth, digest_json(data)),
            start_check=lambda: validate_start_authority(data, root, auth, digest_json(data)))
        result = guarded.complete([])
        assert result.content == 'pilot_refusal: insufficient_start_runway'
        assert participant.calls == 0
        assert ledger.summary()['calls'] == {'claude': 0, 'qwen': 0}


def test_post_response_expiry_retains_exact_refusal_usage_and_prevents_retry(tmp_path, monkeypatch):
    from scripts.pilot_ledger import RunLedger, read_ledger_summary
    root, data, auth, now = extended_ready(tmp_path)
    clock = [now]
    monkeypatch.setattr('scripts.pilot_execution.utc_now', lambda: clock[0])
    class ExpiresOnResponse(ScriptedParticipant):
        def complete(self, *args, **kwargs):
            turn = super().complete(*args, **kwargs)
            clock[0] += timedelta(hours=1)
            return turn
    participant = ExpiresOnResponse('claude')
    directory = tmp_path / 'operator'
    with RunLedger(directory, digest_json(data), data['limits']) as ledger:
        guarded = GuardedModel(participant, 'claude', ledger, lambda: 'claude:position',
            lambda: validate_authority(data, root, auth, digest_json(data)))
        assert guarded.complete([]).stop_reason == 'error'
        clock[0] = now  # Even if authority were valid again, no retry.
        assert guarded.complete([]).stop_reason == 'error'
        assert participant.calls == 1
        assert ledger.summary()['known_usage']['input_tokens'] == 10
        assert ledger.summary()['known_usage']['output_tokens'] == 5
    entries = [json.loads(line) for line in (directory / 'ledger.jsonl').read_text().splitlines()]
    receipt = next(entry['data'] for entry in entries if entry['kind'] == 'receipt')
    assert receipt['accepted'] is False
    assert receipt['receipt']['status'] == 'completed'
    assert receipt['receipt']['authority_failure'] == 'live_authority_expired'
    assert read_ledger_summary(directory)['integrity'] == 'valid'
