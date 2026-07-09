"""Deterministic eval runner for Harnessie.

The baseline suite uses a scripted mock brain, not live endpoints. That keeps
it network-free and makes it suitable for CI. Live brain scorecards are a later
layer built on the same scenario shape.
"""

from __future__ import annotations

import json
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .events import EventLog
from .loop import AgentLoop
from .models.base import AssistantTurn, Message, MockModel, ModelSpec, ToolCall
from .runner import WorkflowRunner
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import parse_verdict


@dataclass
class EvalCaseResult:
    id: str
    passed: bool
    expected: Any
    observed: Any
    notes: str = ""


def load_eval_files(root: Path, suite_path: Path | None = None) -> list[Path]:
    if suite_path is not None:
        return [suite_path]
    eval_dir = root / "evals"
    return sorted(eval_dir.glob("*.yaml")) if eval_dir.exists() else []


def run_eval_suite(root: Path, suite_path: Path | None = None) -> dict[str, Any]:
    files = load_eval_files(root, suite_path)
    results: list[EvalCaseResult] = []
    for path in files:
        suite = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for scenario in suite.get("scenarios", []):
            results.append(run_scenario(scenario, root=root))
    passed = sum(1 for r in results if r.passed)
    return {
        "passed": passed,
        "total": len(results),
        "results": [r.__dict__ for r in results],
    }


def run_scenario(scenario: dict[str, Any], root: Path | None = None) -> EvalCaseResult:
    kind = scenario.get("kind")
    if kind == "verdict":
        verdict = parse_verdict(scenario.get("report", ""))
        expected = bool(scenario["expect_passed"])
        observed = verdict.passed
        return EvalCaseResult(
            id=scenario["id"],
            passed=observed == expected,
            expected=expected,
            observed=observed,
            notes=verdict.reasons,
        )
    if kind == "loop":
        return _run_loop_scenario(scenario)
    if kind == "workflow":
        return _run_workflow_scenario(scenario)
    if kind == "resume":
        return _run_resume_scenario(scenario)
    if kind == "ownership":
        return _run_ownership_scenario(scenario)
    if kind == "adversarial":
        return _run_adversarial_scenario(scenario)
    if kind == "audit":
        return _run_audit_scenario(scenario)
    if kind == "triage":
        return _run_triage_scenario(scenario)
    if kind == "parallel":
        return _run_parallel_scenario(scenario)
    if kind == "repo_hygiene":
        return _run_repo_hygiene_scenario(scenario, root)
    if kind == "canary_leak":
        return _run_canary_leak_scenario(scenario)
    return EvalCaseResult(
        id=scenario.get("id", "(missing-id)"),
        passed=False,
        expected="known scenario kind",
        observed=kind,
        notes="unknown scenario kind",
    )


def _check_file_expectations(scenario: dict[str, Any], workspace: Path,
                             problems: list[str]) -> None:
    expect_file = scenario.get("expect_file")
    if expect_file:
        target = workspace / expect_file["path"]
        if not target.exists():
            problems.append(f"expected file missing: {expect_file['path']}")
        elif expect_file.get("contains") and \
                expect_file["contains"] not in target.read_text(encoding="utf-8"):
            problems.append(f"file {expect_file['path']} lacks expected content")
    absent = scenario.get("expect_file_absent")
    if absent and (workspace / absent).exists():
        problems.append(f"file should not exist: {absent}")


def _run_loop_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        run_dir = root / "run"
        reg = ToolRegistry()
        workspace = root / "workspace"
        workspace.mkdir()
        register_builtin(reg, workspace=workspace)
        model = MockModel(
            ModelSpec(name="mid", provider="mock", model_id="mock"),
            script=[_turn(t, i) for i, t in enumerate(scenario.get("script", []), 1)],
        )
        loop = AgentLoop(
            role=scenario.get("role", "worker"),
            model=model,
            registry=reg,
            events=EventLog(run_dir, echo=False),
            max_steps=int(scenario.get("max_steps", 6)),
            agent_name=scenario.get("agent", "implementer"),
            consent_required=bool(scenario.get("consent", False)),
        )
        result = loop.run("system", scenario.get("task", "task"))
        expected = scenario["expect_stop"]
        if result.stop != expected:
            problems.append(f"stop={result.stop}, expected {expected}")
        _check_file_expectations(scenario, workspace, problems)
        _check_refusal_expectations(scenario, run_dir, problems)
        _check_events_absent(scenario, run_dir, problems)
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=expected,
        observed=result.stop if not problems else problems,
        notes=result.report[:500],
    )


