"""SEC-20261118-006: a resumed run reuses a prior acceptance only when it is
bound to the same goal, workflow, phase contract, inputs and the files that
accepted phase produced. Drift is a structured refusal pointing to a new run;
nothing is re-executed and the journal keeps its recorded acceptance.

The documented remedies stay open: crash recovery, an operator fix after a
halt, OS noise files, and fixing one halted parallel sibling all resume."""

import hashlib
import json
import os
import textwrap

import pytest
import yaml

import harness.maiden as maiden
from harness import sandbox
from harness.maiden import workspace_manifest
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner
from harness.state import RunState

WORKFLOW = {
    "name": "mini",
    "phases": [
        {"name": "plan", "agent": "orchestrator", "task": "Plan for goal: {goal}"},
        {"name": "implement", "agent": "implementer",
         "task": "Do this plan: {plan}",
         "verify": {"max_attempts": 1,
                    "criteria": "greeting.txt exists"}},
        {"name": "integrate", "agent": "orchestrator",
         "task": "Summarize: {implement}"},
    ],
}


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


FIRST_SCRIPT = [
    turn_tool("task_complete", {"report": "PLAN: write greeting.txt"}),
    turn_tool("accept_task", {}),
    turn_tool("write_file", {"path": "greeting.txt", "content": "hello"}),
    turn_tool("task_complete", {"report": "wrote greeting.txt"}),
    turn_tool("task_complete", {"report": "FINAL: done"}),
]


def _scaffold(root, workflow=None):
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
    _write_workflow(root, workflow or WORKFLOW)


def _write_workflow(root, workflow):
    (root / "workflows" / "mini.yaml").write_text(
        yaml.safe_dump(workflow, sort_keys=False))


def _run(root, script, goal="greet", run_id="bound"):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"),
                      script=list(script))
    runner._models["mid"] = brain
    outcomes = runner.run_workflow(root / "workflows" / "mini.yaml", goal=goal)
    return runner, brain, outcomes


def _events(runner, kind):
    return [e for e in (json.loads(line) for line in
            (runner.run_dir / "events.jsonl").read_text().splitlines()
            if line.strip()) if e["kind"] == kind]


def _first_run(root):
    _, _, outcomes = _run(root, FIRST_SCRIPT)
    assert [o.status for o in outcomes] == ["passed"] * 3


def _assert_refused(runner, brain, outcomes, phase, reason):
    assert [o.status for o in outcomes] == ["needs_human"]
    assert outcomes[-1].phase == phase
    refusals = _events(runner, "resume_refused")
    assert [(r["phase"], r["reason"]) for r in refusals] == [(phase, reason)]
    assert refusals[0]["remedy"] == "new_run"
    assert brain.calls == []
    journal = RunState.open(runner.run_dir)
    assert all(journal.result(f"phase:{p['name']}")["status"] == "passed"
               for p in WORKFLOW["phases"])


def test_unchanged_resume_skips_every_accepted_phase(tmp_path):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    runner, brain, outcomes = _run(tmp_path, [])
    assert [o.status for o in outcomes] == ["skipped_resume"] * 3
    assert brain.calls == []
    assert _events(runner, "resume_refused") == []


def test_changed_goal_refuses_resume(tmp_path):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    runner, brain, outcomes = _run(tmp_path, [], goal="a different goal")
    _assert_refused(runner, brain, outcomes, "plan", "goal_changed")


def _mutate(root, fn):
    workflow = json.loads(json.dumps(WORKFLOW))
    fn(workflow)
    _write_workflow(root, workflow)


@pytest.mark.parametrize("mutation,phase,reason", [
    (lambda w: w["phases"][0].__setitem__("task", "Different: {goal}"),
     "plan", "phase_contract_changed"),
    (lambda w: w["phases"][1]["verify"].__setitem__("criteria", "anything"),
     "implement", "phase_contract_changed"),
    (lambda w: w["phases"][1]["verify"].__setitem__(
        "checks", [{"name": "c", "command": "true"}]),
     "implement", "phase_contract_changed"),
    (lambda w: w["phases"].insert(0, {"name": "prep", "agent": "orchestrator",
                                      "task": "prep"}),
     "plan", "upstream_contract_changed"),
    (lambda w: w.__setitem__("name", "renamed"), "plan", "workflow_changed"),
])
def test_changed_workflow_refuses_resume(tmp_path, mutation, phase, reason):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    _mutate(tmp_path, mutation)
    runner, brain, outcomes = _run(tmp_path, [])
    _assert_refused(runner, brain, outcomes, phase, reason)


