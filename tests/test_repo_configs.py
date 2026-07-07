"""Smoke tests for the SHIPPED configs and prompts, not synthetic fixtures.
These exist because a green suite over tmp-dir fixtures once hid an
unparseable config/models.yaml from the operator quick start."""

import inspect
from pathlib import Path

import yaml
import pytest

from harness.models.base import EFFORT_LEVELS
from harness.roles import RoleLibrary
from harness.routing import TIER_ORDER
from harness.runner import WorkflowRunner, load_models_config
from harness.tools.registry import PermissionDenied, ToolRegistry
from harness.tools.builtin import register_builtin

ROOT = Path(__file__).resolve().parents[1]


def _shipped_registry(tmp_path) -> ToolRegistry:
    """The built-in tool registry exactly as a run wires it — the shipped
    policy surface, not a synthetic fixture."""
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    reg = ToolRegistry()
    register_builtin(reg, workspace=ws)
    return reg


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


# -- Default-deny posture audit (0.6.0 launch gate) -------------------------
# One pass proving every tool grant, network allowance, and approval gate in
# the SHIPPED configs defaults closed. These assert over register_builtin and
# the shipped OWNERSHIP.yaml / models.yaml, not tmp fixtures, so a permission
# loosened in the real surface fails here.

def test_default_approval_handler_denies():
    # A registry with no approval handler wired must fail closed, so a
    # misconfigured headless run cannot silently run an approval-gated tool.
    reg = ToolRegistry()
    assert reg.approval_handler("any_tool", {}) is False


def test_orchestrator_has_no_side_effecting_tools(tmp_path):
    # The orchestrator boundary says it has no tools with side effects; the
    # policy surface must actually enforce that, not just say it in a prompt.
    reg = _shipped_registry(tmp_path)
    for spec in reg.for_role("orchestrator"):
        assert spec.effects == "read", \
            f"orchestrator granted side-effecting tool {spec.name!r} ({spec.effects})"


def test_verifier_never_writes(tmp_path):
    # Verifier is read-only plus test execution: read/execute allowed, no write.
    reg = _shipped_registry(tmp_path)
    for spec in reg.for_role("verifier"):
        assert spec.effects in ("read", "execute"), spec.name
        assert spec.effects != "write", \
            f"verifier granted write tool {spec.name!r}"


def test_side_effecting_tools_exclude_orchestrator_and_include_worker(tmp_path):
    # Mutation is the worker's lane. Every write/execute tool must be denied to
    # the orchestrator and granted to the worker — side effects never leak into
    # the planning seat.
    reg = _shipped_registry(tmp_path)
    side_effecting = [t for t in reg.tools.values()
                      if t.effects in ("write", "execute")]
    assert side_effecting, "expected at least one side-effecting tool shipped"
    for spec in side_effecting:
        assert "orchestrator" not in spec.allowed_roles, \
            f"{spec.name!r} ({spec.effects}) is reachable by the orchestrator"
        assert "worker" in spec.allowed_roles, spec.name


def test_destructive_fact_tool_requires_approval(tmp_path):
    # expire_fact is the one irreversible memory op; it must be approval-gated.
    reg = _shipped_registry(tmp_path)
    assert reg.tools["expire_fact"].requires_approval is True


def test_dispatch_and_loop_default_network_off():
    # Network is opt-in at every seam: the dispatch entry point and the agent
    # loop factory both default allow_network to False.
    assert inspect.signature(ToolRegistry.dispatch).parameters[
        "allow_network"].default is False
    assert inspect.signature(WorkflowRunner._loop_for).parameters[
        "allow_network"].default is False


def test_unknown_tool_is_refused(tmp_path):
    reg = _shipped_registry(tmp_path)
    result = reg.dispatch("worker", "no_such_tool", {})
    assert result.ok is False
    assert result.refusal.error == "action_unsupported"


def test_role_without_grant_is_denied(tmp_path):
    # The orchestrator calling a worker-only write tool is a hard denial.
    reg = _shipped_registry(tmp_path)
    with pytest.raises(PermissionDenied):
        reg.dispatch("orchestrator", "write_file",
                     {"path": "x.txt", "content": "y"})


def test_approval_gated_tool_fails_closed_under_default_handler(tmp_path):
    # Default (deny) handler + an approval-gated tool = refusal, not mutation.
    reg = _shipped_registry(tmp_path)
    result = reg.dispatch("worker", "expire_fact", {"slug": "whatever"})
    assert result.ok is False
    assert result.refusal.error == "approval_required"


def test_side_effects_locked_refuses_mutation_before_consent(tmp_path):
    # Consent lock: a side-effecting tool called before accept_task is refused.
    reg = _shipped_registry(tmp_path)
    result = reg.dispatch("worker", "write_file",
                          {"path": "x.txt", "content": "y"},
                          side_effects_locked=True)
    assert result.ok is False
    assert result.refusal.error == "consent_required"


def test_ownership_config_ships_operator_lane():
    # The operator lane concept ships even when empty, and files are
    # first-writer auto-claims (no pre-granted agent ownership).
    cfg = yaml.safe_load((ROOT / "OWNERSHIP.yaml").read_text())
    assert "operator" in cfg["lanes"], "operator lane missing from ledger"
    assert cfg["files"] == {}, "shipped ledger must not pre-claim files for agents"
