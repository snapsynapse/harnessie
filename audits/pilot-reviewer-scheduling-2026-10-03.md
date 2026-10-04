# Pilot reviewer scheduling repair

Date: 2026-10-03 (America/Denver)
Scope: approved offline scheduling repair only
Baseline: a42712b
Status: implemented and independently verified; no live execution authority

## Problem and correction

The October 3 v5 attempt spent all four stage calls requesting evidence and stopped without a position. Its final tool results never reached a synthesis turn. The earlier scripted rehearsal demonstrated a feasible schedule but did not communicate that schedule to the live reviewer.

The sealed reviewer instructions now describe the default four-call schedule: read the index, batch source reads across the next two calls, then submit the position or objection through task_complete on the final call. The pilot wrapper supplies a fresh stage-budget notice on each request, derived from the ledger's actual stage limit and consumed calls. The notice is added to that request without accumulating in the transcript. Lower stage limits require earlier batching; missing evidence must remain unknown.

This is reviewer guidance, not a new enforcement guarantee. A reviewer can still spend its final call reading. Existing runner and ledger limits then stop the incomplete stage without advancing or exporting. No public runtime, provider schema, authentication contract, resource ceiling, evidence allowlist or automatic retry policy changed.

## Verification

- The new workload test failed before implementation and passed after correction.
- Worker focused suite: 36 passed.
- Worker broader pilot suite: 199 passed, 2 transport timing failures. The output-overflow fixture returned process_timeout, and the orphan-child fixture did not create its PID file before timeout. Both reproduced in the worker's individual reruns; neither test nor transport implementation was changed.
- Independent verifier full offline pilot suite: 201 passed. The two timing failures did not recur in that run; this does not establish that their underlying instability is resolved.
- Independent workload and integration suite: 7 passed.
- Final synthesis-request assertions verify the complete contents of all 17 sources across all four stages through both real adapter encoders with injected synthetic responses.
- Noncompliant-reader regression tests cover three- and four-call limits: incomplete outcome, halted ledger, no Qwen calls and no export. The independent verifier additionally exercised the same checks directly at one- and two-call limits.
- The full-evidence rehearsal retains zero next-live allowance and reaches needs_arbitration with synthetic reports.
- Independent diff review found no actionable issues; git diff --check passed.

The independent full-suite command was:

Literal
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pilot*.py
```

## Limits and next gate

These tests establish prompt delivery, evidence availability, encoded-request fit, completion mechanics and fail-closed exhaustion. They do not establish live reviewer compliance, review quality, provider usage or billing behavior. No live provider calls, account checks, new execution candidate, consumed-run edits, commit, push, release or deployment were performed for this repair.

Preparing a fresh sealed execution candidate remains a separate next step. Existing consumed approvals cannot be reused, and a future live attempt requires fresh identity and allowance evidence plus explicit approval.