def test_reordered_phases_refuse_resume(tmp_path):
    workflow = {"name": "mini", "phases": [
        {"name": "a", "agent": "orchestrator", "task": "A {goal}"},
        {"name": "b", "agent": "orchestrator", "task": "B {goal}"},
    ]}
    _scaffold(tmp_path, workflow)
    _run(tmp_path, [turn_tool("task_complete", {"report": "A"}),
                    turn_tool("task_complete", {"report": "B"})])
    workflow["phases"].reverse()
    _write_workflow(tmp_path, workflow)
    runner, brain, outcomes = _run(tmp_path, [])
    assert [o.status for o in outcomes] == ["needs_human"]
    refusal = _events(runner, "resume_refused")[0]
    assert (refusal["phase"], refusal["reason"]) == (
        "b", "upstream_contract_changed")
    assert brain.calls == []


def test_later_phase_contract_change_names_first_drifted_phase(tmp_path):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    _mutate(tmp_path, lambda w: w["phases"][2].__setitem__(
        "task", "Summarize differently: {implement}"))
    runner, brain, outcomes = _run(tmp_path, [])
    _assert_refused(runner, brain, outcomes, "integrate",
                    "phase_contract_changed")


def test_changed_role_prompt_refuses_resume(tmp_path):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    (tmp_path / "agents" / "workers" / "implementer.md").write_text(
        "# Worker\nDo something else.")
    runner, brain, outcomes = _run(tmp_path, [])
    _assert_refused(runner, brain, outcomes, "implement",
                    "phase_contract_changed")


def test_changed_upstream_report_refuses_resume(tmp_path):
    _scaffold(tmp_path)
    _first_run(tmp_path)
    state = RunState.open(tmp_path / "runs" / "bound")
    prior = dict(state.result("phase:plan"))
    prior["report"] = "PLAN: something else entirely"
    state.record("phase:plan", prior)
    runner, brain, outcomes = _run(tmp_path, [])
    assert [o.status for o in outcomes] == ["needs_human"]
    refusal = _events(runner, "resume_refused")[0]
    assert (refusal["phase"], refusal["reason"]) == ("implement", "inputs_changed")
    assert brain.calls == []


def test_changed_workspace_artifact_refuses_resume(tmp_path):
    """The refusal names the accepted phase that produced the changed file
    and the file itself, not merely the first reused phase."""
    _scaffold(tmp_path)
    _first_run(tmp_path)
    (tmp_path / "workspace" / "greeting.txt").write_text("tampered")
    runner, brain, outcomes = _run(tmp_path, [])
    _assert_refused(runner, brain, outcomes, "implement",
                    "reused_output_changed")
    assert _events(runner, "resume_refused")[0]["path"] == "greeting.txt"


def test_unbound_legacy_acceptance_refuses_resume(tmp_path):
    _scaffold(tmp_path)
    run_dir = tmp_path / "runs" / "bound"
    run_dir.mkdir(parents=True)
    RunState.open(run_dir).record(
        "phase:plan", {"status": "passed", "report": "legacy plan"})
    runner, brain, outcomes = _run(tmp_path, [])
    assert [o.status for o in outcomes] == ["needs_human"]
    refusal = _events(runner, "resume_refused")[0]
    assert (refusal["phase"], refusal["reason"]) == ("plan", "unbound_legacy")
    assert brain.calls == []
    assert RunState.open(run_dir).result("phase:plan")["status"] == "passed"


def test_halted_phase_reruns_after_its_own_contract_is_fixed(tmp_path):
    """Fixing the halted phase (the documented remedy) still resumes: only
    accepted phases are bound, and their contracts did not change."""
    _scaffold(tmp_path)
    _, _, outcomes = _run(tmp_path, [
        turn_tool("task_complete", {"report": "PLAN: write greeting.txt"}),
        turn_tool("decline_task", {"reason": "unclear"}),
    ])
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    _mutate(tmp_path, lambda w: w["phases"][1].__setitem__(
        "task", "Clearer: {plan}"))
    runner, brain, outcomes = _run(tmp_path, [
        turn_tool("accept_task", {}),
        turn_tool("write_file", {"path": "greeting.txt", "content": "hello"}),
        turn_tool("task_complete", {"report": "wrote greeting.txt"}),
        turn_tool("task_complete", {"report": "FINAL: done"}),
    ])
    assert [o.status for o in outcomes] == ["skipped_resume", "passed", "passed"]
    assert _events(runner, "resume_refused") == []


