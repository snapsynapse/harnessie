"""SEC-20261118-005: an invalid approval policy or an explicit deny is decided
before any workflow preapproval, policy allow, or TTY answer."""

import json
import textwrap
from unittest.mock import patch

import pytest

from harness.memory import ProjectMemory
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner

TOOL = "expire_fact"
PHASE = "triage"


def _scaffold(root, approve_tools=()):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock
        routing:
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    grants = f"    approve_tools: {list(approve_tools)}\n" if approve_tools else ""
    (root / "workflows" / "triage.yaml").write_text(
        "name: memory-triage\nphases:\n  - name: triage\n    agent: implementer\n"
        "    task: \"Expire stale fact.\"\n" + grants
        + "    verify:\n      max_attempts: 1\n      memory_lint: true\n")
    ProjectMemory(root / "memory").save_fact(
        "Stale fact", "past due", source="seed", verify_by="2020-01-01")


def _runner(root, policy_text=None, interactive=False, run_id="prec"):
    policy = None
    if policy_text is not None:
        policy = root / "approval-policy.yaml"
        policy.write_text(textwrap.dedent(policy_text), encoding="utf-8")
    return WorkflowRunner(project_root=root, run_id=run_id, echo=False,
                          approval_policy=policy,
                          interactive_approvals=interactive)


def _events(runner):
    return [json.loads(line) for line in
            (runner.run_dir / "events.jsonl").read_text().splitlines()
            if line.strip()]


def _approval_events(runner):
    return [(e["kind"], e.get("source")) for e in _events(runner)
            if e["kind"].startswith("approval_")]


GLOBAL_DENY = """
    deny:
      - tool: expire_fact
"""
PHASE_DENY = """
    deny:
      - tool: expire_fact
        phase: triage
"""
DENY_AND_ALLOW = """
    allow:
      - tool: expire_fact
    deny:
      - tool: expire_fact
        phase: triage
"""
OTHER_PHASE_DENY = """
    deny:
      - tool: expire_fact
        phase: elsewhere
"""
ALLOW = """
    allow:
      - tool: expire_fact
        phase: triage
"""
MALFORMED = """
    allow: [
"""
SCHEMA_INVALID = """
    allow: not-a-list
"""


@pytest.mark.parametrize("policy_text", [GLOBAL_DENY, PHASE_DENY, DENY_AND_ALLOW])
@pytest.mark.parametrize("granted", [True, False])
@pytest.mark.parametrize("tty_answer", [True, None])
def test_explicit_deny_wins_over_every_grant(tmp_path, policy_text, granted,
                                            tty_answer):
    _scaffold(tmp_path)
    runner = _runner(tmp_path, policy_text, interactive=True)
    handler = runner._approval_handler_for(
        PHASE, frozenset({TOOL}) if granted else frozenset())
    with patch("harness.runner.tty_approval", return_value=tty_answer) as tty:
        assert handler(TOOL, {}) is False
    tty.assert_not_called()
    assert _approval_events(runner)[-1] == ("approval_denied", "policy-file")
    assert ("approval_granted", "workflow-config") not in _approval_events(runner)


@pytest.mark.parametrize("policy_text", [MALFORMED, SCHEMA_INVALID])
@pytest.mark.parametrize("granted", [True, False])
def test_invalid_policy_denies_before_workflow_grant_and_tty(
        tmp_path, policy_text, granted):
    _scaffold(tmp_path)
    runner = _runner(tmp_path, policy_text, interactive=True)
    assert runner.approval_policy.problems
    handler = runner._approval_handler_for(
        PHASE, frozenset({TOOL}) if granted else frozenset())
    with patch("harness.runner.tty_approval", return_value=True) as tty:
        assert handler(TOOL, {}) is False
    tty.assert_not_called()
    kinds = [e["kind"] for e in _events(runner)]
    assert "approval_policy_invalid" in kinds
    assert ("approval_denied", "policy-file") in _approval_events(runner)
    assert not any(k == "approval_granted" for k, _ in _approval_events(runner))


def test_missing_policy_file_denies_workflow_grant(tmp_path):
    _scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="missing", echo=False,
                            approval_policy=tmp_path / "absent.yaml")
    handler = runner._approval_handler_for(PHASE, frozenset({TOOL}))
    assert handler(TOOL, {}) is False


@pytest.mark.parametrize("policy_text,granted,tty_answer,source", [
    (None, True, None, "workflow-config"),
    (OTHER_PHASE_DENY, True, None, "workflow-config"),
    (ALLOW, False, None, "policy-file"),
    (ALLOW, True, None, "workflow-config"),
    (None, False, True, "tty"),
    (OTHER_PHASE_DENY, False, True, "tty"),
])
def test_valid_grants_still_allow(tmp_path, policy_text, granted, tty_answer,
                                  source):
    _scaffold(tmp_path)
    runner = _runner(tmp_path, policy_text, interactive=tty_answer is not None)
    handler = runner._approval_handler_for(
        PHASE, frozenset({TOOL}) if granted else frozenset())
    with patch("harness.runner.tty_approval", return_value=tty_answer):
        assert handler(TOOL, {}) is True
    assert _approval_events(runner)[-1] == ("approval_granted", source)


def test_no_rule_and_no_grant_default_denies(tmp_path):
    _scaffold(tmp_path)
    runner = _runner(tmp_path, OTHER_PHASE_DENY)
    handler = runner._approval_handler_for(PHASE, frozenset())
    assert handler(TOOL, {}) is False
    assert _approval_events(runner)[-1] == ("approval_denied", "default-deny")


def test_policy_deny_blocks_workflow_preapproved_side_effect(tmp_path):
    """End to end: the preapproved expire_fact never archives the fact."""
    _scaffold(tmp_path, approve_tools=[TOOL])
    runner = _runner(tmp_path, PHASE_DENY)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=[
            AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="c1", name="accept_task", arguments={})]),
            AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="c2", name=TOOL,
                         arguments={"slug": "stale-fact", "reason": "old"})]),
            AssistantTurn(content="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="c3", name="task_complete",
                         arguments={"report": "done"})]),
        ])
    runner.run_workflow(tmp_path / "workflows" / "triage.yaml")
    assert not (tmp_path / "memory" / "archive" / "stale-fact.md").exists()
    assert (tmp_path / "memory" / "facts" / "stale-fact.md").exists()
    assert ("approval_denied", "policy-file") in _approval_events(runner)
