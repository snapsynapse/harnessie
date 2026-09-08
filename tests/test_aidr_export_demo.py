"""Run the distributed mock walkthrough through its CLI subprocess boundary."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'examples/aidr-export/demo.py'


def test_mock_walkthrough_from_outside_repository(tmp_path):
    if shutil.which('node') is None:
        pytest.skip('Node required by the pinned-reference demonstration')
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    result = subprocess.run([sys.executable, str(DEMO)], cwd=tmp_path, env=env,
                            text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['status'] == 'passed'
    assert receipt['actors'] == 'scripted MockModel only'
    assert receipt['live_model_calls'] == 0
    assert receipt['mock_model_calls'] == 8
    assert receipt['resume_model_calls'] == 0
    assert receipt['initial_status'] == receipt['resume_status'] == 'needs_arbitration'
    assert receipt['export_preserved_inputs'] is True
    assert receipt['format_refusal'] == {'status': 'refused', 'code': 'invalid_record'}
    assert receipt['format_refusal_preserved_inputs'] is True
    assert receipt['participant_labels'] == ['implementer', 'implementer-2']
    assert receipt['reference_spec'] == '0.1.0'
    assert receipt['reference_revision'] == 'a67c41d339d3e70bc3baaf07e652f9cf9d13a5bb'
    assert not Path(receipt['temporary_root']).exists()
    assert not list(tmp_path.iterdir())
    assert result.stderr == ''
