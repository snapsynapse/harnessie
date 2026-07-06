# Next session handoff
## Current state
Harnessie is at v0.3.0 on `main`. v0.2.0 (governance layer) is committed as `c6f4e56`; the v0.3.0 aggregated-intelligence release is built and verified but **uncommitted** pending operator review. Two direction records await Sam's arbitration: `decisions/AIDR-0001` (v0.2 governance layer) and `decisions/AIDR-0002` (v0.3 tenets + triage). Arbitrate by editing each record's Arbitration section in your own words, flipping `status: arbitrated`, adding `decided:`.
## What shipped in v0.3
- Operator in the audit stream: `approval_granted`/`approval_denied` events with source, `operator_action` on arbitration-detected resume, `approve_tools:` phase key as recorded per-phase pre-approval (restored to default-deny after the phase).
- Memory as substrate: facts carry stamped provenance (run + agent — agent-claimed sources ignored) plus `verified`/`verify_by` dates; `stale_facts()`, `archive_fact()` (archival-only, never delete), `lint()`.
- Tools `save_fact` / `expire_fact` (expire requires approval, fail closed headless); `inject_memory_status:` harness-prepared digest; `memory_lint:` in-process gate check.
- `workflows/memory-triage.yaml` — the maintenance-agent pattern under enforcement, routed to the local tier; cadence via cron/launchd.
- Eval kind `triage` + `evals/triage.yaml`, red-first.
## Verification status
- `python3 -m pytest -q`: 114 passed (3 sandbox tests skip on hosts where Seatbelt profiles cannot apply).
- `python3 -m harness.cli eval`: 24/24 passed (baseline + governance + triage).
- `node <aidr>/tools/aidr-lint.mjs decisions/`: both records PASS.
## Next 0.4 priorities (portability — displaced twice; a THIRD displacement should be declined absent operator arbitration)
1. Linux sandbox backend (bubblewrap first) + confinement-parity tests.
2. Live-endpoint smoke tests incl. governance + triage scorecards per brain.
3. Live contested-phase run across two real providers (earn `independent-positions` on a real record).
## Non-goals for next session
- Do not weaken fail-closed behavior anywhere.
- Do not let any code path author an Arbitration section or delete a memory fact.
- Do not resolve AIDR-0001/0002 on Sam's behalf.
- Do not stage `.agents/` or `.codex/`.
## First commands for the next agent
- `git status --short --branch`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