def test_parallel_skip_is_not_rejournaled(tmp_path):
    workflow = {"name": "mini", "phases": [
        {"name": "left", "parallel": "g", "agent": "orchestrator",
         "task": "left {goal}"},
        {"name": "right", "parallel": "g", "agent": "orchestrator",
         "task": "right {goal}"},
    ]}
    _scaffold(tmp_path, workflow)

    def brain_fn(messages):
        if "right" in messages[1].content:
            return turn_tool("task_complete", {"report": "RIGHT"})
        return AssistantTurn(content="no tool", stop_reason="error")

    runner = WorkflowRunner(project_root=tmp_path, run_id="bound", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), fn=brain_fn)
    first = runner.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    assert {o.phase: o.status for o in first}["right"] == "passed"
    assert {o.phase: o.status for o in first}["left"] != "passed"

    for _ in range(2):
        again = WorkflowRunner(project_root=tmp_path, run_id="bound", echo=False)
        again._models["mid"] = MockModel(
            ModelSpec(name="mid", provider="mock", model_id="mock"), fn=brain_fn)
        outcomes = again.run_workflow(tmp_path / "workflows" / "mini.yaml",
                                      goal="g")
        assert {o.phase: o.status for o in outcomes}["right"] == "skipped_resume"
        assert RunState.open(again.run_dir).result(
            "phase:right")["status"] == "passed"


# -- remedies that must resume, and the reused-output binding ----------------

SECRET = "pplx-" + "SYNTHETICCANARY" * 3

WRITERS = {
    "name": "writers",
    "phases": [
        {"name": "draft", "agent": "implementer", "task": "Draft for {goal}",
         "verify": {"max_attempts": 1}},
        {"name": "build", "agent": "implementer", "task": "Build from {draft}",
         "verify": {"max_attempts": 1, "checks": [
             {"name": "ready", "command": "test -f ready.txt"}]}},
    ],
}


def _draft(content="v1", path="draft.txt"):
    return [turn_tool("accept_task", {}),
            turn_tool("write_file", {"path": path, "content": content}),
            turn_tool("task_complete", {"report": "drafted"})]


def _build(extra=()):
    return [turn_tool("accept_task", {}), *extra,
            turn_tool("write_file", {"path": "build.txt", "content": "built"}),
            turn_tool("task_complete", {"report": "built"})]


class Crash(Exception):
    """Stands in for a process death mid-phase: nothing journals the phase."""


def _crashing(turns):
    pending = list(turns)

    def fn(messages):
        if not pending:
            raise Crash("simulated crash")
        return pending.pop(0)
    return fn


@pytest.fixture
def writers(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    _scaffold(tmp_path, WRITERS)
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "ready.txt").write_text("operator input")
    return tmp_path


def _assert_resumed(runner, outcomes, statuses):
    assert [o.status for o in outcomes] == statuses
    assert _events(runner, "resume_refused") == []


def _assert_output_refused(runner, brain, outcomes, phase, path):
    assert [o.status for o in outcomes] == ["needs_human"]
    refusal = _events(runner, "resume_refused")
    assert [(r["phase"], r["reason"], r.get("path")) for r in refusal] == [
        (phase, "reused_output_changed", path)]
    assert brain.calls == []


def _crash_in_build(root, build_turns):
    runner = WorkflowRunner(project_root=root, run_id="bound", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        fn=_crashing([*_draft(), turn_tool("accept_task", {}), *build_turns]))
    with pytest.raises(Crash):
        runner.run_workflow(root / "workflows" / "mini.yaml", goal="greet")
    journal = RunState.open(runner.run_dir)
    assert journal.result("phase:draft")["status"] == "passed"
    assert not journal.has("phase:build")


def test_crash_mid_phase_after_a_write_resumes(writers):
    _crash_in_build(writers, [turn_tool(
        "write_file", {"path": "build.txt", "content": "half"})])
    runner, _, outcomes = _run(writers, _build())
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed"])
    assert (writers / "workspace" / "build.txt").read_text() == "built"


