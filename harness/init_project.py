"""Project scaffold for installed Harnessie CLI usage."""

from __future__ import annotations

from pathlib import Path


FILES = {
    "agents/orchestrator.md": "# Role: Orchestrator\n\nPlan scoped tasks and integrate gated results.\n",
    "agents/workers/implementer.md": "# Role: Implementer\n\nExecute one scoped task and report evidence.\n",
    "agents/verifiers/code-verifier.md": (
        "# Role: Code verifier\n\n"
        "Verify artifacts against criteria. End with a JSON verdict object.\n"
    ),
    "config/models.yaml": """tiers:
  mid:
    provider: mock
    model_id: mock
routing:
  default: { tier: mid, effort: medium }
  plan: { tier: mid, effort: medium }
  implement: { tier: mid, effort: medium }
  verify: { tier: mid, effort: medium }
  integrate: { tier: mid, effort: medium }
budget:
  max_usd: 5.0
  max_tokens: 100000
""",
    "workflows/build-and-verify.yaml": """name: build-and-verify
phases:
  - name: plan
    agent: orchestrator
    task_class: plan
    task: "Plan for goal: {goal}"
  - name: implement
    agent: implementer
    task_class: implement
    task: "Implement this plan: {plan}"
    verify:
      max_attempts: 2
      verifier: code-verifier
      task_class: verify
      criteria: artifact satisfies the plan
  - name: integrate
    agent: orchestrator
    task_class: integrate
    task: "Summarize gated result: {implement}"
""",
    "evals/baseline.yaml": """name: baseline
scenarios:
  - id: verdict_json_passes
    kind: verdict
    report: '{"passed": true, "reasons": "checked"}'
    expect_passed: true
  - id: prose_pass_fails_closed
    kind: verdict
    report: "looks good, PASS"
    expect_passed: false
""",
    "memory/MEMORY.md": "# Project memory index\n",
    "OWNERSHIP.yaml": """# Ownership ledger — operator-owned; agents cannot reach this file.
# lanes: are declared by you and always win; files: are first-writer
# auto-claims maintained by the harness. Edit lanes to reassign ownership.
lanes:
  agent: {}
  collaborative: []
  operator: []
files: {}
""",
}


def init_project(root: Path, force: bool = False) -> list[Path]:
    written: list[Path] = []
    for rel, content in FILES.items():
        path = root / rel
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    (root / "workspace").mkdir(exist_ok=True)
    return written
