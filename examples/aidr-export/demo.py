#!/usr/bin/env python3
"""Exercise mock review -> installed export CLI -> pinned lint -> human halt.

All generated project/run artifacts live in a temporary directory. No real
provider is used, and this example never authors an Arbitration section.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import harness
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner

REFERENCE_REVISION = 'a67c41d339d3e70bc3baaf07e652f9cf9d13a5bb'
PROVENANCE_SHA256 = '0f6318e4edb19c63f6d87cae0b63f3e8be121255f3b86001400058cc7e68da3a'
GOAL = 'Should this synthetic cache use SQLite?'
FIRST = 'SQLite gives this cache transactional updates.'
SECOND = 'Retain JSONL until migration is reversible.'
OBJECTION = 'The migration can discard history before rollback is tested.'
OUTPUT = 'decisions/AIDR-9999-synthetic-mock-review.md'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def command(argv: list[str], root: Path, expected: int = 0) -> str:
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, check=False)
    require(result.returncode == expected,
            f'Command exit {result.returncode}, expected {expected}: {result.stdout}{result.stderr}')
    require(not result.stderr, f'Unexpected command stderr: {result.stderr}')
    return result.stdout


def check_reference(reference: Path) -> Path:
    manifest_bytes = (reference / 'provenance.json').read_bytes()
    require(hashlib.sha256(manifest_bytes).hexdigest() == PROVENANCE_SHA256,
            'Reference provenance does not match the pinned fixture')
    manifest = json.loads(manifest_bytes)
    require(manifest['revision'] == REFERENCE_REVISION and manifest['spec_version'] == '0.1.0',
            'Unexpected AIDR reference revision')
    for name, digest in manifest['files'].items():
        require(hashlib.sha256((reference / name).read_bytes()).hexdigest() == digest,
                f'Pinned reference bytes changed: {name}')
    return reference / 'tools/aidr-lint.mjs'


def scaffold(root: Path) -> None:
    files = {
        'agents/orchestrator.md': '# Orchestrator\nSynthetic example only.\n',
        'agents/workers/implementer.md': '# Worker\nGive the scripted position.\n',
        'config/models.yaml': '''tiers:
  mid:
    provider: mock
    model_id: mock-proposal
  cheap:
    provider: mock
    model_id: mock-challenge
routing:
  default: {tier: mid, effort: medium}
  challenge: {tier: cheap, effort: medium}
budget:
  max_usd: 1.0
  max_tokens: 10000
''',
        'workflows/review.yaml': '''name: synthetic-review
phases:
  - name: decide
    mode: adversarial
    arbitration: human
    arbiter: synthetic-human-tester
    task: "Decide: {goal}"
    positions:
      - {agent: implementer}
      - {agent: implementer, task_class: challenge}
''',
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    (root / 'decisions').mkdir()


def complete(report: str, identifier: str) -> AssistantTurn:
    return AssistantTurn(content='', stop_reason='tool_use', tool_calls=[
        ToolCall(id=identifier, name='task_complete', arguments={'report': report})])


def review(root: Path, run_id: str, goal: str, *, resume: bool = False) -> tuple[str, int]:
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    reports = {
        'mid': [FIRST + '\n' + json.dumps({'stance': 'recommend', 'summary': FIRST}),
                     json.dumps({'objections': [], 'no_new_objection': True})],
        'cheap': [SECOND + '\n' + json.dumps({'stance': 'oppose', 'summary': SECOND}),
                      json.dumps({'objections': [OBJECTION], 'no_new_objection': False})],
    }
    for name, entries in reports.items():
        runner._models[name] = MockModel(
            ModelSpec(name=name, provider='mock', model_id='mock-proposal' if name == 'mid' else 'mock-challenge'),
            script=[] if resume else [complete(report, f'{name}-{i}')
                                      for i, report in enumerate(entries)])
    try:
        outcomes = runner.run_workflow(root / 'workflows/review.yaml', goal=goal)
        require(len(outcomes) == 1, 'Expected exactly one contested phase')
        calls = sum(len(model.calls) for model in runner._models.values())
        require(calls == (0 if resume else 4), 'Unexpected number of scripted model calls')
        return outcomes[0].status, calls
    finally:
        runner.events.close()


def snapshot(root: Path, run_id: str) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in (root / 'runs' / run_id).rglob('*') if path.is_file()}


def export_args(cli: Path, root: Path, run_id: str, output: str) -> list[str]:
    return [str(cli), '--root', str(root), 'export-aidr', run_id, 'decide',
            '--output', output, '--arbiter', 'synthetic-human-tester']


def demonstrate(cli: Path, reference: Path) -> dict:
    lint = check_reference(reference)
    node = shutil.which('node')
    require(node is not None, 'Node is required by this reference-lint demo, not by the exporter')
    require(cli.is_file(), 'Install Harnessie first, or supply its installed CLI with --cli')
    with tempfile.TemporaryDirectory(prefix='harnessie-aidr-mock-') as raw:
        root = Path(raw).resolve()
        scaffold(root)
        initial, calls = review(root, 'synthetic-supported', GOAL)
        require(initial == 'needs_arbitration', 'Mock dissent did not halt for a human')
        before = snapshot(root, 'synthetic-supported')
        result = json.loads(command(export_args(cli, root, 'synthetic-supported', OUTPUT), root))
        require(result['status'] == 'exported', 'Supported mock record did not export')
        output = root / OUTPUT
        text = output.read_text(encoding='utf-8')
        require(all(value in text for value in (FIRST, SECOND, OBJECTION)), 'Export lost recorded dissent')
        require('- agent: implementer\n' in text and '- agent: implementer-2\n' in text,
                'Repeated roles lost their distinct participant labels')
        require(text.count('- original_role: implementer\n') == 2, 'Original roles were not retained')
        require(text.split('## Arbitration\n')[1].split('## Evidence')[0].strip() == '',
                'Export must retain an empty Arbitration section')
        require(result['output_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest(),
                'Output digest does not match published bytes')
        receipt = command([node, str(lint), str(output)], root)
        require('PASS ' in receipt and 'human-arbitrated' not in receipt, 'Reference lint did not pass open output')
        require(snapshot(root, 'synthetic-supported') == before, 'Export/lint changed run inputs')
        original_record = root / 'runs/synthetic-supported/decisions/DR-decide.md'
        resumed, resume_calls = review(root, 'synthetic-supported', GOAL, resume=True)
        require(resumed == 'needs_arbitration', 'Export incorrectly enabled resume')
        require(original_record.read_bytes() == before[original_record], 'Resume changed the source record')

        # This second source is also produced by the actual runner. Its rendered
        # task contains an unclosed fence, intentionally outside the export subset.
        unsupported_status, more_calls = review(root, 'synthetic-unsupported', GOAL + '\n\n```text\nunfinished')
        require(unsupported_status == 'needs_arbitration', 'Unsupported fixture did not halt')
        unsupported_before = snapshot(root, 'synthetic-unsupported')
        decisions_before = {p.name: p.read_bytes() for p in (root / 'decisions').iterdir()}
        refused = json.loads(command(export_args(cli, root, 'synthetic-unsupported',
                              'decisions/AIDR-9998-synthetic-unsupported.md'), root, expected=2))
        require(refused == {'status': 'refused', 'code': 'invalid_record'}, 'Formatting was not refused')
        require(snapshot(root, 'synthetic-unsupported') == unsupported_before, 'Refusal changed run inputs')
        require({p.name: p.read_bytes() for p in (root / 'decisions').iterdir()} == decisions_before,
                'Refusal left output or staging artifacts')
        return {'status': 'passed', 'actors': 'scripted MockModel only', 'live_model_calls': 0,
                'mock_model_calls': calls + more_calls, 'resume_model_calls': resume_calls,
                'initial_status': initial, 'resume_status': resumed, 'export_preserved_inputs': True,
                'format_refusal': refused, 'format_refusal_preserved_inputs': True,
                'participant_labels': ['implementer', 'implementer-2'],
                'reference_spec': '0.1.0', 'reference_revision': REFERENCE_REVISION,
                'temporary_root': str(root), 'harness_module': str(Path(harness.__file__).resolve()),
                'cli': str(cli), 'export': result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, default=Path(sys.executable).with_name('harnessie'))
    parser.add_argument('--reference', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'tests/fixtures/aidr-0.1.0')
    args = parser.parse_args()
    def forbidden(*unused, **kwargs):
        raise RuntimeError('Demo attempted live model construction or network access')
    try:
        # Installed CLI and reference subprocesses consume only local files.
        # In-process execution is restricted to the explicitly injected mocks.
        with patch('harness.runner.build_model', forbidden), patch('socket.socket.connect', forbidden), \
                patch('socket.create_connection', forbidden):
            result = demonstrate(args.cli.absolute(), args.reference.resolve())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f'mock export demo FAILED: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
