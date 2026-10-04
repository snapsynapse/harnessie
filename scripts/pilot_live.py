"""Pilot-only guarded runner. Proposals and rehearsals never authorize live calls."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from harness.adversarial import parse_stance, parse_objection_response
from harness.aidr_export import export_aidr
from harness.audit import verify_chain
from harness.models.base import ModelInterface, ModelSpec, Message, AssistantTurn, ToolCall
from harness.runner import WorkflowRunner
from scripts.pilot_claude_code import ClaudeCodePilot
from scripts.pilot_contract import CLAUDE_MODEL, QWEN_MODEL, QUESTION, CallAllowance, PilotLimits, PilotRefusal
from scripts.pilot_execution import (STAGES, TOOLS, require, proposal, validate_proposal, validate_authority,
                                     validate_start_authority, load_json, write_proposal, digest_json)
from scripts.pilot_ledger import RunLedger, read_ledger_summary
from scripts.pilot_policy import CLAUDE_MAX_HAIKU_CONTEXT
from scripts.pilot_prepare import verify_packet
from scripts.pilot_qwen import QwenPilot
from scripts.pilot_capture import ResponseCaptureStore
from scripts.pilot_request_metrics import RequestMetricsStore, read_request_metrics


def forbidden(*args, **kwargs):
    raise PilotRefusal('unapproved_model_factory')


class GuardedModel(ModelInterface):
    """One shared ledger wraps every transport, including ordinary loop retries."""
    def __init__(self, delegate, participant, ledger, stage, verify,
                 request_metrics: RequestMetricsStore | None = None, start_check=None):
        super().__init__(delegate.spec)
        self.delegate, self.participant, self.ledger = delegate, participant, ledger
        self.stage, self.verify = stage, verify
        self.request_metrics = request_metrics
        self.start_check = start_check

    def complete(self, messages, tools=None, effort='medium'):
        offered_tools = tools or []
        if self.request_metrics is not None and getattr(self.delegate, '_failed', False):
            return AssistantTurn(content='pilot_refusal: transport_latched', stop_reason='error')
        try:
            self.verify()
            require(all(t.get('name') in TOOLS for t in offered_tools), 'tool_scope_mismatch')
            stage = self.stage()
            limit = self.ledger.limits['calls_per_stage']
            call_number = self.ledger.summary()['calls_per_stage'].get(stage, 0) + 1
            allowance = getattr(self.delegate, 'allowance', None)
            output_limit = allowance.limits.max_output_tokens if allowance is not None else None
            # Add fresh guidance without accumulating notices in the transcript.
            messages = [*messages, Message(role='user', content=json.dumps({
                'pilot_stage_budget': {
                    'stage': stage, 'calls_per_stage': limit,
                    'call_number': call_number,
                    'calls_remaining_after_this': max(0, limit - call_number),
                    'final_call_reserved_for': 'task_complete',
                    'max_output_tokens_per_call': output_limit,
                    'output_budget_scope': 'aggregate_reported_output_all_models',
                },
                'output_instruction': (
                    'Use the configured output ceiling for the entire response, including any reported '
                    'reasoning, formatter and helper-model output. Keep the report concise, retaining '
                    'required stance or objection fields, evidence-path citations and uncertainty. '
                    'Do not spend the full ceiling on report text or repeat the source evidence.'),
                'instruction': ('Final call: synthesize available evidence and submit only task_complete. '
                                'Identify missing evidence as unknown.' if call_number >= limit else
                                'Batch evidence reads; finish reading before the final synthesis call.'),
            }))]
            if self.request_metrics is not None:
                require(callable(getattr(self.delegate, 'prepare_request', None))
                        and callable(getattr(self.delegate, 'complete_prepared', None)),
                        'request_metrics_unsupported')
                prepared = self.delegate.prepare_request(messages, offered_tools, effort)
                limits = self.delegate.allowance.limits
                self.request_metrics.record(
                    stage=stage, participant=self.participant, prepared=prepared,
                    messages=messages, tools=offered_tools,
                    max_input_bytes=limits.max_input_bytes,
                    max_evidence_bytes=limits.max_evidence_bytes)
            else:
                prepared = None
            # Preparation can consume time; validate again immediately before
            # reserving the irreversible dispatch, with full runway on call one.
            self.verify()
            if self.start_check is not None and not sum(self.ledger.summary()['calls'].values()):
                self.start_check()
            attempt = self.ledger.reserve(stage, self.participant)
            self.ledger.dispatched(attempt)
        except PilotRefusal as exc:
            if self.request_metrics is not None:
                self.delegate._failed = True
            return AssistantTurn(content=f'pilot_refusal: {exc.code}', stop_reason='error')
        except Exception:
            if self.request_metrics is not None:
                self.delegate._failed = True
            return AssistantTurn(content='pilot_refusal: invalid_request', stop_reason='error')
        try:
            previous = len(self.delegate.receipts)
            turn = (self.delegate.complete_prepared(prepared, offered_tools, effort)
                    if prepared is not None else self.delegate.complete(messages, tools, effort))
            require(len(self.delegate.receipts) == previous + 1, 'transport_receipt_missing')
            receipt = self.delegate.receipts[-1]
            receipt = receipt.as_dict() if hasattr(receipt, 'as_dict') else receipt
            still_bound = True
            try:
                self.verify()
            except PilotRefusal as exc:
                still_bound = False
                # Keep transport status and usage intact, but retain the exact
                # acceptance refusal in the hash-chained operator receipt.
                receipt = dict(receipt, authority_failure=exc.code)
            accepted = (receipt.get('status') == 'completed' and turn.stop_reason in {'end_turn', 'tool_use'}
                        and all(t.name in TOOLS for t in turn.tool_calls) and still_bound)
            self.ledger.finish(attempt, receipt, accepted)
            if not accepted:
                return AssistantTurn(content='pilot_refusal: transport_refused', stop_reason='error')
            return turn
        except Exception as exc:
            # A crash or receipt failure is uncertain. Never retry its dispatch.
            try:
                self.ledger.halt('uncertain_transport_outcome')
            except PilotRefusal:
                pass
            code = exc.code if isinstance(exc, PilotRefusal) else 'uncertain_transport_outcome'
            return AssistantTurn(content=f'pilot_refusal: {code}', stop_reason='error')


class PilotWorkflow(WorkflowRunner):
    def _run_role(self, agent_name, task, route, **kwargs):
        index = self.stage_index
        require(index < len(STAGES), 'unexpected_stage')
        expected = 'frontier' if STAGES[index].startswith('claude:') else 'local'
        require(route.tier == expected and route.alt == 0 and agent_name == 'reviewer', 'stage_route_mismatch')
        self.active_stage = STAGES[index]
        kwargs['max_steps'] = self.execution['limits']['calls_per_stage']
        kwargs['deny_tools'] = frozenset(set(self.registry.tools) - set(TOOLS))
        result = super()._run_role(agent_name, task, route, **kwargs)
        require(result.ok, 'stage_failed')
        parsed = parse_stance(result.report) if index < 2 else parse_objection_response(result.report)
        require(parsed is not None, 'stage_protocol_invalid')
        self.stage_index += 1
        return result


def _workflow_contract(root):
    import yaml
    config = yaml.safe_load((root / 'workflows/review.yaml').read_text())
    require(len(config.get('phases', [])) == 1, 'workflow_contract_mismatch')
    phase = config['phases'][0]
    require(phase.get('name') == 'decide' and phase.get('mode') == 'adversarial'
            and phase.get('arbitration') == 'human' and phase.get('arbiter') == 'Sam Rogers'
            and phase.get('rebuttal_rounds') == 1
            and phase.get('positions') == [{'agent': 'reviewer'}, {'agent': 'reviewer', 'task_class': 'challenge'}],
            'workflow_contract_mismatch')


def _export(root, run_id, execution):
    run_dir = root / 'runs' / run_id
    export_root = root / 'runs' / execution['run_id'] / 'open-export'
    copied = export_root / 'runs' / run_id
    shutil.copytree(run_dir, copied)
    (export_root / 'decisions').mkdir()
    snapshot = lambda: {p.relative_to(run_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in run_dir.rglob('*') if p.is_file()}
    before = snapshot()
    out = export_aidr(export_root, run_id, 'decide', 'decisions/AIDR-9998-pilot.md', 'Sam Rogers')
    require(out['status'] == 'exported' and snapshot() == before, 'export_failed')
    path = export_root / 'decisions/AIDR-9998-pilot.md'
    require(not path.read_text().split('## Arbitration\n')[1].split('## Evidence')[0].strip(), 'arbitration_not_empty')
    # Reuse the installed-example pinned reference checker without network.
    import importlib.util
    import subprocess
    spec = importlib.util.spec_from_file_location('pilot_reference_check', Path(__file__).resolve().parents[1] / 'examples/aidr-export/demo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    lint = module.check_reference(Path(__file__).resolve().parents[1] / 'tests/fixtures/aidr-0.1.0')
    result = subprocess.run(['node', str(lint), str(path)], capture_output=True, text=True, timeout=20)
    require(result.returncode == 0 and 'PASS ' in result.stdout, 'reference_lint_failed')
    return str(path.relative_to(root))


def _run_panel(root: Path, execution: dict, factories: dict, *, offline: bool, authority_check=None,
               start_check=None) -> dict:
    """Internal injected seam. Host Python/factories are operator-trusted code."""
    seal = validate_proposal(execution, root)
    require(offline or callable(authority_check), 'live_authority_required')
    _workflow_contract(root)
    parent = root / 'runs' / execution['run_id']
    require(not parent.exists() and not parent.is_symlink(), 'pilot_run_exists')
    workflow_id = execution['run_id'] + '-workflow'
    require(not (root / 'runs' / workflow_id).exists(), 'pilot_run_exists')
    (root / 'runs').mkdir(exist_ok=True)
    parent.mkdir(mode=0o700)
    # Persist both directory entries before an irreversible dispatch can occur.
    for directory in (root, root / 'runs'):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    ledger = RunLedger(parent / 'operator', seal, execution['limits'])
    result = {'status': 'incomplete', 'mode': 'offline_rehearsal' if offline else 'live',
              'manifest_sha256': seal, 'actual_dollar_cost': None, 'human_arbitrated': False}
    runner = None
    request_metrics = None
    try:
        with patch('harness.runner.build_model', forbidden):
            runner = PilotWorkflow(root, run_id=workflow_id, echo=False)
            runner.execution, runner.stage_index, runner.active_stage = execution, 0, STAGES[0]
            delegates = {participant: factories[participant]() for participant in ('claude', 'qwen')}
            supports_metrics = all(callable(getattr(delegate, 'prepare_request', None))
                                   and callable(getattr(delegate, 'complete_prepared', None))
                                   for delegate in delegates.values())
            require(offline or supports_metrics, 'request_metrics_unsupported')
            if supports_metrics:
                request_metrics = RequestMetricsStore(parent / 'operator' / 'request-metrics.jsonl')
            for participant, tier in (('claude', 'frontier'), ('qwen', 'local')):
                delegate = delegates[participant]
                runner.router.tiers[tier] = delegate.spec
                runner._models[delegate.spec.name] = GuardedModel(delegate, participant, ledger,
                    lambda: runner.active_stage,
                    lambda: (validate_proposal(execution, root) if offline else authority_check()),
                    request_metrics, start_check)
            # The legacy runner's USD fixture remains non-authoritative; receipts
            # and the operator ledger own usage, cache counts and unknown dollars.
            runner.budget.max_tokens = execution['limits']['total_tokens']
            outcomes = runner.run_workflow(root / 'workflows/review.yaml', goal=QUESTION)
            require(runner.stage_index == 4 and len(outcomes) == 1
                    and outcomes[0].status == 'needs_arbitration', 'human_halt_missing')
            validate_proposal(execution, root)
            verify_packet(root, execution['packet_sha256'], runtime_run_id=workflow_id)
            result['export_path'] = _export(root, runner.run_id, execution)
            before = ledger.summary()['calls']
            resumed = runner.run_workflow(root / 'workflows/review.yaml', goal=QUESTION)
            require(len(resumed) == 1 and resumed[0].status == 'needs_arbitration'
                    and ledger.summary()['calls'] == before, 'resume_dispatched')
            result.update(status='needs_arbitration', resume_status='needs_arbitration', resume_calls=0)
    except Exception as exc:
        result['failure'] = exc.code if isinstance(exc, PilotRefusal) else type(exc).__name__
        try:
            ledger.halt('run_failed')
        except PilotRefusal:
            pass
    finally:
        if runner is not None:
            runner.events.close()
        result['ledger'] = ledger.summary()
        ledger.close()
        result['ledger_integrity'] = read_ledger_summary(parent / 'operator')
        if request_metrics is not None:
            try:
                request_metrics.close()
                result['request_metrics'] = read_request_metrics(
                    parent / 'operator' / 'request-metrics.jsonl')
            except PilotRefusal as exc:
                result.update(status='incomplete', failure=exc.code,
                              request_metrics={'integrity': 'invalid', 'failure': exc.code})
        if runner is not None:
            result['runner_chain'] = verify_chain(runner.run_dir)
        with (parent / 'outcome.json').open('x') as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write('\n')
    return result


class ScriptedParticipant(ModelInterface):
    def __init__(self, participant, agree=False):
        self.participant, self.agree = participant, agree
        super().__init__(ModelSpec('frontier' if participant == 'claude' else 'local', 'mock',
                                  'SCRIPTED-' + participant))
        self.receipts, self.calls = [], 0

    def complete(self, messages, tools=None, effort='medium'):
        self.calls += 1
        if self.calls % 2:
            call = ToolCall(f'read-{self.calls}', 'read_file', {'path': 'evidence-index.json'})
        else:
            data = ({'stance': 'recommend' if self.participant == 'claude' or self.agree else 'oppose',
                     'summary': 'SCRIPTED ONLY, no live opinion.'} if self.calls == 2 else
                    {'objections': [] if self.agree else ['SCRIPTED concern'], 'no_new_objection': self.agree})
            call = ToolCall(f'done-{self.calls}', 'task_complete', {'report': 'SCRIPTED ONLY.\n' + json.dumps(data)})
        usage = {'input_tokens': 10, 'output_tokens': 5, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
        self.receipts.append({'status': 'completed', 'mode': 'scripted_only', 'usage': usage,
                              'model_usage': {self.spec.model_id: usage}, 'dollar_cost': None})
        return AssistantTurn('', [call], 'tool_use', 10, 5)


def rehearse_panel(root: Path, execution: dict, *, agree=False) -> dict:
    # CLI rehearsal cannot substitute external providers for these factories.
    with patch('socket.socket.connect', forbidden), patch('socket.create_connection', forbidden):
        return _run_panel(root, execution, {p: (lambda p=p: ScriptedParticipant(p, agree))
                                           for p in ('claude', 'qwen')}, offline=True)


def execute_panel(root: Path, execution: dict, approval: dict | None = None,
                  confirmation: str | None = None) -> dict:
    validate_start_authority(execution, root, approval, confirmation)
    from scripts.pilot_preflight import claude_metadata, local_qwen_identity
    c, q = execution['identities']['claude'], execution['identities']['qwen']
    current = claude_metadata(Path(c['executable']))
    require(all(current[k] == c[k] for k in
                ('sha256','cli_version','auth_contract','auth_class','model_id')),
            'claude_identity_drift')
    from scripts.pilot_identity import assert_same_identity
    assert_same_identity(q, local_qwen_identity(q['harness_identity'], q['client_version']))
    with tempfile.TemporaryDirectory(prefix='harnessie-live-claude-') as temp:
        def allowance(participant):
            return CallAllowance(PilotLimits(max_calls=execution['limits']['calls'][participant], **execution['process_limits']))
        return _run_panel(root, execution, {
            'claude': lambda: ClaudeCodePilot(ModelSpec('frontier','claude-code-max-pilot',CLAUDE_MODEL),
                Path(c['executable']), Path(temp), allowance('claude'), policy=CLAUDE_MAX_HAIKU_CONTEXT,
                expected_auth_class=c['auth_class'],
                capture_store=ResponseCaptureStore(root / 'runs' / execution['run_id'] / 'operator' / 'responses',
                                                   execution['process_limits']['max_output_bytes'])),
            'qwen': lambda: QwenPilot(ModelSpec('local','openai-compat',QWEN_MODEL,base_url='http://127.0.0.1:11434/v1'),
                q, lambda: local_qwen_identity(q['harness_identity'], q['client_version']), allowance('qwen')),
        }, offline=False, authority_check=lambda: validate_authority(execution, root, approval, confirmation),
            start_check=lambda: validate_start_authority(execution, root, approval, confirmation))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('prepare'); build.add_argument('root', type=Path); build.add_argument('packet_seal')
    build.add_argument('run_id'); build.add_argument('output', type=Path)
    for name in ('rehearse', 'execute'):
        command = sub.add_parser(name); command.add_argument('manifest', type=Path)
        if name == 'execute':
            command.add_argument('--approval', required=True, type=Path)
            command.add_argument('--confirm-manifest', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            data = proposal(args.root.absolute(), args.packet_seal, args.run_id)
            result = {'manifest_sha256': write_proposal(args.output.absolute(), data), 'live_calls': 0}
        else:
            data = load_json(args.manifest.absolute()); root = Path(data['packet_root'])
            result = (rehearse_panel(root, data) if args.command == 'rehearse' else
                      execute_panel(root, data, load_json(args.approval.absolute()), args.confirm_manifest))
        print(json.dumps(result, indent=2)); return 0 if result.get('status') in (None,'needs_arbitration') else 2
    except (PilotRefusal, OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'refused', 'failure': exc.code if isinstance(exc,PilotRefusal) else type(exc).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