def test_crash_then_edit_of_reused_output_still_refuses(writers):
    _crash_in_build(writers, [turn_tool(
        "write_file", {"path": "build.txt", "content": "half"})])
    (writers / "workspace" / "draft.txt").write_text("edited")
    runner, brain, outcomes = _run(writers, _build())
    _assert_output_refused(runner, brain, outcomes, "draft", "draft.txt")


def test_operator_fix_after_needs_human_resumes(writers):
    """The documented remedy: fix what blocked the halted phase (add the
    missing file, edit an operator input), then resume."""
    (writers / "workspace" / "ready.txt").unlink()
    (writers / "workspace" / "notes.txt").write_text("operator notes")
    _, _, outcomes = _run(writers, [*_draft(), *_build()])
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    (writers / "workspace" / "ready.txt").write_text("fixed")
    (writers / "workspace" / "notes.txt").write_text("operator notes, edited")
    runner, _, outcomes = _run(writers, _build())
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed"])


def test_halted_phase_edit_of_upstream_output_does_not_refuse(writers):
    """A halted phase's own unverified writes are redone on resume, even
    when they touched a file an accepted phase produced."""
    (writers / "workspace" / "ready.txt").unlink()
    _, _, outcomes = _run(writers, [*_draft(), *_build([turn_tool(
        "write_file", {"path": "draft.txt", "content": "touched by build"})])])
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    (writers / "workspace" / "ready.txt").write_text("fixed")
    runner, _, outcomes = _run(writers, _build())
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed"])


def test_secret_egress_remedy_resumes(writers):
    (writers / "config" / "boundary.yaml").write_text(
        "enabled: true\ninclude_contextual: false\n")
    (writers / "workspace" / "settings.txt").write_text(f"key = {SECRET}\n")
    read = turn_tool("read_file", {"path": "settings.txt"})
    _, _, outcomes = _run(writers, [*_draft(), *_build([read])])
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    (writers / "workspace" / "settings.txt").write_text(
        "key = from environment\n")
    runner, _, outcomes = _run(writers, _build([read]))
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed"])


def test_os_noise_files_do_not_refuse(writers):
    _run(writers, [*_draft(), *_build()])
    (writers / "workspace" / ".DS_Store").write_bytes(b"\x00\x01finder")
    (writers / "workspace" / "__pycache__").mkdir()
    (writers / "workspace" / "__pycache__" / "m.cpython-311.pyc").write_bytes(
        b"\x00pyc")
    runner, brain, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 2)
    assert brain.calls == []


def test_fifo_in_workspace_neither_blocks_nor_refuses(writers):
    os.mkfifo(writers / "workspace" / "before.fifo")
    _, _, outcomes = _run(writers, [*_draft(), *_build()])
    assert [o.status for o in outcomes] == ["passed", "passed"]
    os.mkfifo(writers / "workspace" / "after.fifo")
    runner, _, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 2)


def test_deleted_reused_output_refuses(writers):
    _run(writers, [*_draft(), *_build()])
    (writers / "workspace" / "build.txt").unlink()
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "build", "build.txt")


def test_later_accepted_overwrite_binds_to_the_later_phase(writers):
    _run(writers, [*_draft(), *_build([turn_tool(
        "write_file", {"path": "draft.txt", "content": "v2"})])])
    runner, _, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 2)
    (writers / "workspace" / "draft.txt").write_text("v1")
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "build", "draft.txt")


def test_reused_output_behind_a_swapped_symlink_parent_refuses(writers):
    _run(writers, [*_draft(path="out/draft.txt"), *_build()])
    workspace = writers / "workspace"
    (workspace / "out").rename(workspace / "elsewhere")
    (workspace / "out").symlink_to("elsewhere")
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "draft", "out/draft.txt")


PARALLEL = {"name": "mini", "phases": [
    {"name": "left", "parallel": "g", "agent": "orchestrator",
     "task": "left {goal}"},
    {"name": "right", "parallel": "g", "agent": "orchestrator",
     "task": "right {goal}"},
]}


