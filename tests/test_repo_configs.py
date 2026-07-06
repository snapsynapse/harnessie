"""Smoke tests for the SHIPPED configs and prompts, not synthetic fixtures.
These exist because a green suite over tmp-dir fixtures once hid an
unparseable config/models.yaml from the operator quick start."""

from pathlib import Path

import yaml
import pytest

from harness.models.base import EFFORT_LEVELS
from harness.roles import RoleLibrary
from harness.routing import TIER_ORDER
from harness.runner import load_models_config

ROOT = Path(__file__).resolve().parents[1]


def test_models_yaml_parses_and_routing_is_valid():
    cfg = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())
    assert set(cfg["tiers"]) <= set(TIER_ORDER)
    for task_class, row in cfg["routing"].items():
        assert row["tier"] in cfg["tiers"], task_class
        assert row["effort"] in EFFORT_LEVELS, task_class
    assert cfg["budget"]["max_usd"] > 0
    load_models_config(ROOT / "config" / "models.yaml")


def test_bad_routing_tier_fails_config_load(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("""
tiers:
  mid:
    provider: mock
    model_id: mock
routing:
  plan: { tier: frontier, effort: high }
budget:
  max_usd: 1.0
  max_tokens: 1000
""")
    with pytest.raises(ValueError, match="not configured"):
        load_models_config(path)


def test_workflows_parse_and_reference_real_agents():
    lib = RoleLibrary.load(ROOT / "agents")
    workflows = sorted((ROOT / "workflows").glob("*.yaml"))
    assert workflows, "no workflows shipped"
    for wf_path in workflows:
        wf = yaml.safe_load(wf_path.read_text())
        assert wf.get("phases"), wf_path.name
        for phase in wf["phases"]:
            assert "task" in phase, f"{wf_path.name}:{phase.get('name')}"
            if phase.get("mode") == "adversarial":
                positions = phase.get("positions")
                assert positions, f"{wf_path.name}:{phase['name']} has no positions"
                for pos in positions:
                    lib.get(pos.get("agent", "implementer"))   # raises on unknown
                assert phase.get("arbitration", "convergence") in (
                    "convergence", "human"), f"{wf_path.name}:{phase['name']}"
            else:
                lib.get(phase.get("agent", "orchestrator"))   # raises on unknown
            # tool paths are workspace-relative; a task telling the agent to
            # touch "workspace/..." double-prefixes and fails its own gate
            assert "workspace/" not in phase["task"], \
                f"{wf_path.name}:{phase['name']} uses project-relative paths"


def test_eval_suites_parse():
    suites = sorted((ROOT / "evals").glob("*.yaml"))
    assert suites, "no eval suites shipped"
    for suite_path in suites:
        suite = yaml.safe_load(suite_path.read_text())
        assert suite.get("scenarios"), suite_path.name
        ids = [s["id"] for s in suite["scenarios"]]
        assert len(ids) == len(set(ids)), suite_path.name
