"""CLI entrypoint.

    harnessie run workflows/build-and-verify.yaml --goal "..."      run a workflow
    harnessie resume <run_id> workflows/build-and-verify.yaml       resume a crashed run
    harnessie report <run_id>                                       human-readable run report
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

    p_resume = sub.add_parser("resume", help="resume a run from its journal")
    p_resume.add_argument("run_id")
    p_resume.add_argument("workflow")
    p_resume.add_argument("--goal", default="")

    p_report = sub.add_parser("report", help="print a run's journal and proofs")
    p_report.add_argument("run_id")

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

    from .runner import WorkflowRunner  # deferred: import cost + optional deps

    run_id = args.run_id if args.cmd == "resume" else None
    runner = WorkflowRunner(project_root=root, run_id=run_id)
    outcomes = runner.run_workflow(root / args.workflow, goal=args.goal)
    print(f"\nrun {runner.run_id}: spent ${runner.budget.spent_usd:.4f}, "
          f"{runner.budget.spent_tokens} tokens")
    worst = 0
    for o in outcomes:
        print(f"  [{o.status:>14}] {o.phase}: {o.report[:120]}")
        if o.status == "needs_human":
            worst = 2
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
