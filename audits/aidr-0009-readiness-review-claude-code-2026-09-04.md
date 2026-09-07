# AIDR-0009 readiness review - Claude Code engine

Date: 2026-09-04
Reviewed base: `feature/bidding-and-observer` at committed HEAD `b3efeca`
Scope: one of four independent engine reviews (Claude Code, Codex, Google Antigravity, Qwen 3.8) assessing whether AIDR-0009 (bid rounds and a run observer) is ready for human arbitration. Read-only analysis; no repository changes were made while producing the review. This document was written after the review at explicit operator request, as a separate act from the review itself.

Lane: independent AIDR decision reviewer. Answers the seven questions in [AIDR-0009-design-draft.md](../decisions/AIDR-0009-design-draft.md) Part 5, identifies objections, and recommends arbitration boundaries. Does not treat its own recommendation as authority; does not edit [AIDR-0009-bid-rounds-and-run-observer.md](../decisions/AIDR-0009-bid-rounds-and-run-observer.md) Positions, Objections, or Arbitration sections.

## Recommendation

Conditional. Sequencing steps 1-2 in the design draft (Part 3: deterministic observer layer, bid `record` mode) are well-bounded by existing guard tests and ready to authorize. The AIDR as posed asks for approval of a six-step plan whose later gates (`select`'s calibration threshold, the fourth role kind for commentary) are deliberately left as empirical unknowns pending scorecard evidence that does not yet exist. A single up-or-down arbitration on the full scope would either rubber-stamp undetermined numbers or block a safe first slice; recommend arbitration scope be split accordingly.

## AIDR readiness

- Ready for arbitration as a single whole-scope question: no.
- Ready for arbitration as a question scoped to Part 3 steps 1-2 only: yes.
- Missing evidence or decisions:
  - Only one independent position is on record (Claude Fable 5, recommend, written before any objection existed); no objections have been filed against it.
  - The Part 4 hand-run probe (five packets, three configured brains, no code) that would validate the "zero resolvable citations voids the bid" severity for small models has not been run or recorded.
  - No test currently proves that bid state, once `harness/bidding.py` exists, cannot be read by `harness/routing.py`'s decision function. The "routing table still decides" claim is asserted in the design draft, not yet falsifiable by a specific test.
  - The calibration sample threshold N ("set by the scorecard's variance," 1.7) has no interim value or method a reviewer can check today.
- Questions Sam must arbitrate:
  - Authorize Part 3 steps 1-2 now, or require a broader position/objection round across all six steps first?
  - Should "record/propose instrument invariant 6, they do not violate it" be affirmed as explicit AIDR text, citable by future contributors, rather than left implicit in the design draft?
  - Should "the observer never holds authority" be promoted from this AIDR into INTENT's invariant list, given how load-bearing it already is (two guard tests in `tests/test_aidr_0009_guards.py` already depend on it)?
  - Is the fourth role kind (`observer`, for optional commentary, design 2.5) approved in principle now, or deferred to its own decision when sequencing reaches step 5?
  - Accept "observe, don't refuse" for provider-correlated bids through `record`/`propose` (design 1.9), on the condition it is revisited with evidence before `select` is considered?

## Findings

1. `tests/test_aidr_0009_guards.py` already proves two of the AIDR's central safety claims today, not just in design prose: a workflow without a `bid:` key emits no bid or observer events (byte-identical to 1.2 behavior), and observer output kinds (`observation`, `narration`) never join `GOVERNANCE_KINDS`.
2. The falsifier suite is genuinely red-first: 37 tests across `tests/test_bidding.py` and `tests/test_observer.py` are `xfail(strict=True)`, so an accidental first pass fails the whole suite until the marker is deliberately removed - a correctly built forcing function under invariant 11.
3. The design intentionally leaves several numeric gates undetermined (calibration sample threshold N, whether `confidence` ever enters ranking, the cross-brain pre-mortem variant) pending scorecard evidence (design 1.8). Appropriate for `select`, but means "adopt as drafted" cannot mean the final thresholds are approved today; the AIDR text should say it approves a process for empirical gating, not fixed numbers.
4. `harness/roles.py:25` currently fixes `ROLE_KINDS = ("orchestrator", "worker", "verifier")` as a plain tuple. Adding `observer` as a fourth kind (design 2.5) is a real code-surface change, correctly deferred to sequencing step 5, but the AIDR record's own Question section does not state this deferral explicitly; it is only clear from the design draft's Part 3.
5. `tests/test_bidding.py`'s docstring specifies one whole-file `strict=True` xfail marker, removed only when the entire file is green, but the file's scenarios span record, conditional-degrade, calibration, and select-adjacent behavior together. This conflicts with Part 3's staged rollout (record before propose before select) unless implementing bid `record` mode (step 2) also builds more of the bid object model than record mode strictly needs, or the file is split by mode before implementation starts.

## Falsifiers

- Most important existing falsifier: the test pinning that `record` mode must never change the dispatched tier, named in design Part 4 as the test that would falsify the whole framing if it failed, already encoded as strict-xfail (`bid_record_no_routing_change` in `tests/test_bidding.py`).
- Missing falsifier: no committed, reproducible evidence yet for the Part 4 hand-run probe deciding whether "zero resolvable citations voids the bid" is calibrated correctly for small or cheap brains. Currently a manual, ungated, pre-code step with no recorded result.
- Condition that would reverse this recommendation: evidence, once `harness/bidding.py` exists, that bid data measurably influences the routing decision in `record` or `propose` mode through any path (direct read, log ordering, cache effects, an implementer role incidentally reading bid output). That would mean invariant 6 is structurally at risk rather than merely instrumented, and this reviewer would move to oppose until a hard code-level partition exists and is proven by a specific test.

## Implementation map

- First safe slice: observer deterministic layer plus `harnessie observe` (design Part 3 step 1). No dispatch, routing, or schema change; the byte-identity guard already covers it.
- Required production modules: `harness/observer.py` (new) and a CLI verb in `harness/cli.py`. For bid `record` mode (step 2, once step 1 is done): `harness/bidding.py` (new), a phase-dispatch read hook in `harness/runner.py` for the optional `bid:` key, a schema addition in `harness/schemas/v1/` and `harness/schema.py`, new event kinds in `harness/events.py`, calibration counters in `harness/trace_eval.py`, and a `GOVERNANCE_KINDS` addition in `harness/audit.py` limited to `bid_selected`/`bid_fallback` only (design 1.10), not `bid_recorded`.
- Tests that should turn from strict xfail to passing: all of `tests/test_observer.py` for step 1. For step 2, ideally only the record-mode subset of `tests/test_bidding.py`, but see Finding 5: the file's single whole-file marker may force implementing conditional-degrade and calibration-count logic before any of it can go green, which should be resolved before coding starts.
- Work explicitly deferred: `select` mode and its own AIDR with scorecard evidence attached; observer commentary and the fourth role kind; scorecard-corpus admission of external benchmark-style items; the cross-brain pre-mortem variant.
- Main regression risk: the test-file granularity mismatch in Finding 5. A contributor implementing "just record mode" per Part 3 step 2 may find the strict-xfail file will not go green without also building conditional-degrade and calibration-count logic, silently expanding the first bid-round slice beyond what the sequencing implies.

## Cross-engine handoff

- One claim another engine should challenge: that `record`/`propose` bid data can be kept structurally separate from the routing decision using only "the routing table still decides" as the guarantee, with no dedicated test yet forbidding `harness/routing.py` from reading bid state.
- One question another engine should answer: does `tests/test_bidding.py`'s single whole-file `strict=True` xfail marker match the Part 3 staged rollout (record before propose before select), or does it force a larger first implementation than the sequencing describes? Codex's module-mapping lane is best positioned to answer this precisely.
- Evidence Sam should compare across all four reports: whether each engine scopes "ready for arbitration" to the same slice (Part 3 steps 1-2) or to the full six-step plan. Divergence here is itself a signal for how narrowly or broadly the Arbitration section's boundary should be written.

## Verification

- `.venv/bin/python3 -m pytest -q tests/test_aidr_0009_guards.py tests/test_bidding.py tests/test_observer.py`: 2 passed, 37 xfailed.
- `.venv/bin/python3 -m pytest -q` (full suite): 496 passed, 1 skipped, 37 xfailed.
- No files were edited, created, deleted, staged, committed, stashed, reset, pushed, merged, or installed while producing the review itself. This file was written after the review, at explicit operator request, as a separate act.
