"""Operator-owned execution proposals. Creating one never grants dispatch."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.pilot_contract import CLAUDE_MODEL, QWEN_MODEL, QUESTION, PilotLimits, PilotRefusal, digest_json
from scripts.pilot_identity import assert_same_identity
from scripts.pilot_claude_code import AUTH_CONTRACT_ID, ELIGIBLE_AUTH_CLASSES
from scripts.pilot_policy import (
    CLAUDE_MAX_HAIKU_CONTEXT,
    CONTEXT_HAIKU_INPUT_PER_RUN,
    CONTEXT_HAIKU_OUTPUT_PER_RUN,
    CONTEXT_TOTAL_TOKENS_PER_RUN,
)
from scripts.pilot_prepare import verify_packet, _read
from scripts.pilot_stream import _loads

REPO = Path(__file__).resolve().parents[1]
STAGES = ('claude:position', 'qwen:position', 'claude:objection', 'qwen:objection')
TOOLS = ['read_file', 'list_files', 'task_complete']
SCHEMA = 'harnessie-live-pilot/2'
EXTENDED_TIMING_POLICY = {
    'schema': 'harnessie-pilot-timing/1',
    'observation_max_age_s': 3600,
    'initial_observation_max_age_s': 900,
    'approval_max_duration_s': 3600,
    'start_margin_s': 300,
}
RESPONSE_CAPTURE = {
    'provider': 'claude', 'format': 'exact_stdout_bytes',
    'required_before_parse': True, 'private_local_only': True,
    'max_bytes_basis': 'process_max_output_bytes_plus_one_overflow_sentinel',
    'on_failure': 'halt_no_retry_preserve_available_usage',
    'auth_output': 'excluded', 'stderr': 'not_captured',
}


def require(value: bool, code: str) -> None:
    if not value:
        raise PilotRefusal(code)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else None
        require(parsed is not None and parsed.tzinfo is not None, 'invalid_timestamp')
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise PilotRefusal('invalid_timestamp') from exc


def implementation_hashes(repo: Path = REPO) -> dict[str, str]:
    # Bind all runtime Python sources plus the pilot's actual operator code.
    paths = sorted(list((repo / 'harness').rglob('*.py')) + list((repo / 'scripts').glob('pilot_*.py')))
    require(bool(paths), 'implementation_missing')
    return {p.relative_to(repo).as_posix(): hashlib.sha256(_read(repo, p.relative_to(repo).as_posix())).hexdigest()
            for p in paths}


def proposal(packet_root: Path, packet_seal: str, run_id: str, *,
             identities: dict | None = None, billing: dict | None = None,
             timing_policy: dict | None = None) -> dict:
    packet = verify_packet(packet_root, packet_seal)
    require(isinstance(run_id, str) and re.fullmatch(r'pilot-[a-z0-9][a-z0-9-]{0,60}', run_id) is not None,
            'invalid_run_id')
    now = utc_now()
    result = {
        'schema': SCHEMA, 'status': 'proposal_not_authorization',
        'question': QUESTION, 'run_id': run_id, 'packet_root': str(packet_root.resolve()),
        'packet_sha256': packet_seal, 'created_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=24)).isoformat(),
        'stages': list(STAGES), 'allowed_tools': TOOLS.copy(),
        'policy': CLAUDE_MAX_HAIKU_CONTEXT.as_dict(),
        'implementation_sha256': implementation_hashes(),
        'disclosure': {p: v for p, v in packet['files'].items()
                       if p.startswith('workspace/') or p.startswith('agents/')},
        'limits': {'calls': {'claude': 8, 'qwen': 8}, 'calls_per_stage': 4,
                   'total_tokens': CONTEXT_TOTAL_TOKENS_PER_RUN,
                   'haiku_input_tokens': CONTEXT_HAIKU_INPUT_PER_RUN,
                   'haiku_output_tokens': CONTEXT_HAIKU_OUTPUT_PER_RUN},
        'process_limits': {'timeout_s': 120, 'max_input_bytes': 256_000,
                           'max_evidence_bytes': 256_000,
                           'max_output_bytes': 128_000, 'max_output_tokens': 4096},
        'limits_basis': 'Approved offline candidate: up to three evidence-reading exchanges and one completion '
                        'per stage. Run token limits are post-response stop thresholds, not a provider billing cap.',
        'identities': identities or {'claude': None, 'qwen': None},
        'billing': billing or {'requirement': 'included_allowance_only', 'verified': False,
                              'included_fable_allowance': None, 'usage_credits_enabled': None,
                              'evidence': None, 'checked_at': None},
        'live_allowance': {'claude': 0, 'qwen': 0},
        'response_capture': dict(RESPONSE_CAPTURE),
        'outputs': {'ledger': f'runs/{run_id}/operator', 'run': f'runs/{run_id}-workflow',
                    'responses': f'runs/{run_id}/operator/responses',
                    'request_metrics': f'runs/{run_id}/operator/request-metrics.jsonl',
                    'export': f'runs/{run_id}/open-export/decisions/AIDR-9998-pilot.md'},
    }
    if timing_policy is not None:
        result['timing_policy'] = timing_policy
        _timing_policy(result)
        result['timing_policy'] = dict(timing_policy)
    return result


def _timing_policy(data: dict) -> dict | None:
    """The longer window is an explicit, exact, sealed opt-in, never a default."""
    if 'timing_policy' not in data:
        return None
    policy = data['timing_policy']
    require(type(policy) is dict and set(policy) == set(EXTENDED_TIMING_POLICY)
            and all(type(policy[k]) is type(v) and policy[k] == v
                    for k, v in EXTENDED_TIMING_POLICY.items()), 'invalid_timing_policy')
    return policy


def validate_proposal(data: dict, packet_root: Path, *, now: datetime | None = None) -> str:
    """Validate local bytes and contracts, with no metadata or model calls."""
    try:
        require(type(data) is dict and data['schema'] == SCHEMA
                and data['status'] == 'proposal_not_authorization', 'invalid_execution_manifest')
        require(data['question'] == QUESTION and data['stages'] == list(STAGES)
                and data['allowed_tools'] == TOOLS, 'execution_contract_mismatch')
        require(data['policy'] == CLAUDE_MAX_HAIKU_CONTEXT.as_dict(), 'policy_drift')
        require(data['live_allowance'] == {'claude': 0, 'qwen': 0}, 'proposal_grants_calls')
        require(data['response_capture'] == RESPONSE_CAPTURE, 'response_capture_contract_mismatch')
        _timing_policy(data)
        run_id = data['run_id']
        require(type(run_id) is str and re.fullmatch(r'pilot-[a-z0-9][a-z0-9-]{0,60}', run_id) is not None,
                'invalid_run_id')
        require(data['packet_root'] == str(packet_root.resolve()), 'packet_root_mismatch')
        packet = verify_packet(packet_root, data['packet_sha256'], runtime_run_id=run_id + '-workflow')
        expected = {p: v for p, v in packet['files'].items()
                    if p.startswith('workspace/') or p.startswith('agents/')}
        require(data['disclosure'] == expected, 'disclosure_drift')
        require(data['implementation_sha256'] == implementation_hashes(), 'implementation_drift')
        require(data['outputs'] == {'ledger': f'runs/{run_id}/operator', 'run': f'runs/{run_id}-workflow',
                'responses': f'runs/{run_id}/operator/responses',
                'request_metrics': f'runs/{run_id}/operator/request-metrics.jsonl',
                'export': f'runs/{run_id}/open-export/decisions/AIDR-9998-pilot.md'}, 'output_path_mismatch')
        now = now or utc_now()
        created, expires = timestamp(data['created_at']), timestamp(data['expires_at'])
        require(created <= now < expires and expires - created <= timedelta(hours=24), 'execution_manifest_expired')
        limits = data['limits']
        require(type(limits) is dict and set(limits) == {'calls', 'calls_per_stage', 'total_tokens',
                'haiku_input_tokens', 'haiku_output_tokens'}, 'invalid_execution_limits')
        require(type(limits['calls']) is dict and set(limits['calls']) == {'claude', 'qwen'}, 'invalid_execution_limits')
        values = list(limits['calls'].values()) + [v for k, v in limits.items() if k != 'calls']
        require(all(type(v) is int and v > 0 for v in values), 'invalid_execution_limits')
        require(limits['calls_per_stage'] <= 4 and all(v <= 8 for v in limits['calls'].values()),
                'invalid_execution_limits')
        require(limits['total_tokens'] <= CONTEXT_TOTAL_TOKENS_PER_RUN
                and limits['haiku_input_tokens'] <= CONTEXT_HAIKU_INPUT_PER_RUN
                and limits['haiku_output_tokens'] <= CONTEXT_HAIKU_OUTPUT_PER_RUN,
                'invalid_execution_limits')
        process = data['process_limits']
        require(type(process) is dict and set(process) == {'timeout_s','max_input_bytes',
                'max_evidence_bytes','max_output_bytes','max_output_tokens'},
                'invalid_process_limits')
        PilotLimits(max_calls=0, **process)
        require(process['timeout_s'] <= 120 and process['max_input_bytes'] <= 256_000
                and process['max_evidence_bytes'] <= 256_000
                and process['max_output_bytes'] <= 128_000 and process['max_output_tokens'] <= 4096, 'invalid_process_limits')
        return digest_json(data)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        if isinstance(exc, PilotRefusal):
            raise
        raise PilotRefusal('invalid_execution_manifest') from exc


def validate_authority(data: dict, packet_root: Path, approval: dict | None,
                       confirmation: str | None) -> str:
    """Requires both a bound operator record and an explicit dispatch confirmation.

    Local operator code and its approval files are trusted. This is not remote
    authentication or a sandbox against arbitrary Python running as the owner.
    """
    seal = validate_proposal(data, packet_root)
    try:
        require(verify_packet(packet_root, data['packet_sha256'], runtime_run_id=data['run_id'] + '-workflow').get('purpose') == 'execution_candidate',
                'mock_packet_not_executable')
        require(type(approval) is dict and confirmation == seal, 'live_authority_required')
        require(set(approval) == {'manifest_sha256','approved_by','approved_at','expires_at','action'}, 'invalid_live_authority')
        require(approval['manifest_sha256'] == seal and approval['approved_by'] == 'Sam Rogers'
                and approval['action'] == 'execute_live_panel', 'invalid_live_authority')
        now = utc_now()
        start, end = timestamp(approval['approved_at']), timestamp(approval['expires_at'])
        require(start <= now < end and end <= timestamp(data['expires_at']), 'live_authority_expired')
        timing = _timing_policy(data)
        if timing is not None:
            require(end - start <= timedelta(seconds=timing['approval_max_duration_s']),
                    'invalid_approval_duration')
        max_age = timedelta(seconds=timing['observation_max_age_s'] if timing else 900)
        billing = data['billing']
        require(billing['requirement'] == 'included_allowance_only' and billing['verified'] is True
                and billing['included_fable_allowance'] is True and billing['usage_credits_enabled'] is False
                and type(billing['evidence']) is str and bool(billing['evidence'].strip()), 'included_allowance_unverified')
        require(timedelta(0) <= now - timestamp(billing['checked_at']) <= max_age, 'billing_evidence_stale')
        identities = data['identities']
        c = identities['claude']
        require(c['model_id'] == CLAUDE_MODEL and c['auth_contract'] == AUTH_CONTRACT_ID
                and c['auth_class'] in ELIGIBLE_AUTH_CLASSES
                and type(c['cli_version']) is str and bool(c['cli_version']), 'claude_identity_unverified')
        require(timedelta(0) <= now - timestamp(c['checked_at']) <= max_age, 'claude_identity_stale')
        require(Path(c['executable']).is_absolute() and Path(c['executable']).is_file()
                and hashlib.sha256(Path(c['executable']).read_bytes()).hexdigest() == c['sha256'], 'claude_executable_drift')
        q = identities['qwen']
        assert_same_identity(q, q)
        require(q['model']['tag'] == QWEN_MODEL and q['ollama_base_url'] == 'http://127.0.0.1:11434', 'qwen_identity_unverified')
        sealed = verify_packet(packet_root, data['packet_sha256'], runtime_run_id=data['run_id'] + '-workflow')
        require(q['harness_identity'] == sealed['participants']['qwen']['declared_harness_identity'], 'qwen_configuration_drift')
        return seal
    except (KeyError, TypeError, ValueError, OSError, AttributeError) as exc:
        if isinstance(exc, PilotRefusal):
            raise
        raise PilotRefusal('invalid_live_authority') from exc


def validate_start_authority(data: dict, packet_root: Path, approval: dict | None,
                             confirmation: str | None) -> str:
    """Require fresh observations and worst-case call runway before starting.

    Legacy proposals retain their original semantics. The sealed extended policy
    budgets every permitted call at its timeout plus a fixed operational margin.
    """
    seal = validate_authority(data, packet_root, approval, confirmation)
    timing = _timing_policy(data)
    if timing is None:
        return seal
    now = utc_now()
    observed = [timestamp(data['billing']['checked_at']),
                timestamp(data['identities']['claude']['checked_at'])]
    require(all(timedelta(0) <= now - checked <= timedelta(seconds=timing['initial_observation_max_age_s'])
                for checked in observed), 'initial_observation_stale')
    deadline = min(timestamp(approval['expires_at']), timestamp(data['expires_at']),
                   *(checked + timedelta(seconds=timing['observation_max_age_s']) for checked in observed))
    required_s = sum(data['limits']['calls'].values()) * data['process_limits']['timeout_s'] + timing['start_margin_s']
    require(deadline - now >= timedelta(seconds=required_s), 'insufficient_start_runway')
    return seal


def load_json(path: Path) -> dict:
    require(path.is_absolute(), 'unsafe_operator_path')
    raw = _read(path.parent, path.name, 1_500_000)
    try:
        value = _loads(raw.decode())
        require(type(value) is dict, 'invalid_operator_document')
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PilotRefusal('invalid_operator_document') from exc


def write_proposal(path: Path, data: dict) -> str:
    # No helper generates an approval record. A proposal remains zero-authority.
    require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents), 'unsafe_operator_path')
    with path.open('x') as handle:
        json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    return digest_json(data)
