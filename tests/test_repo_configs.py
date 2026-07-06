"""Smoke tests for the SHIPPED configs and prompts, not synthetic fixtures.
These exist because a green suite over tmp-dir fixtures once hid an
unparseable config/models.yaml from the operator quick start."""

from pathlib import Path

import yaml

from harness.models.base import EFFORT_LEVELS
from harness.roles import RoleLibrary
from harness.routing import TIER_ORDER

ROOT = Path(__file__).resolve().parents[1]


def test_models_yaml_parses_and_routing_is_valid():
    cfg = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())
    assert set(cfg["tiers"]) <= set(TIER_ORDER)
    for task_class, row in cfg["routing"].items():
        assert row["tier"] in TIER_ORDER, task_class
        assert row["effort"] in EFFORT_LEVELS, task_class
    assert cfg["budget"]["max_usd"] > 0


def test_workflows_parse_and_reference_real_agents():
    lib = RoleLibrary.load(ROOT / "agents")
    workflows = sorted((ROOT / "workflows").glob("*.yaml"))
    assert workflows, "no workflows shipped"
    for wf_path in workflows:
        wf = yaml.safe_load(wf_path.read_text())
        assert wf.get("phases"), wf_path.name
        for phase in wf["phases"]:
            assert "task" in phase, f"{wf_path.name}:{phase.get('name')}"
            lib.get(phase.get("agent", "orchestrator"))   # raises on unknown
            # tool paths are workspace-relative; a task telling the agent to
            # touch "workspace/..." double-prefixes and fails its own gate
            assert "workspace/" not in phase["task"], \
                f"{wf_path.name}:{phase['name']} uses project-relative paths"