def test_fixing_earlier_halted_parallel_sibling_resumes(tmp_path):
    """Siblings share one snapshot: an earlier sibling's contract is not
    upstream of a later one, so fixing it does not refuse the other."""
    workflow = json.loads(json.dumps(PARALLEL))
    _scaffold(tmp_path, workflow)

    def failing_left(messages):
        if "right" in messages[1].content:
            return turn_tool("task_complete", {"report": "RIGHT"})
        return AssistantTurn(content="no tool", stop_reason="error")

    def healthy(messages):
        return turn_tool("task_complete", {"report": "OK"})

    runner = WorkflowRunner(project_root=tmp_path, run_id="bound", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        fn=failing_left)
    first = runner.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    assert {o.phase: o.status for o in first} == {
        "left": "needs_human", "right": "passed"}

    workflow["phases"][0]["task"] = "left, clarified {goal}"
    _write_workflow(tmp_path, workflow)
    again = WorkflowRunner(project_root=tmp_path, run_id="bound", echo=False)
    again._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), fn=healthy)
    outcomes = again.run_workflow(tmp_path / "workflows" / "mini.yaml",
                                  goal="g")
    assert {o.phase: o.status for o in outcomes} == {
        "left": "passed", "right": "skipped_resume"}
    assert _events(again, "resume_refused") == []


def test_changed_parallel_sibling_contract_still_refuses_it(tmp_path):
    workflow = json.loads(json.dumps(PARALLEL))
    _scaffold(tmp_path, workflow)

    def healthy(messages):
        return turn_tool("task_complete", {"report": "OK"})

    runner = WorkflowRunner(project_root=tmp_path, run_id="bound", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), fn=healthy)
    runner.run_workflow(tmp_path / "workflows" / "mini.yaml", goal="g")
    workflow["phases"][1]["task"] = "right, changed {goal}"
    _write_workflow(tmp_path, workflow)
    runner, brain, outcomes = _run(tmp_path, [], goal="g")
    refusal = _events(runner, "resume_refused")
    assert [(r["phase"], r["reason"]) for r in refusal] == [
        ("right", "phase_contract_changed")]
    assert brain.calls == []


# -- the manifest itself ------------------------------------------------------

def test_manifest_streams_files_in_bounded_chunks(tmp_path, monkeypatch):
    data = os.urandom(maiden.HASH_CHUNK_BYTES * 3 + 17)
    (tmp_path / "big.bin").write_bytes(data)
    reads = []
    real_read = os.read

    def tracking_read(fd, size):
        reads.append(size)
        return real_read(fd, size)
    monkeypatch.setattr(maiden.os, "read", tracking_read)
    manifest = workspace_manifest(tmp_path)
    assert manifest["big.bin"].endswith(hashlib.sha256(data).hexdigest())
    assert reads and max(reads) <= maiden.HASH_CHUNK_BYTES


def test_manifest_marks_special_files_and_symlinks_without_reading(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    (tmp_path / "target.txt").write_text("t")
    (tmp_path / "link").symlink_to("target.txt")
    manifest = workspace_manifest(tmp_path)
    assert manifest["pipe"] == "special:fifo"
    assert manifest["link"].startswith("symlink:")
    assert manifest["target.txt"].startswith("file:")


# -- the expected entry is the last journaled toucher's ----------------------

THREE = {"name": "writers", "phases": [
    *WRITERS["phases"],
    {"name": "ship", "agent": "orchestrator", "task": "Ship {build}"},
]}


def _halt_build_after_editing_draft(root, workflow=THREE):
    _write_workflow(root, workflow)
    (root / "workspace" / "ready.txt").unlink()
    _, _, outcomes = _run(root, [*_draft(), *_build([turn_tool(
        "write_file", {"path": "draft.txt", "content": "touched by build"})])])
    assert [o.status for o in outcomes] == ["passed", "needs_human"]
    (root / "workspace" / "ready.txt").write_text("fixed")


def test_superseded_halted_edit_binds_after_its_phase_passes(writers):
    """P11: build halts after editing draft.txt, then passes on resume
    without touching it. A later unchanged resume must not refuse on
    draft's original bytes: the halted record touched the path last."""
    _halt_build_after_editing_draft(writers)
    runner, _, outcomes = _run(writers, [
        *_build(), turn_tool("task_complete", {"report": "shipped"})])
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed", "passed"])
    runner, brain, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 3)
    assert brain.calls == []


