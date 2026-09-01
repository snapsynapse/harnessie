"""CLI entrypoint.

    harnessie run workflows/build-and-verify.yaml --goal "..."      run a workflow
    harnessie resume <run_id> workflows/build-and-verify.yaml       resume a crashed run
    harnessie report <run_id>                                       human-readable run report
    harnessie audit <run_id>                                        verify hash chain + governance timeline
    harnessie ownership <path> --agent <name>                       explain write authority
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


def _print_raw_report(run_dir: Path) -> None:
    """Developer view: the raw journal, selected events, and proof filenames.
    Kept behind `report --raw`; the default report is the plain-language one."""
    journal = run_dir / "journal.jsonl"
    if journal.exists():
        print("\njournal (phase results, resume ledger):")
        for line in journal.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            print(f"{rec.get('kind'):>14}  "
                  f"{json.dumps({k: v for k, v in rec.items() if k not in ('ts', 'kind')}, default=str)[:200]}")
    events = run_dir / "events.jsonl"
    if events.exists():
        print("\nevents (routes, gate verdicts, costs):")
        wanted = {"role_start", "gate_verdict", "check", "phase_done", "workflow_done"}
        for line in events.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("kind") in wanted:
                print(f"{rec.get('kind'):>14}  "
                      f"{json.dumps({k: v for k, v in rec.items() if k not in ('ts', 'kind')}, default=str)[:200]}")
    proofs = run_dir / "proofs"
    if proofs.exists():
        print("\nproofs:")
        for p in sorted(proofs.iterdir()):
            print(f"  {p.name}")


def _ownership_relative_path(root: Path, raw: str) -> str:
    """Resolve a CLI path exactly as a workspace-relative write target."""
    if not raw or raw != raw.strip() or "\\" in raw \
            or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise ValueError("PATH must be a non-empty relative POSIX workspace path")
    workspace = (root / "workspace").resolve()
    target = (workspace / raw).resolve()
    if target == workspace or not target.is_relative_to(workspace):
        raise ValueError("PATH must name a file or directory inside workspace/")
    return target.relative_to(workspace).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harnessie")
    parser.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run a workflow")
    p_run.add_argument("workflow")
    p_run.add_argument("--goal", default="", help="top-level goal passed to the workflow")
    p_run.add_argument("--approval-policy", help="headless approval policy YAML")
    p_run.add_argument("--approve-interactive", action="store_true",
                       help="prompt on TTY for approval-gated tools")
    p_run.add_argument("--plugin", action="append", default=[], metavar="NAME",
                       help="admit an installed harnessie.tools.v1 plugin (repeatable)")

    p_resume = sub.add_parser("resume", help="resume a run from its journal")
    p_resume.add_argument("run_id")
    p_resume.add_argument("workflow")
    p_resume.add_argument("--goal", default="")
    p_resume.add_argument("--approval-policy", help="headless approval policy YAML")
    p_resume.add_argument("--approve-interactive", action="store_true",
                          help="prompt on TTY for approval-gated tools")
    p_resume.add_argument("--plugin", action="append", default=[], metavar="NAME",
                          help="readmit the original harnessie.tools.v1 plugin (repeatable)")

    p_report = sub.add_parser(
        "report", help="plain-language summary of a run and its next action")
    p_report.add_argument("run_id")
    p_report.add_argument("--raw", action="store_true",
                          help="also print the raw journal, events, and proofs")

    p_audit = sub.add_parser(
        "audit", help="verify a run's event hash chain and print its governance timeline")
    p_audit.add_argument("run_id")

    p_eval = sub.add_parser("eval", help="run deterministic eval scorecards")
    p_eval.add_argument("suite", nargs="?", help="optional eval suite YAML path")
    p_eval.add_argument("--live", action="store_true",
                        help="run opt-in live provider scorecards")

    p_validate = sub.add_parser(
        "validate", help="validate configuration and workflows without starting a run")
    p_validate.add_argument(
        "paths", nargs="*", help="optional documents (default: project authoring surfaces)")
    p_validate.add_argument(
        "--kind", choices=("models", "cascade", "boundary", "approval-policy",
                            "ownership", "workflow"),
        help="schema kind for one explicitly named document")

    p_ownership = sub.add_parser(
        "ownership", help="explain whether an agent may write a workspace path")
    p_ownership.add_argument("path", metavar="PATH",
                             help="path relative to workspace/")
    p_ownership.add_argument("--agent", required=True,
                             help="agent identity to evaluate")
    p_ownership.add_argument("--json", action="store_true", dest="json_output",
                             help="emit the decision as JSON")

    p_manifest = sub.add_parser(
        "verify-manifest", help="verify the trust-bundle MANIFEST integrity")
    p_manifest.add_argument("manifest", nargs="?", default="docs/MANIFEST.yaml")

    p_inward = sub.add_parser(
        "verify-inward-manifest",
        help="verify role prompts and shipped configuration against the inward manifest")
    p_inward.add_argument(
        "manifest", nargs="?", default="INWARD_MANIFEST.yaml")

    p_maiden = sub.add_parser(
        "approve-maiden",
        help="approve and promote one verified maiden-voyage proposal")
    p_maiden.add_argument("run_id")
    p_maiden.add_argument("phase")

    p_verify = sub.add_parser(
        "verify", help="standalone verification of a workspace against a "
                       "claims file (exit 0 verified / 1 failed / 2 cannot verify)")
    p_verify.add_argument("--workspace", required=True,
                          help="directory holding the artifacts to verify")
    verify_source = p_verify.add_mutually_exclusive_group(required=True)
    verify_source.add_argument(
        "--criteria", help="markdown file of acceptance criteria / claims")
    verify_source.add_argument(
        "--evidence-bundle",
        help="v1 evidence bundle containing claims and content-addressed proofs")
    p_verify.add_argument(
        "--evidence-root",
        help="directory containing files referenced by the evidence bundle")
    p_verify.add_argument("--check", action="append", default=[],
                          metavar="CMD",
                          help="deterministic check command (repeatable); "
                               "runs sandboxed in the workspace, exit 0 = pass")
    p_verify.add_argument("--report-dir",
                          help="where the report and proofs land "
                               "(default: ./verify-reports/<timestamp>)")
    p_verify.add_argument("--models",
                          help="models.yaml for the verifier brain "
                               "(default: ./config/models.yaml)")
    p_verify.add_argument("--tier", default="",
                          help="route the verifier to this tier explicitly")
    p_verify.add_argument("--verifier-prompt",
                          help="override the built-in verifier prompt file")
    p_verify.add_argument("--no-verifier", action="store_true",
                          help="deterministic checks only, no verifier agent")
    p_verify.add_argument("--allow-network", action="store_true",
                          help="let check commands use the network (checks are "
                               "network-denied by default; the verifier agent "
                               "stays denied regardless)")
    p_verify.add_argument("--max-steps", type=int, default=20)

    p_init = sub.add_parser("init", help="scaffold a project and run a guided first run")
    p_init.add_argument("path", nargs="?", default=".", help="target directory")
    p_init.add_argument("--force", action="store_true",
                        help="overwrite existing scaffold files")
    p_init.add_argument("--no-verify", action="store_true",
                        help="skip the guided readiness check and zero-dollar mock run")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "ownership":
        from .ownership import OwnershipLedger
        from .schema import ConfigurationError

        try:
            if not args.agent or args.agent != args.agent.strip() \
                    or any(ord(char) < 32 or ord(char) == 127
                           for char in args.agent):
                raise ValueError("AGENT must be a non-empty identity without surrounding whitespace")
            rel = _ownership_relative_path(root, args.path)
            decision = OwnershipLedger.load(
                root / "OWNERSHIP.yaml").explain_write(args.agent, rel)
        except (ConfigurationError, ValueError) as exc:
            print(f"ownership inspection failed: {exc}", file=sys.stderr)
            return 2
        if args.json_output:
            print(json.dumps(
                {"schema_version": 1, **asdict(decision)}, sort_keys=True))
            return 0
        print(f"ownership: {'ALLOWED' if decision.allowed else 'DENIED'}")
        print(f"agent: {decision.agent}")
        print(f"path: {decision.path}")
        print(f"source: {decision.source}")
        if decision.owner is not None:
            print(f"owner: {decision.owner}")
        if decision.pattern is not None:
            print(f"pattern: {decision.pattern}")
        print(f"reason: {decision.reason}")
        if decision.remedy is not None:
            print(f"remedy: {decision.remedy}")
        return 0

    if args.cmd == "validate":
        from .schema import (ConfigurationError, ValidationReport, format_report,
                             read_document, validate_project)

        if args.kind:
            if len(args.paths) != 1:
                print("validate --kind requires exactly one path", file=sys.stderr)
                return 2
            path = Path(args.paths[0])
            path = path if path.is_absolute() else root / path
            try:
                read_document(path, args.kind)
                report = ValidationReport(documents=1)
            except ConfigurationError as exc:
                report = ValidationReport(problems=exc.problems)
        else:
            report = validate_project(root, [Path(path) for path in args.paths])
        print(format_report(report), file=sys.stdout if report.ok else sys.stderr)
        return 0 if report.ok else 2

    if args.cmd == "report":
        from .explain import format_report

        run_dir = root / "runs" / args.run_id
        if not (run_dir / "events.jsonl").exists() and not (run_dir / "journal.jsonl").exists():
            print(f"no run found at {run_dir}", file=sys.stderr)
            return 1
        print(format_report(run_dir))
        if getattr(args, "raw", False):
            _print_raw_report(run_dir)
        return 0

    if args.cmd == "audit":
        from .adversarial import lint_record
        from .audit import format_audit, governance_timeline, verify_chain

        run_dir = root / "runs" / args.run_id
        if not (run_dir / "events.jsonl").exists():
            print(f"no events log at {run_dir / 'events.jsonl'}", file=sys.stderr)
            return 2
        chain = verify_chain(run_dir)
        decisions = []
        ddir = run_dir / "decisions"
        if ddir.exists():
            for rec in sorted(ddir.glob("*.md")):
                lint = lint_record(rec.read_text(encoding="utf-8"))
                decisions.append({"path": rec.name, "status": lint["status"],
                                  "claims": lint["claims"]})
        print(format_audit(args.run_id, chain, governance_timeline(run_dir),
                           decisions))
        return 0 if chain["ok"] else 1

    if args.cmd == "eval":
        if args.live:
            from .live_scorecard import format_live_scorecard, run_live_scorecard

            scorecard = run_live_scorecard(root)
            print(format_live_scorecard(scorecard))
            return 0 if scorecard["passed"] == scorecard["total"] else 2

        from .evals import format_scorecard, run_eval_suite

        suite = (root / args.suite).resolve() if args.suite else None
        scorecard = run_eval_suite(root, suite_path=suite)
        if scorecard["total"] == 0:
            location = str(suite) if suite is not None else str(root / "evals")
            print(
                f"no eval suites found at {location}; refusing a vacuous pass",
                file=sys.stderr,
            )
            return 2
        print(format_scorecard(scorecard))
        return 0 if scorecard["passed"] == scorecard["total"] else 2

    if args.cmd == "verify":
        from .verify import Check
        from .verify_standalone import VerifyRequest, run_standalone_verify

        checks = [Check(name=f"check-{i}", command=cmd)
                  for i, cmd in enumerate(args.check, start=1)]
        outcome = run_standalone_verify(VerifyRequest(
            workspace=Path(args.workspace),
            criteria_path=Path(args.criteria) if args.criteria else None,
            checks=checks,
            report_dir=Path(args.report_dir) if args.report_dir else None,
            models_path=Path(args.models) if args.models else None,
            tier=args.tier,
            verifier_prompt_path=(Path(args.verifier_prompt)
                                  if args.verifier_prompt else None),
            no_verifier=args.no_verifier,
            allow_network=args.allow_network,
            max_steps=args.max_steps,
            evidence_bundle_path=(Path(args.evidence_bundle)
                                  if args.evidence_bundle else None),
            evidence_root=(Path(args.evidence_root)
                           if args.evidence_root else None)))
        print(outcome.summary, file=sys.stderr if outcome.exit_code else sys.stdout)
        return outcome.exit_code

    if args.cmd == "verify-manifest":
        from .trust_manifest import verify_manifest

        result = verify_manifest(root, (root / args.manifest).resolve())
        if result.ok:
            print(f"trust manifest OK: {len(result.files)} file(s)")
            return 0
        print("trust manifest FAILED", file=sys.stderr)
        for problem in result.problems:
            print(f"- {problem}", file=sys.stderr)
        return 2

    if args.cmd == "verify-inward-manifest":
        from .inward_manifest import verify_inward_manifest

        result = verify_inward_manifest(
            root, (root / args.manifest).resolve())
        if result.ok:
            print(f"inward manifest OK: {len(result.files)} file(s)")
            return 0
        print("inward manifest FAILED", file=sys.stderr)
        for problem in result.problems:
            print(f"- {problem}", file=sys.stderr)
        return 2

    if args.cmd == "approve-maiden":
        from .maiden import approve_maiden

        result = approve_maiden(root, args.run_id, args.phase)
        print(result.message, file=sys.stdout if result.ok else sys.stderr)
        if result.ok:
            print("resume the original run with the same workflow and goal")
            return 0
        return 2

    if args.cmd == "init":
        from .init_project import init_project

        target = (root / args.path).resolve()
        written = init_project(target, force=args.force)
        print(f"initialized Harnessie project at {target}")
        print(f"wrote {len(written)} file(s)")
        if args.no_verify:
            return 0
        from .firstrun import guided_first_run

        ready, report = guided_first_run(target)
        print(report)
        return 0 if ready else 1

    from .runner import WorkflowRunner, load_models_config  # deferred: import cost
    from .preflight import build_preview, format_preview

    # Cost preview and the ceiling-less-live-run refusal run BEFORE any run
    # state is created or any brain is built, so a refused run leaves no trace
    # and bills nothing.
    tiers, _routing, budget_cfg, _fallbacks = load_models_config(root / "config" / "models.yaml")
    preview = build_preview(tiers, budget_cfg)
    print(format_preview(preview))
    if preview.refuse_reason is not None:
        print(preview.refuse_reason, file=sys.stderr)
        return 2

    from .plugins import PluginError, resolve_plugins
    try:
        plugins = resolve_plugins(getattr(args, "plugin", []))
    except PluginError as exc:
        print(f"plugin admission refused: {exc}", file=sys.stderr)
        return 2

    run_id = args.run_id if args.cmd == "resume" else None
    approval_policy = (root / args.approval_policy).resolve() \
        if getattr(args, "approval_policy", None) else None
    try:
        runner = WorkflowRunner(
            project_root=root, run_id=run_id,
            approval_policy=approval_policy,
            interactive_approvals=bool(
                getattr(args, "approve_interactive", False)),
            plugins=plugins,
        )
    except PluginError as exc:
        print(f"plugin admission refused: {exc}", file=sys.stderr)
        return 2
    from .explain import HALT_STATUSES, format_run_summary

    outcomes = runner.run_workflow(root / args.workflow, goal=args.goal)
    print()
    print(format_run_summary(
        runner.run_id, args.workflow,
        [(o.phase, o.status) for o in outcomes],
        runner.budget.spent_usd, runner.budget.spent_tokens))
    return 2 if any(o.status in HALT_STATUSES for o in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
