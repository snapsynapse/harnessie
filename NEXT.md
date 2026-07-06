# Next session handoff
## Current state
Harnessie is at v0.3.1 on `main` — a fix-first coherence patch (stance-vocabulary blocker, NEXT.md relocation, audit-timeline defect, doc-drift sweep) following an adversarially verified impact sweep. Working tree clean except a PARKED, deliberately uncommitted diff: `handoffs/parked-governance-s7-tenets-realignment.patch` (GOVERNANCE.md §7 realigned to a privately maintained tenets draft, ratification pending). It stays parked until the operator decides.
## Holding pattern
An operator decision packet with six open items (two AIDR arbitrations, tenets ratification, repo-standards tier, one adoption row, scrub timing) was delivered out-of-band; each item carries a default-on-silence. **Harnessie feature work holds until the packet returns.** Executed fix-first commits are listed in the packet for retroactive veto.
## Verification status
- `python3 -m pytest -q`: 115 passed.
- `python3 -m harness.cli eval`: 25/25 across baseline, governance, triage.
- AIDR lint: both records in `decisions/` PASS.
## Gated next steps (in packet order)
1. If approved: v0.3.2 low-cost adoptions — structured refusal grammar (`{error, boundary, detail, why}`) across the 16 enumerated denial sites with atomic per-surface migration + red-first refusal scenarios; human-readable IDs (check-digit alphabet) for run/record/change-request refs, keeping the timestamp run-id prefix. 1-day hard cap; overflow drops to backlog, never to 0.4.
2. 0.4 = portability, undiluted (Linux sandbox backend + parity tests; live-endpoint scorecards incl. governance + triage suites; live contested-phase run across two real providers), with trust-bundle MANIFEST integrity as its companion.
3. Post-0.4: triage-label profile, dogfooded by pointer to its canonical concept note (re-review the note first; its own review date is 2026-08-05).
## Non-goals (standing)
- No public promotion work; no treating unratified tenets as canon; no gated third-party names on any surface.
- No `run_shell` ok-semantics flip, no decision-record filename randomization, no replacing the timestamp run-id prefix.
- Do not resolve the operator's open decisions on their behalf; do not commit the parked §7 diff without instruction.
## First commands for the next agent
- `git status --short --branch && git log --oneline -6`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
