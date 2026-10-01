"""Disposable pilot input integrity and offline admission checks."""
import json
from pathlib import Path

import pytest

from scripts.pilot_contract import PilotRefusal
from scripts.pilot_prepare import SOURCE_FILES, prepare_packet, verify_packet, capture_packet_identity
from scripts.pilot_policy import CLAUDE_MAX_HAIKU_CONTEXT

ROOT = Path(__file__).resolve().parents[1]


def test_packet_is_exact_allowlist_with_zero_live_allowance(tmp_path):
    root = tmp_path / "pilot"
    receipt = prepare_packet(ROOT, root)
    manifest = verify_packet(root, receipt["manifest_sha256"])
    assert manifest["live_allowance"] == {"claude": 0, "qwen": 0}
    assert manifest["question"].startswith("Should Harnessie proceed")
    assert {f"workspace/evidence/{p}" for p in SOURCE_FILES} <= set(manifest["files"])
    assert not (root / "workspace" / "historical-brief.md").exists()
    assert manifest["participants"]["claude"]["transport"] == "claude-code-max-pilot"
    assert manifest["participants"]["claude"]["cost_usd"] is None
    assert manifest["participants"]["claude"]["additional_model_policy"] == CLAUDE_MAX_HAIKU_CONTEXT.as_dict()
    plan = json.loads((root / "pilot-provider-plan.json").read_text())
    assert plan["participants"]["claude"]["additional_model_policy"] == CLAUDE_MAX_HAIKU_CONTEXT.as_dict()
    assert plan["limits_approved"] is False


@pytest.mark.parametrize("name", ["workspace/evidence/INTENT.md", "config/models.yaml", "pilot-provider-plan.json"])
def test_changed_frozen_inputs_refuse(tmp_path, name):
    root = tmp_path / "pilot"
    receipt = prepare_packet(ROOT, root)
    (root / name).write_text("changed")
    with pytest.raises(PilotRefusal, match="packet_drift"):
        verify_packet(root, receipt["manifest_sha256"])


def test_manifest_cannot_reseal_itself(tmp_path):
    root = tmp_path / "pilot"
    receipt = prepare_packet(ROOT, root)
    path = root / "pilot-manifest.json"
    data = json.loads(path.read_text())
    data["live_allowance"]["claude"] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(PilotRefusal, match="manifest_drift"):
        verify_packet(root, receipt["manifest_sha256"])


def test_extra_input_and_symlink_refuse(tmp_path):
    root = tmp_path / "pilot"
    receipt = prepare_packet(ROOT, root)
    (root / "workspace" / "extra.txt").write_text("unreviewed")
    with pytest.raises(PilotRefusal, match="unexpected_input"):
        verify_packet(root, receipt["manifest_sha256"])
    (root / "workspace" / "extra.txt").unlink()
    path = root / "workspace/evidence/INTENT.md"
    path.unlink()
    path.symlink_to(ROOT / "INTENT.md")
    with pytest.raises(PilotRefusal, match="unsafe_path"):
        verify_packet(root, receipt["manifest_sha256"])


def test_existing_destination_preserved(tmp_path):
    marker = tmp_path / "existing.txt"
    marker.write_text("preserve me")
    with pytest.raises(PilotRefusal, match="destination_exists"):
        prepare_packet(ROOT, tmp_path)
    assert marker.read_text() == "preserve me"


def test_source_symlink_refused_before_destination_write(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "INTENT.md").symlink_to(ROOT / "INTENT.md")
    dest = tmp_path / "pilot"
    with pytest.raises(PilotRefusal, match="unsafe_path"):
        prepare_packet(repo, dest)
    assert not dest.exists()


def test_identity_is_derived_from_sealed_plan_and_refuses_drift(tmp_path, monkeypatch):
    root = tmp_path / "pilot"
    packet = prepare_packet(ROOT, root)
    seal = packet["manifest_sha256"]
    expected = verify_packet(root, seal)["participants"]["qwen"]["declared_harness_identity"]
    captured = []

    def capture(**kwargs):
        captured.append(kwargs["harness_identity"])
        return {"fingerprint": "fixture"}

    monkeypatch.setattr("scripts.pilot_identity.capture_identity", capture)
    result = capture_packet_identity(root, seal, client_version="fixture")
    assert captured == [expected]
    assert result["manifest_sha256"] == seal
    assert captured[0]["sampling"] == {"temperature": 0.0}

    def mutate(**kwargs):
        (root / "agents/workers/reviewer.md").write_text("changed during metadata capture")
        return {"fingerprint": "fixture"}

    monkeypatch.setattr("scripts.pilot_identity.capture_identity", mutate)
    with pytest.raises(PilotRefusal, match="packet_drift"):
        capture_packet_identity(root, seal, client_version="fixture")