def _check_refusal_expectations(scenario: dict[str, Any], run_dir: Path,
                                problems: list[str]) -> None:
    expected = scenario.get("expect_refusal")
    if not expected:
        return
    events_path = run_dir / "events.jsonl"
    events = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    refusals = [e for e in events if e.get("kind") == "refusal"]
    if not refusals:
        problems.append("expected refusal event, observed none")
        return
    expected_event = {k: v for k, v in expected.items() if k != "content_fields"}
    matching = [e for e in refusals
                if all(e.get(key) == value
                       for key, value in expected_event.items())]
    if expected_event and not matching:
        problems.append(f"no refusal event matching {expected_event!r}")
    # Field presence is asserted on the refusal event, which carries the full
    # grammar; tool_result content is truncated at 300 chars and is not a
    # stable surface to parse.
    fields = expected.get("content_fields") or []
    targets = matching or refusals
    for field in fields:
        if not any(e.get(field) for e in targets):
            problems.append(f"refusal event lacks field {field!r}")


def _check_events_absent(scenario: dict[str, Any], run_dir: Path,
                         problems: list[str]) -> None:
    """Assert canary strings never reach the events log, anywhere.

    `expect_events_absent` lists exact strings (canary credentials, seeded
    PII) that must not appear in any event line: not in refusal detail, not
    in truncated tool_result content, not in any field. This is the
    exfiltration claim made falsifiable: refusals carry kind labels, never
    value fragments.
    """
    canaries = scenario.get("expect_events_absent") or []
    if not canaries:
        return
    events_path = run_dir / "events.jsonl"
    raw = events_path.read_text(encoding="utf-8") if events_path.exists() else ""
    for canary in canaries:
        if canary in raw:
            # Name the canary by prefix only, so even the eval report never
            # carries a full credential-shaped string.
            problems.append(f"canary string leaked into events log: {canary[:12]}...")


def _run_ownership_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    """Sequential worker loops as different agents over one shared workspace
    and ownership ledger; assertions on final ownership and file contents."""
    from .ownership import OwnershipLedger

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        workspace = root / "workspace"
        workspace.mkdir()
        lanes = scenario.get("lanes", {}) or {}
        ledger = OwnershipLedger.load(root / "OWNERSHIP.yaml")
        ledger.agent_lanes = {a: list(g) for a, g in (lanes.get("agent") or {}).items()}
        ledger.collaborative = list(lanes.get("collaborative") or [])
        ledger.operator = list(lanes.get("operator") or [])
        events = EventLog(root / "run", echo=False)
        reg = ToolRegistry()
        register_builtin(reg, workspace=workspace, ledger=ledger, events=events)
        for step in scenario.get("steps", []):
            model = MockModel(
                ModelSpec(name="mid", provider="mock", model_id="mock"),
                script=[_turn(t, i) for i, t in enumerate(step.get("script", []), 1)],
            )
            AgentLoop(role="worker", model=model, registry=reg, events=events,
                      max_steps=int(scenario.get("max_steps", 8)),
                      agent_name=step.get("agent", "implementer")).run(
                "system", step.get("task", "task"))
        reloaded = OwnershipLedger.load(root / "OWNERSHIP.yaml")
        for rel, owner in (scenario.get("expect_owner") or {}).items():
            actual = reloaded.owner_of(rel)
            if actual != owner:
                problems.append(f"owner of {rel}: {actual!r}, expected {owner!r}")
        _check_file_expectations(scenario, workspace, problems)
        _check_refusal_expectations(scenario, root / "run", problems)
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected="ownership expectations hold",
        observed=problems or "ok",
    )


