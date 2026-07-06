# Example: policy analysis and compliance assessment

End-to-end demonstration of orchestrator + worker + verifier, effort routing, memory, and proof artifacts.

## Setup

```bash
mkdir -p workspace/policies
cp examples/policy-compliance/acme-ai-usage-policy.md workspace/policies/
cp examples/policy-compliance/obligations.md workspace/
export ANTHROPIC_API_KEY=...   # or point tiers at your local endpoint in config/models.yaml
```

## Run

```bash
python3 -m harness.cli run workflows/policy-compliance.yaml \
  --goal "Assess ACME's AI usage policy in policies/ against the obligations in obligations.md"
```

Paths in the goal are relative to the workspace root, which is how the agents' tools see them.

## What happens

1. `plan` (orchestrator, frontier tier, high effort): reads the documents, emits an assessment plan with per-obligation acceptance criteria and the required findings structure.
2. `assess` (researcher worker, cheap tier, low effort): writes `workspace/assessment/findings.md`, one finding per obligation with verdict and quoted provenance. The gate then runs the deterministic check (findings file exists and is non-trivial) and the `claims-verifier` (mid tier, high effort), which spot-checks quotes against the source documents and fails the phase on any fabricated citation. Failures reformulate the task with the verifier's evidence and escalate effort, then tier.
3. `integrate` (orchestrator, frontier, high effort): executive summary, posture, top risks, no-evidence gaps for human follow-up.

## Expected findings on the sample data

Obligations 4, 5, 6 are clearly evidenced (vendor review, training, incident path). Obligation 1 is partially met (catalog entries name owner and purposes, but only for tools, not all AI systems). Obligations 2 and 3 should come back not-met / no-evidence, the sample policy says nothing about human oversight of high-risk use or lawful basis for training data. A run that reports all six as "met" is a failed run; the claims-verifier exists to catch exactly that.

## Where the evidence lands

- `runs/<run_id>/journal.jsonl`: phase results (the resume ledger)
- `runs/<run_id>/events.jsonl`: routes, gate verdicts, checks, costs (the audit trail)
- `runs/<run_id>/proofs/`: check outputs per attempt
- `workspace/assessment/findings.md`: the assessed deliverable
- `memory/`: save durable lessons afterwards via `ProjectMemory.save_fact`
