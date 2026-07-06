# Next session handoff
## Current state
Harnessie is at v0.2.0 on `main` (uncommitted work in tree): the governance release. Adversarial collaboration and evals are now foundational principles, imported from Turnfile (consent, ownership lanes, authority order) and AIDR (positions/objections/arbitration, earned claims) as harness-enforced mechanics. Design: `GOVERNANCE.md`. Direction record: `decisions/AIDR-0001` — **status open, awaiting Sam's arbitration** (edit the Arbitration section in your own words, flip `status: arbitrated`, add `decided:`).
## What shipped in v0.2
- Consent contract: side-effecting tools locked until `accept_task`; `decline_task(reason, counter_proposal?)` is a first-class `declined` stop; gate re-offers once on a counter, never escalates on decline. Worker phases default `consent: true`.
- Ownership lanes: `OWNERSHIP.yaml` at project root (agent/collaborative/operator lanes + first-writer auto-claims), enforced in `write_file` dispatch; `request_change` records cross-lane needs. Honest limit documented: interpreter writes bypass the per-file check.
- Contested phases (`mode: adversarial`): independent read-only positions -> bounded objection rounds -> AIDR-shaped record under `runs/<id>/decisions/` -> convergence or `needs_arbitration`; human arbitrates by editing the record and resuming. `workflows/contested-decision.yaml` shipped.
- Hash-chained events log + `harnessie audit <run_id>` (exit 1 on broken chain).
- Eval kinds `ownership` / `adversarial` / `audit` + consent-flagged `loop`; `evals/governance.yaml` (12 scenarios, written red first).
## Verification status
- `python3 -m pytest -q`: 100 passed (3 sandbox tests skip on hosts where Seatbelt profiles cannot apply).
- `python3 -m harness.cli eval`: 21/21 passed (baseline + governance).
## Next 0.3 priorities (portability, displaced from old 0.2)
1. Linux sandbox backend (bubblewrap first) + parity tests.
2. Live-endpoint smoke tests incl. the governance scorecard per brain.
3. Live contested-phase run across two real providers (earn `independent-positions` on a real record).
4. Per-lane sandbox profiles are 1.0 material; do not start early.
## Non-goals for next session
- Do not weaken fail-closed behavior (unparseable stance = dissent; missing sandbox = blocked shell).
- Do not let any code path author an Arbitration section.
- Do not resolve AIDR-0001 on Sam's behalf.
## First commands for the next agent
- `git status --short --branch`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
- `node /Users/snap/Git/aidr/tools/aidr-lint.mjs decisions/`