def test_superseded_halted_edit_still_binds_its_bytes(writers):
    """P8b: the halted record's post-state stays bound once its phase is
    no longer rerunning, so replacing the file still refuses."""
    _halt_build_after_editing_draft(writers)
    _run(writers, [*_build(), turn_tool("task_complete", {"report": "shipped"})])
    (writers / "workspace" / "draft.txt").write_text("arbitrary bytes")
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "build", "draft.txt")


def test_superseded_halted_edit_binds_while_a_later_phase_reruns(writers):
    """Only the phase rerunning now may change what it last touched: with
    build accepted and ship halted, build's halted edit stays bound."""
    workflow = json.loads(json.dumps(THREE))
    workflow["phases"][2] = {
        "name": "ship", "agent": "implementer", "task": "Ship {build}",
        "verify": {"max_attempts": 1, "checks": [
            {"name": "go", "command": "test -f go.txt"}]}}
    _halt_build_after_editing_draft(writers, workflow)
    ship = [turn_tool("accept_task", {}),
            turn_tool("task_complete", {"report": "shipped"})]
    _, _, outcomes = _run(writers, [*_build(), *ship])
    assert [o.status for o in outcomes] == [
        "skipped_resume", "passed", "needs_human"]
    (writers / "workspace" / "draft.txt").write_text("arbitrary bytes")
    runner, brain, outcomes = _run(writers, ship)
    _assert_output_refused(runner, brain, outcomes, "build", "draft.txt")


def test_halted_then_passed_edit_binds_to_the_new_bytes(writers):
    """A rerun that does edit the upstream file binds to its new bytes."""
    _halt_build_after_editing_draft(writers)
    runner, _, outcomes = _run(writers, [
        *_build([turn_tool("write_file",
                           {"path": "draft.txt", "content": "rebuilt"})]),
        turn_tool("task_complete", {"report": "shipped"})])
    _assert_resumed(runner, outcomes, ["skipped_resume", "passed", "passed"])
    runner, _, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 3)
    (writers / "workspace" / "draft.txt").write_text("touched by build")
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "build", "draft.txt")


# -- noise is narrow; links are part of a file's entry ------------------------

def test_manifest_ignores_only_bytecode_and_finder_files(tmp_path):
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "m.cpython-311.pyc").write_bytes(b"\x00pyc")
    (cache / "m.cpython-311.pyo").write_bytes(b"\x00pyo")
    (cache / "notes.txt").write_text("kept")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / ".DS_Store").write_bytes(b"finder")
    (tmp_path / "loose.pyc").write_bytes(b"\x00not in a cache")
    manifest = workspace_manifest(tmp_path)
    assert sorted(manifest) == ["__pycache__/notes.txt", "loose.pyc"]


def test_phase_output_under_pycache_is_bound(writers):
    _run(writers, [*_draft(path="__pycache__/plan.txt"), *_build()])
    runner, _, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 2)
    (writers / "workspace" / "__pycache__" / "plan.txt").write_text("swapped")
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "draft",
                           "__pycache__/plan.txt")


def test_reused_output_replaced_by_outside_hardlink_refuses(writers):
    _run(writers, [*_draft(), *_build()])
    draft = writers / "workspace" / "draft.txt"
    outside = writers / "outside.txt"
    outside.write_bytes(draft.read_bytes())
    os.chmod(outside, os.stat(draft).st_mode & 0o7777)
    draft.unlink()
    os.link(outside, draft)
    runner, brain, outcomes = _run(writers, [])
    _assert_output_refused(runner, brain, outcomes, "draft", "draft.txt")


def test_multiply_linked_phase_output_resumes_unchanged(writers):
    workflow = json.loads(json.dumps(WRITERS))
    workflow["phases"][1]["verify"]["checks"] = [
        {"name": "link", "command": "ln -f build.txt build.hard"},
        {"name": "ready", "command": "test -f ready.txt"}]
    _write_workflow(writers, workflow)
    _, _, outcomes = _run(writers, [*_draft(), *_build()])
    assert [o.status for o in outcomes] == ["passed", "passed"]
    outputs = RunState.open(writers / "runs" / "bound").result(
        "phase:build")["outputs"]
    assert "links>1" in outputs["build.txt"]
    assert "links>1" in outputs["build.hard"]
    runner, brain, outcomes = _run(writers, [])
    _assert_resumed(runner, outcomes, ["skipped_resume"] * 2)
    assert brain.calls == []
