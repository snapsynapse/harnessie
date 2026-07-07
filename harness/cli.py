"""CLI entrypoint.

    harnessie run workflows/build-and-verify.yaml --goal "..."      run a workflow
    harnessie resume <run_id> workflows/build-and-verify.yaml       resume a crashed run
    harnessie report <run_id>                                       human-readable run report
    harnessie audit <run_id>                                        verify hash chain + governance timeline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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

    p_resume = sub.add_parser("resume", help="resume a run from its journal")
    p_resume.add_argument("run_id")
    p_resume.add_argument("workflow")
    p_resume.add_argument("--goal", default="")
    p_resume.add_argument("--approval-policy", help="headless approval policy YAML")
    p_resume.add_argument("--approve-interactive", action="store_true",
                          help="prompt on TTY for approval-gated tools")

    p_report = sub.add_parser("report", help="print a run's journal and proofs")
    p_report.add_argument("run_id")

    p_audit = sub.add_parser(
        "audit", help="verify a run's event hash chain and print its governance timeline")
    p_audit.add_argument("run_id")

    p_eval = sub.add_parser("eval", help="run deterministic eval scorecards")
    p_eval.add_argument("suite", nargs="?", help="optional eval suite YAML path")
    p_eval.add_argument("--live", action="store_true",
                        help="run opt-in live provider scorecards")

    p_manifest = sub.add_parser(
        "verify-manifest", help="verify the trust-bundle MANIFEST integrity")
    p_manifest.add_argument("manifest", nargs="?", default="docs/MANIFEST.yaml")

    p_init = sub.add_parser("init", help="create a minimal Harnessie project layout")
    p_init.add_argument("path", nargs="?", default=".", help="target directory")
    p_init.add_argument("--force", action="store_true",
                        help="overwrite existing scaffold files")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "report":
        run_dir = root / "runs" / args.run_id
        journal = run_dir / "journal.jsonl"
        if not journal.exists():
            print(f"no journal at {journal}", file=sys.stderr)
            return 1
        print("journal (phase results, resume ledger):")
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
        print(format_scorecard(scorecard))
        return 0 if scorecard["passed"] == scorecard["total"] else 2

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

    if args.cmd == "init":
        from .init_project import init_project

        target = (root / args.path).resolve()
        written = init_project(target, force=args.force)
        print(f"initialized Harnessie project at {target}")
        print(f"wrote {len(written)} file(s)")
        return 0

    from .runner import WorkflowRunner  # deferred: import cost + optional deps

    run_id = args.run_id if args.cmd == "resume" else None
    approval_policy = (root / args.approval_policy).resolve() \
        if getattr(args, "approval_policy", None) else None
    runner = WorkflowRunner(project_root=root, run_id=run_id,
                            approval_policy=approval_policy,
                            interactive_approvals=bool(
                                getattr(args, "approve_interactive", False)))
    outcomes = runner.run_workflow(root / args.workflow, goal=args.goal)
    print(f"\nrun {runner.run_id}: spent ${runner.budget.spent_usd:.4f}, "
          f"{runner.budget.spent_tokens} tokens")
    worst = 0
    for o in outcomes:
        print(f"  [{o.status:>14}] {o.phase}: "
              f"${o.spent_usd:.6f}, {o.spent_tokens} tokens; {o.report[:120]}")
        if o.status == "needs_human":
            worst = 2
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
