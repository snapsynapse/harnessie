# Capability program readiness

Date: 2026-09-09. Source revision: `f1e17139cb23bee69b4d9d5a315d1ef839ee524c`. Scope: current-source architecture and test assessment, not implementation or live-provider evidence.

## Decision

Harnessie is ready to begin the bidding, commentary, follow, runner-observation and model-selection capability program as sequential tranches. It is not ready to implement those capabilities as one batch. The first implementation-ready slice is automatic deterministic runner observation. Bid record, commentary and follow mode each need a bounded design or guard tranche first. Bid-driven selection remains evidence-blocked until earlier slices produce calibrated outcomes and a separate human decision.

The [live controlled-review pilot packet](controlled-review-pilot-2026-09-09.md) is the approved next active tranche. It exercises the shipped governed-review and open-record export path before runtime expansion.

## Current evidence

- Stable core 1.4.1, the offline observer and open-record AIDR exporter are published and verified.
- Exact-main CI, package gates, CodeQL, Scorecard and Pages passed at the assessed revision.
- The targeted AIDR-0009 suite currently reports 13 passed and 28 strict expected failures. The expected failures are executable contracts for unimplemented slices, not failing shipped behavior.
- `harness/observer.py` is deterministic, verifies the event chain, preserves source bytes, minimizes raw payloads and writes outside agent workspaces.
- `tests/test_aidr_0009_guards.py` proves that workflows without opt-in emit no bid or observer artifacts and that observer output does not join the governance timeline.
- There is no `harness/bidding.py`; follow mode has no red-first contract yet.

## Feature readiness

| Capability | Readiness | Required next boundary |
|---|---|---|
| Automatic deterministic runner observation | READY TO IMPLEMENT | Strengthen the unique context-exclusion sentinel, cover completion and every halt path, add opt-in `run` and `resume` controls, and report observer failure without changing the underlying run result. |
| Bid `record` mode | READY TO DESIGN | Decide pre-egress candidate filtering, a true per-round budget, worker-budget reservation, partial-round outcomes and fallback versus refusal. Add those red tests before implementing the existing parser, event and unchanged-routing contracts. |
| Model commentary | READY TO DESIGN | Decide fourth-role versus dedicated no-tool invocation, add a threat-model row, and prove no tools, no feedback to agent context, memory or governance, and safe handling of directive-bearing cited prose. |
| Follow mode | READY TO DESIGN | Specify verified-prefix parsing, partial-line handling, truncation and chain-change refusal, polling and interruption, terminal events, resource bounds and artifact consistency. Add a deterministic concurrent-writer contract before code. |
| Bid-driven model selection | BLOCKED ON EVIDENCE | Accumulate record-mode outcomes, run the frozen calibration corpus and scorecard, set measured thresholds and minimum sample size, then submit `select` under its own AIDR and human arbitration. |

Static routing through `config/models.yaml` remains shipped. The blocked item is automatic `bid.mode: select`, not ordinary operator-configured model choice.

## Active sequence

1. Run the controlled-review pilot with frozen evidence, explicit provider permission and human arbitration.
2. Implement automatic deterministic runner observation as an opt-in, model-free slice.
3. Settle the bid-record budget and exposure policies, complete red contracts, then implement record mode without changing dispatch.
4. Run the live bid scorecard against a frozen corpus and add propose-only reporting.
5. Settle and implement manual opt-in model commentary with its threat and context-exclusion controls.
6. Build deterministic follow mode, then combine already-proven observation surfaces deliberately.
7. Consider automatic bid-driven selection only after measured calibration and a separate human decision.

This sequence turns the prior deferral into active dependencies. It does not rewrite the historical AIDR-0009 observer-only arbitration or authorize later slices without their named gates.
