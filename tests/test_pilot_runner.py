"""Actual runner and exporter rehearsal, with scripted participants only."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.pilot_contract import PilotRefusal
from scripts.pilot_prepare import prepare_packet
from scripts.pilot_runner import rehearse

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("agree", [False, True])
def test_rehearsal_preserves_human_halt_and_frozen_inputs(tmp_path, agree):
    root = tmp_path / "pilot"
    packet = prepare_packet(ROOT, root)
    with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
            patch("harness.runner.build_model", side_effect=AssertionError("provider factory forbidden")):
        result = rehearse(root, packet["manifest_sha256"], agree=agree)
    assert result["status"] == "passed"
    assert result["live_model_calls"] == 0
    assert result["mock_model_calls"] == 8
    assert result["initial_status"] == result["resume_status"] == "needs_arbitration"
    assert result["resume_model_calls"] == 0
    assert result["chain"]["ok"]
    assert result["input_hashes_unchanged"]
    assert result["reference_lint"] == "passed"
    text = (root / result["export_path"]).read_text()
    assert text.split("## Arbitration\n")[1].split("## Evidence")[0].strip() == ""
    assert "SCRIPTED" in text
    with pytest.raises(PilotRefusal, match="rehearsal_exists"):
        rehearse(root, packet["manifest_sha256"])


def test_mutated_packet_cannot_start_runner(tmp_path):
    root = tmp_path / "pilot"
    packet = prepare_packet(ROOT, root)
    (root / "workspace/question.md").write_text("replacement question")
    with patch("scripts.pilot_runner.WorkflowRunner", side_effect=AssertionError("must not start")):
        with pytest.raises(PilotRefusal, match="packet_drift"):
            rehearse(root, packet["manifest_sha256"])