def _run_adversarial_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    """A contested phase driven by a scripted brain. With arbitration_text the
    eval simulates the OPERATOR editing the record between runs (the eval
    fixture plays the human; at runtime no code path does this)."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=2, adversarial=True)
        first = _run_scripted_workflow(root, "evalrun", scenario.get("script", []),
                                       scenario.get("goal", "eval goal"),
                                       workflow="adv.yaml")
        arbitration_text = scenario.get("arbitration_text")
        if arbitration_text is None:
            expected: Any = scenario["expect_statuses"]
            if first != expected:
                problems.append(f"statuses={first}, expected {expected}")
        else:
            expected = {"first": scenario["expect_first_statuses"],
                        "second": scenario["expect_second_statuses"]}
            if first != expected["first"]:
                problems.append(f"first statuses={first}")
            record = root / "runs" / "evalrun" / "decisions" / "DR-decide.md"
            text = record.read_text(encoding="utf-8")
            text = text.replace("status: open", "status: arbitrated")
            text = text.replace("date: ", "decided: 2026-01-02\ndate: ", 1)
            text = text.replace(
                "## Arbitration\n",
                "## Arbitration\n\n- decided_by: operator\n- date: 2026-01-02\n"
                f"- decision: {arbitration_text}\n\nOperator rationale.\n")
            record.write_text(text, encoding="utf-8")
            second = _run_scripted_workflow(root, "evalrun", [],
                                            scenario.get("goal", "eval goal"),
                                            workflow="adv.yaml")
            if second != expected["second"]:
                problems.append(f"second statuses={second}")
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=expected,
        observed=problems or "ok",
    )


def _run_triage_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    """Memory-triage workflow over seeded facts: approval-gated expiry applies
    or fails closed to propose-only; memory_lint gates the phase."""
    from .memory import ProjectMemory

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=1, triage=True,
                               approve_expiry=bool(scenario.get("approve_expiry")))
        mem = ProjectMemory(root / "memory")
        mem.save_fact("Fresh fact", "still good", source="seed",
                      verify_by="2099-01-01")
        mem.save_fact("Stale fact", "past due", source="seed",
                      verify_by="2020-01-01")
        if scenario.get("corrupt_index"):
            mem.index_path.write_text(mem.index_path.read_text()
                                      + "- [Ghost](facts/ghost.md) `lesson`\n")
        approval_policy = None
        if scenario.get("approval_policy"):
            approval_policy = root / "approval-policy.yaml"
            approval_policy.write_text(yaml.safe_dump(scenario["approval_policy"]),
                                       encoding="utf-8")
        statuses = _run_scripted_workflow(root, "evalrun",
                                          scenario.get("script", []),
                                          scenario.get("goal", ""),
                                          workflow="triage.yaml",
                                          approval_policy=approval_policy)
        expected = scenario["expect_statuses"]
        if statuses != expected:
            problems.append(f"statuses={statuses}, expected {expected}")
        if scenario.get("expect_fact") and not \
                (root / "memory" / "facts" / f"{scenario['expect_fact']}.md").exists():
            problems.append(f"expected fact missing: {scenario['expect_fact']}")
        if scenario.get("expect_archived"):
            slug = scenario["expect_archived"]
            if (root / "memory" / "facts" / f"{slug}.md").exists() or not \
                    (root / "memory" / "archive" / f"{slug}.md").exists():
                problems.append(f"fact not archived: {slug}")
        if scenario.get("expect_fact_kept"):
            slug = scenario["expect_fact_kept"]
            if not (root / "memory" / "facts" / f"{slug}.md").exists():
                problems.append(f"fact should have been kept: {slug}")
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=expected,
        observed=problems or "ok",
    )


def _run_parallel_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    from .audit import verify_chain

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=1, parallel=True)

        def brain(messages: list[Message]) -> AssistantTurn:
            task = messages[1].content
            if messages[-1].name == "accept_task" and "Write left" in task:
                content = "wrong" if scenario.get("fail_phase") == "left" else "left"
                return _turn({"tool": "write_file",
                              "args": {"path": "out.txt", "content": content}}, 1)
            if messages[-1].name == "accept_task" and "Write right" in task:
                content = "wrong" if scenario.get("fail_phase") == "right" else "right"
                return _turn({"tool": "write_file",
                              "args": {"path": "out.txt", "content": content}}, 1)
            if messages[-1].name == "write_file":
                return _turn({"tool": "task_complete",
                              "args": {"report": f"wrote {task.split()[1]}"}}, 1)
            if "Plan for goal" in task:
                return _turn({"tool": "task_complete", "args": {"report": "PLAN"}}, 1)
            if "Verify completed work" in task:
                failed_left = scenario.get("fail_phase") == "left" and "Write left" in task
                failed_right = scenario.get("fail_phase") == "right" and "Write right" in task
                if failed_left or failed_right:
                    return _turn({"tool": "task_complete",
                                  "args": {"report": '{"passed": false, "reasons": "wrong artifact"}'}}, 1)
                return _turn({"tool": "task_complete",
                              "args": {"report": '{"passed": true, "reasons": "artifact ok"}'}}, 1)
            if "Write left" in task or "Write right" in task:
                time.sleep(0.2)
                return _turn({"tool": "accept_task", "args": {}}, 1)
            if "Summarize" in task:
                return _turn({"tool": "task_complete", "args": {"report": "FINAL"}}, 1)
            return _turn({"tool": "task_complete", "args": {"report": "done"}}, 1)

        runner = WorkflowRunner(project_root=root, run_id="evalrun", echo=False)
        runner._models["mid"] = MockModel(
            ModelSpec(name="mid", provider="mock", model_id="mock"),
            fn=brain)
        start = time.monotonic()
        outcomes = runner.run_workflow(root / "workflows" / "parallel.yaml",
                                       goal=scenario.get("goal", "eval goal"))
        elapsed = time.monotonic() - start
        observed = [o.status for o in outcomes]
        expected = scenario["expect_statuses"]
        if observed != expected:
            problems.append(f"statuses={observed}, expected {expected}")
        limit = scenario.get("expect_elapsed_lt")
        if limit is not None and elapsed >= float(limit):
            problems.append(f"elapsed={elapsed:.3f}, expected < {limit}")
        for rel, content in (scenario.get("expect_files") or {}).items():
            target = root / "workspace" / ".phases" / rel
            if not target.exists():
                problems.append(f"expected file missing: {rel}")
            elif target.read_text(encoding="utf-8") != content:
                problems.append(f"file {rel} content mismatch")
        for rel in scenario.get("expect_root_absent") or []:
            if (root / "workspace" / rel).exists():
                problems.append(f"root workspace file should be absent: {rel}")
        if scenario.get("expect_audit_ok") is not None:
            ok = verify_chain(root / "runs" / "evalrun")["ok"]
            if ok != bool(scenario["expect_audit_ok"]):
                problems.append(f"audit chain ok={ok}")
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=expected,
        observed=problems or "ok",
    )


def _run_repo_hygiene_scenario(
    scenario: dict[str, Any],
    root: Path | None,
) -> EvalCaseResult:
    root = (root or Path.cwd()).resolve()
    problems: list[str] = []
    paths: list[Path] = []
    for pattern in scenario.get("paths", []):
        paths.extend(sorted(root.glob(pattern)))
    paths = [p for p in dict.fromkeys(paths) if p.is_file()]
    for path in paths:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in scenario.get("deny_contains", []):
            if needle in text:
                problems.append(f"{rel} contains forbidden text {needle!r}")
        for required in scenario.get("require_contains", []):
            if required not in text:
                problems.append(f"{rel} lacks required text {required!r}")
    expected = "repo hygiene expectations hold"
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=expected,
        observed=problems or "ok",
    )


def _run_audit_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    from .audit import governance_timeline, verify_chain

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        run_dir = Path(d) / "run"
        log = EventLog(run_dir, echo=False)
        expect_kinds = scenario.get("expect_timeline_kinds", [])
        for kind in ("workflow_start", "consent_granted", "gate_verdict",
                     *expect_kinds, "workflow_done"):
            log.emit(kind, detail=f"eval-{kind}")
        log.close()
        if expect_kinds:
            rendered = {e["kind"] for e in governance_timeline(run_dir)}
            for kind in expect_kinds:
                if kind not in rendered:
                    problems.append(f"{kind} missing from governance timeline")
        before = verify_chain(run_dir)["ok"]
        if before != bool(scenario.get("expect_before", True)):
            problems.append(f"chain before tamper: ok={before}")
        if scenario.get("tamper"):
            path = run_dir / "events.jsonl"
            lines = path.read_text(encoding="utf-8").splitlines()
            rec = json.loads(lines[1])
            rec["detail"] = "history, tidied"
            lines[1] = json.dumps(rec, ensure_ascii=False)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            after = verify_chain(run_dir)["ok"]
            if after != bool(scenario.get("expect_after", False)):
                problems.append(f"chain after tamper: ok={after}")
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected={"before": scenario.get("expect_before", True),
                  "after": scenario.get("expect_after", False)},
        observed=problems or "ok",
    )


def _check_events_contain(scenario: dict[str, Any], run_dir: Path,
                          problems: list[str]) -> None:
    """Assert expected strings DID reach the events log (the positive twin of
    _check_events_absent): e.g. an injection_flag event proving the quarantine
    layer saw a gate-integrity canary rather than the halt merely coinciding."""
    needles = scenario.get("expect_events_contain") or []
    if not needles:
        return
    events_path = run_dir / "events.jsonl"
    raw = events_path.read_text(encoding="utf-8") if events_path.exists() else ""
    for needle in needles:
        if needle not in raw:
            problems.append(f"expected event content missing: {needle!r}")


def _run_workflow_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=int(scenario.get("max_attempts", 2)))
        statuses = _run_scripted_workflow(root, "evalrun", scenario.get("script", []),
                                          scenario.get("goal", "eval goal"))
        expected = scenario["expect_statuses"]
        if statuses != expected:
            problems.append(f"statuses={statuses}, expected {expected}")
        run_dir = root / "runs" / "evalrun"
        _check_events_contain(scenario, run_dir, problems)
        _check_events_absent(scenario, run_dir, problems)
    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected=scenario["expect_statuses"],
        observed=problems or statuses,
    )


def _run_resume_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=int(scenario.get("max_attempts", 2)))
        first = _run_scripted_workflow(root, "evalrun", scenario.get("first_script", []),
                                       scenario.get("goal", "eval goal"))
        second = _run_scripted_workflow(root, "evalrun", scenario.get("second_script", []),
                                        scenario.get("goal", "eval goal"))
    expected = {
        "first": scenario["expect_first_statuses"],
        "second": scenario["expect_second_statuses"],
    }
    observed = {"first": first, "second": second}
    return EvalCaseResult(
        id=scenario["id"],
        passed=observed == expected,
        expected=expected,
        observed=observed,
    )


def _run_canary_leak_scenario(scenario: dict[str, Any]) -> EvalCaseResult:
    """Boundary on, seeded canaries in the goal and scripted tool output. The
    canary strings (fake PII, fake secrets) must appear in NO run artifact:
    not events, journal, phase reports, workspace files, or the run tree at
    all. The strip map (which DOES hold PII values) lives outside the run
    tree by construction, so it is excluded from the sweep — that separation
    is the containment claim.
    """
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="harnessie-eval-") as d:
        root = Path(d)
        _scaffold_eval_project(root, max_attempts=int(scenario.get("max_attempts", 1)),
                               boundary=True)
        statuses = _run_scripted_workflow(root, "evalrun", scenario.get("script", []),
                                          scenario.get("goal", "eval goal"))
        expected = scenario.get("expect_statuses")
        if expected is not None and statuses != expected:
            problems.append(f"statuses={statuses}, expected {expected}")

        run_dir = root / "runs" / "evalrun"
        blob = ""
        for path in run_dir.rglob("*"):
            if path.is_file():
                blob += path.read_text(encoding="utf-8", errors="replace")
        # the workspace is the other place a leak could land
        ws = root / "workspace"
        for path in ws.rglob("*") if ws.exists() else []:
            if path.is_file():
                blob += path.read_text(encoding="utf-8", errors="replace")
        for canary in scenario.get("expect_absent", []):
            if canary in blob:
                problems.append(f"canary leaked into a run artifact: {canary[:12]}...")

        # the strip map is the ONE place PII values legitimately live, and it
        # must be outside the run tree
        boundary_dir = root / ".boundary"
        if scenario.get("expect_stripmap_outside_run") and boundary_dir.exists():
            if any(str(run_dir) in str(p) for p in boundary_dir.rglob("*")):
                problems.append("strip map is inside the run tree")

    return EvalCaseResult(
        id=scenario["id"],
        passed=not problems,
        expected="zero canary bytes in any run artifact",
        observed=problems or "ok",
    )


def _run_scripted_workflow(root: Path, run_id: str, script: list[dict[str, Any]],
                           goal: str, workflow: str = "eval.yaml",
                           approval_policy: Path | None = None) -> list[str]:
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False,
                            approval_policy=approval_policy)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=[_turn(t, i) for i, t in enumerate(script, 1)],
    )
    outcomes = runner.run_workflow(root / "workflows" / workflow, goal=goal)
    return [o.status for o in outcomes]


def _turn(spec: dict[str, Any], idx: int) -> AssistantTurn:
    if "tool" in spec:
        return AssistantTurn(
            content=spec.get("content", ""),
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(
                    id=spec.get("id", f"call_{idx}"),
                    name=spec["tool"],
                    arguments=spec.get("args", {}),
                )
            ],
        )
    return AssistantTurn(
        content=spec.get("content", ""),
        stop_reason=spec.get("stop_reason", "end_turn"),
        input_tokens=int(spec.get("input_tokens", 0)),
        output_tokens=int(spec.get("output_tokens", 0)),
    )


def _scaffold_eval_project(root: Path, max_attempts: int,
                           adversarial: bool = False,
                           triage: bool = False,
                           approve_expiry: bool = False,
                           parallel: bool = False,
                           boundary: bool = False) -> None:
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan and integrate.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo the task.")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\nJudge it.")
    (root / "config").mkdir()
    if boundary:
        (root / "config" / "boundary.yaml").write_text(
            "enabled: true\ninclude_contextual: false\n")
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
    (root / "workflows" / "eval.yaml").write_text(textwrap.dedent(f"""
        name: eval
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {{goal}}"
          - name: implement
            agent: implementer
            task: "Do this plan: {{plan}}"
            verify:
              max_attempts: {max_attempts}
              verifier: code-verifier
              criteria: artifact satisfies the plan
          - name: integrate
            agent: orchestrator
            task: "Summarize: {{implement}}"
    """))
    if adversarial:
        (root / "workflows" / "adv.yaml").write_text(textwrap.dedent("""
            name: adv
            phases:
              - name: decide
                mode: adversarial
                task: "Decide: {goal}"
                positions:
                  - { agent: implementer }
                  - { agent: implementer }
        """))
    if triage:
        approve_line = ("    approve_tools: [expire_fact]\n"
                        if approve_expiry else "")
        (root / "workflows" / "triage.yaml").write_text(
            'name: memory-triage\n'
            'phases:\n'
            '  - name: triage\n'
            '    agent: implementer\n'
            '    task: "Maintain project memory."\n'
            '    inject_memory_status: true\n'
            + approve_line +
            '    verify:\n'
            '      max_attempts: 1\n'
            '      memory_lint: true\n'
            '  - name: summary\n'
            '    agent: orchestrator\n'
            '    task: "Summarize: {triage}"\n')
    if parallel:
        (root / "workflows" / "parallel.yaml").write_text(textwrap.dedent("""
            name: parallel
            phases:
              - name: plan
                agent: orchestrator
                task: "Plan for goal: {goal}"
              - name: left
                parallel: workers
                agent: implementer
                task: "Write left out.txt from {plan}"
                verify:
                  max_attempts: 1
                  verifier: code-verifier
                  criteria: out.txt contains left
              - name: right
                parallel: workers
                agent: implementer
                task: "Write right out.txt from {plan}"
                verify:
                  max_attempts: 1
                  verifier: code-verifier
                  criteria: out.txt contains right
              - name: integrate
                agent: orchestrator
                task: "Summarize {left} and {right}"
        """))


def format_scorecard(scorecard: dict[str, Any]) -> str:
    lines = [f"eval scorecard: {scorecard['passed']}/{scorecard['total']} passed"]
    for result in scorecard["results"]:
        mark = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"{mark} {result['id']}: expected={json.dumps(result['expected'])} "
            f"observed={json.dumps(result['observed'])}")
        if result.get("notes") and not result["passed"]:
            lines.append(f"  {result['notes'][:500]}")
    return "\n".join(lines)
