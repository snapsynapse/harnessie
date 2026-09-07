---
id: AIDR-0009
title: Bid rounds and a run observer as Harnessie surfaces
status: arbitrated
date: 2026-09-01
decided: 2026-09-07
arbiter: Sam Rogers
tags: [architecture, routing, observability, narrate-rung]
---
# AIDR-0009: Bid rounds and a run observer as Harnessie surfaces

## Context

The proposal combines two capabilities: bid rounds collect candidate-model predictions before task execution; an observer reads existing event logs and explains what happened. Bid predictions could affect routing, containment and budgets. An offline observer can be built without invoking models or changing dispatch.

Fable proposed the full staged direction on September 1. Four September 4 readiness reviews evaluated that proposal in different lanes. Their attributable extracts are assembled below on September 7 at Sam's request. Original reports remain unchanged and linked. They are not newly solicited positions or a completed common objection round.

All favor starting with the deterministic observer. They differ over the scope to authorize now and conditions for later bidding. The September 4 preparation packet proposes the narrower offline observer acceptance contract. It supplies implementation requirements; it is not evidence that the implementation exists.

## Question

Should Harnessie adopt bid rounds and a run observer as drafted, and if so: does a `record` or `propose` bid round violate invariant 6 or instrument it; should `select` ship before calibration evidence exists; is a cited, claim-scored pre-mortem plus an internal-corpus scorecard a sufficient answer to overbidding; should the observer ever hold authority; and is a fourth role kind warranted?

### Agreement, scope difference and resolution

Editorial comparison of the source reports, not a vote:

| Topic | Agreement or difference | Decision impact |
|---|---|---|
| Deterministic offline observer first | Fable and all four reviews support it, subject to the stated integrity and non-participant boundary | Shared first slice; no recorded recommendation opposes this bounded start |
| Authorize bid-record mode now | Claude includes it in a bounded approval; Codex and Antigravity defer bidding from the first slice; Qwen asks for scope/prerequisite clarification | Actual difference in approval breadth, not disagreement about observer-first order |
| Commentary and model selection | Later work; selection needs calibration and a separate decision | No blanket authorization for these surfaces |
| Containment, budgets and calibration for bidding | Risks are identified; several exact policies/thresholds remain unset | Open design choices for any bidding authorization |

Scope resolved by Sam on September 7: approve the most conservative observer-only slice, aligning with Codex and Antigravity's bidding deferral. Bid-record mode, every other bid mode, commentary, new role kinds, automatic runner integration and selection remain deferred. The acceptance contract in the preparation packet governs offline implementation. The objections below remain part of the evidence: broader approval is declined, observer authority is excluded, bidding containment/budget/calibration decisions move to a later packet, observer context isolation remains an acceptance requirement, and test-marker separation is already prepared. This paragraph is the session editor's operational mapping of the human decision, not additional reviewer or arbiter prose.

## Positions

Assembly note, 2026-09-07: Fable's original position is unchanged. The four added sections contain verbatim extracts from existing readiness reviews, not new statements authored in the reviewers' names. Their original recommendation was `conditional`; `stance: alternative` is the assembling editor's format mapping for a qualified or narrower alternative to adopting the full proposal. Summaries are editorial navigation; quoted prose is the attributable source. No reviewer has endorsed this later assembly.

Exact hosted serving-model and provider identities were not captured in the reports; `not-recorded` below means missing metadata, not a provider. Qwen's operator-supplied tag is retained. The reviewers saw an existing proposal, had different briefs, and had unequal source access. This record makes no claim of a common blind review or earned `independent-positions`, even if the reference linter mechanically counts `not-recorded` as a second provider value.

### Position: Claude Fable 5

- agent: Claude Fable 5
- model: claude-fable-5-1
- provider: anthropic
- stance: recommend
- summary: Adopt both, in the order observer deterministic layer, bid `record` mode with pre-mortem and calibration, bid scorecard, `propose`, observer commentary, then `select` under its own record with scorecard data as evidence.

Written first, before any other position existed, in the session that produced the draft.

The observer ships first because it touches no dispatch path: a reducer over events the harness already emits, plus one CLI verb, closing a gap the public ladder admits. "Consumer, never participant" keeps it under ordinary change discipline. Commentary alone needs a new role kind, justified the way ARCHITECTURE justifies the existing three: "no tools, sees everything, changes nothing" is a constraint set none of them has.

The bid round is worth having only as a calibration instrument. In `record` mode the routing table still decides; the new thing is a recorded prediction a later verdict can score. That does not cross invariant 6; it makes the invariant checkable. `propose` surfaces the evidence to the operator, who edits config. `select` is the direction-setting piece and waits for the scorecard.

On overbidding: a bid is an opinion; a cited failure mode is a prediction the event log can confirm or refute. The three code rules make the pre-mortem shape the bid rather than decorate it. The scorecard measures the actual bundle with the actual prompt on packets whose outcome is known, which no external benchmark can do. Together they make overconfidence a number before any bid touches routing.

Risks: one call per candidate per phase (capped per round); contained phases must never bid to an exposed tier (existing `CONTAINED_TIERS` filter, to be proven red-then-green); bid reports are an injection surface like any tool result; same-provider bids are not independent and are observed, not refused.

### Position: Codex readiness review

- agent: Codex readiness review
- model: not-recorded
- provider: not-recorded
- stance: alternative
- summary: Implement only the deterministic offline observer first; defer all bidding, commentary and runner integration.

Imported from the [September 4 report](../audits/aidr-0009-readiness-review-codex-2026-09-04.md). Original recommendation: conditional. Exposure: Full repository access; red-first test and implementation mapping. Reviewed the existing proposal. Peer-report exposure at initial review was not recorded.

> Implement only deterministic offline observation for an existing run: verify `events.jsonl`, reduce it into stable cited JSON and Markdown, refuse narration on chain failure, and expose `harnessie observe RUN_ID`; exclude `--follow`, automatic `run --observe`, commentary, bidding, new role kinds, and source-log mutation.

> Oppose if arbitration permits observer output into agent, verifier, approval, halt, routing, or arbitration context, or permits bid predictions to affect dispatch before a separately approved, quantitatively gated `select` decision.

### Position: Claude Code readiness review

- agent: Claude Code readiness review
- model: not-recorded
- provider: not-recorded
- stance: alternative
- summary: Authorize a bounded scope including observer and subsequent bid-record mode; do not approve the entire six-step design.

Imported from the [September 4 report](../audits/aidr-0009-readiness-review-claude-code-2026-09-04.md). Original recommendation: conditional. Exposure: Full repository access at b3efeca; decision-readiness lane. Explicitly read the existing Fable position and design. No common peer objection round is recorded.

> Conditional. Sequencing steps 1-2 in the design draft (Part 3: deterministic observer layer, bid `record` mode) are well-bounded by existing guard tests and ready to authorize. The AIDR as posed asks for approval of a six-step plan whose later gates (`select`'s calibration threshold, the fourth role kind for commentary) are deliberately left as empirical unknowns pending scorecard evidence that does not yet exist. A single up-or-down arbitration on the full scope would either rubber-stamp undetermined numbers or block a safe first slice; recommend arbitration scope be split accordingly.

> observer deterministic layer plus `harnessie observe` (design Part 3 step 1). No dispatch, routing, or schema change; the byte-identity guard already covers it.

Editorial evidence correction: the guard mentioned in this historical excerpt checks absence of new artifacts/events and governance membership, not byte equivalence. The preparation packet records that limitation. The original reviewer wording is retained above.

### Position: Google Antigravity readiness review

- agent: Google Antigravity readiness review
- model: not-recorded
- provider: not-recorded
- stance: alternative
- summary: Ship the deterministic observer first; defer bid schema and candidate evaluation, and enforce containment and budgets before later bid calls.

Imported from the [September 4 report](../audits/aidr-0009-readiness-review-antigravity-2026-09-04.md). Original recommendation: conditional. Exposure: Full repository access at b3efeca; architecture lane. Reviewed the existing proposal. Peer-report exposure at initial review was not recorded.

> The two-surface design is architecturally sound and cleanly decoupled, provided the deterministic observer ships first with zero schema or role changes while candidate bid generation strictly enforces containment filters and budget ceilings before dispatching candidate calls.

> Deterministic run observer in `harness/observer.py` and CLI command `harnessie observe <run_id>`. Zero schema changes, zero prompt modifications, zero model calls.

### Position: Qwen readiness review

- agent: Qwen readiness review
- model: qwen3.8:latest
- provider: not-recorded
- stance: alternative
- summary: Start with the observer; confirm the scope and resolve calibration prerequisites before approving the broader design.

Imported from the [September 4 report](../audits/aidr-0009-readiness-review-qwen3-8-2026-09-04.md). Original recommendation: conditional. Exposure: No repository access; summary-only falsification lane. The tag was supplied by the operator, not independently attested. Different input from the repository reviewers.

> The design is internally coherent and the sequencing discipline (observer-first, record-before-propose-before-select) is
> sound, but the proposal currently conflates three distinct risk surfaces (determinism guarantees, calibration validity, and human-override safety)
> under a single AIDR, and at least two of its kill criteria are specified at a granularity that makes them unfalsifiable in a finite test cycle.

> Implement the deterministic observer and the `harnessie observe` CLI subcommand. This slice should:
>   - Read the existing event/hash-chain data (read-only, no writes to agent workspaces).
>   - Produce a cited narrative as a file outside agent workspaces (exact path to be specified by Sam).
>   - Have zero dependencies on bid, scoring, or commentary modules.
>   - Include the "consumer never participant" negative test (observer output not deserializable by any agent-context schema).
>   - Pass the byte-identity guards unchanged.

## Objections

These are objections and conditions extracted from the reports after the original Fable proposal. They are not a newly completed exchange between reviewers. Editorial disposition notes distinguish a still-open scope choice from a requirement already included in preparation; they do not speak for the reviewer or arbitrate the issue.

### Objection: Claude Code readiness review to approval of the full proposal

> Conditional. Sequencing steps 1-2 in the design draft (Part 3: deterministic observer layer, bid `record` mode) are well-bounded by existing guard tests and ready to authorize. The AIDR as posed asks for approval of a six-step plan whose later gates (`select`'s calibration threshold, the fourth role kind for commentary) are deliberately left as empirical unknowns pending scorecard evidence that does not yet exist. A single up-or-down arbitration on the full scope would either rubber-stamp undetermined numbers or block a safe first slice; recommend arbitration scope be split accordingly.

Source: [Recommendation](../audits/aidr-0009-readiness-review-claude-code-2026-09-04.md). Editorial disposition: open authorization boundary. Claude includes step 2, bid-record mode, in a bounded approval. Codex and Antigravity explicitly defer bidding from the first implementation slice. All can support observer-first sequencing without agreeing to authorize the same total scope now.

### Objection: Codex readiness review to observer authority or premature bid selection

> Oppose if arbitration permits observer output into agent, verifier, approval, halt, routing, or arbitration context, or permits bid predictions to affect dispatch before a separately approved, quantitatively gated `select` decision.

Source: [Falsifiers](../audits/aidr-0009-readiness-review-codex-2026-09-04.md). Editorial disposition: the proposed offline acceptance contract excludes these paths. The remaining choice is whether Sam accepts that narrow scope. No opposing recommendation to a strictly offline, non-participant observer was found.

### Objection: Google Antigravity readiness review to contained prompt leakage and bid budget exhaustion

> Contained phase prompt egress hazard during bid rounds: `test_select_contained_filters_exposed_tiers_before_ranking` tests ranking, but the candidate dispatch loop itself must filter candidate tiers against `CONTAINED_TIERS` (`local`, `sovereign`) before sending the rendered task packet to any brain. Dispatching a sensitive task packet to an exposed candidate in `record` mode would breach data containment before routing even occurs.

> Budget leakage across candidate bid rounds: Each candidate in `candidates:` incurs token and dollar spend. A phase declaring multiple candidates could consume substantial headroom before execution begins unless `Budget.child()` enforces `bid.max_usd` as a hard cap. If candidate calls exceed `max_usd`, the runner must drop to `bid_fallback: budget` and dispatch the configured route without failing the phase.

Source: [Findings 3 and 4](../audits/aidr-0009-readiness-review-antigravity-2026-09-04.md). Editorial disposition: future bidding remains blocked on pre-egress filtering and a real round cap. The preparation packet additionally notes that fallback cannot promise worker execution after parent-budget exhaustion. Whether invalid exposed candidates cause preflight refusal or filtering remains undecided. None of these calls occur in the offline observer.

### Objection: Qwen readiness review to unspecified calibration prerequisites

> If the calibration scoring harness (Brier, over/underclaim, pre-mortem hit rate) does not already
> exist as a standalone module with its own tests, then step 3 of the sequence is not actually implementable without a significant prerequisite build
> that is not scoped in AIDR-0009. In that case, the AIDR should be split: AIDR-0009a for observer + record, AIDR-0009b for calibration harness +
> scorecard + propose, and the current AIDR-0009 should be amended to reflect this before arbitration. I would shift from *conditional* to *oppose* the
> current scope.

Source: [Falsifiers](../audits/aidr-0009-readiness-review-qwen3-8-2026-09-04.md). Editorial disposition: no calibrated bid-selection evidence is established. Qwen's proposed 0009a/0009b labels were suggestions, not allocated records. A later calibration/bidding packet needs a defined corpus, sample protocol, thresholds and dependency scope. This is a condition on the broader plan, not opposition to Qwen's own observer-first slice.

### Objection: Qwen readiness review to observer context leakage

> There is no stated test or check that verifies the observer's output does not appear in any agent-readable context (system
> prompt, tool result, event stream consumed by a brain). The proposal lists the invariant but I see no corresponding test name, test file, or assertion
> in the embedded summary. A "falsification test" for this invariant would be: inject a marker string into the observer's output, run the full pipeline,
> and assert the marker string does not appear in any agent-context capture. I do not see this in the proposed test set.

Source: [Falsifiers](../audits/aidr-0009-readiness-review-qwen3-8-2026-09-04.md). Editorial disposition: the reviewer had no repository access. A draft exclusion test already existed; the preparation packet records this correction. The offline contract adds no runner dispatch or model calls; stronger context-sentinel coverage remains required if automatic runner integration is proposed. Preparation and expected failures are not implemented enforcement.

### Objection: Claude Code and Codex readiness reviews to test markers forcing scope expansion

> `tests/test_bidding.py`'s docstring specifies one whole-file `strict=True` xfail marker, removed only when the entire file is green, but the file's scenarios span record, conditional-degrade, calibration, and select-adjacent behavior together. This conflicts with Part 3's staged rollout (record before propose before select) unless implementing bid `record` mode (step 2) also builds more of the bid object model than record mode strictly needs, or the file is split by mode before implementation starts.

Sources: [Claude finding 5](../audits/aidr-0009-readiness-review-claude-code-2026-09-04.md) and [Codex findings](../audits/aidr-0009-readiness-review-codex-2026-09-04.md). Editorial disposition: preparation at `9b30f40` split expected-failure markers by slice. This implementation-sequencing concern has been addressed in the prepared tests; it is not a reason to authorize deferred features or a retraction of either review.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-09-07
- decision: Approve overall with the most conservative scope, following Codex and Antigravity's bidding deferral rather than Claude's broader scope.

I approve overall and would like to scope things in the most conservative manner possible, so aligning with the Codex and anti-gravity bidding deferral, Rather than the Claude-proposed scope.

Transcription note: the preceding paragraph is Sam Rogers's verbatim decision in this task on 2026-09-07. The session agent transcribed it and normalized the metadata and decision sentence; it did not supply a separate human rationale. The operational scope mapping appears under Question.

## Evidence

- [Codex readiness review, September 4](../audits/aidr-0009-readiness-review-codex-2026-09-04.md): unchanged source of the attributed extracts above.
- [Google Antigravity readiness review, September 4](../audits/aidr-0009-readiness-review-antigravity-2026-09-04.md): unchanged source of the attributed extracts above.
- [Qwen readiness review, September 4](../audits/aidr-0009-readiness-review-qwen3-8-2026-09-04.md): unchanged source of the attributed extracts above.
- [Terminal review provenance](../audits/terminal-smoke-test-2026-09-04.md): unequal repository access, operator-supplied Qwen tag, and missing hosted-model identities.
- [Preparation and accepted observer packet, 2026-09-04](../audits/aidr-0009-preparation-2026-09-04.md): reconciles all four reviews, specifies the accepted first slice, and records deferred bidding prerequisites. Supporting synthesis, not an independent Position or human arbitration.
- [Design draft: bid rounds and the run observer](AIDR-0009-design-draft.md)
- [AIDR-0009 readiness review, Claude Code engine, 2026-09-04](../audits/aidr-0009-readiness-review-claude-code-2026-09-04.md): source readiness review; attributed extracts now appear above with exposure and format-mapping disclosures. The source is preserved unchanged.
- Red-first falsifiers, written before code: [tests/test_bidding.py](../tests/test_bidding.py), [tests/test_observer.py](../tests/test_observer.py), [tests/test_aidr_0009_guards.py](../tests/test_aidr_0009_guards.py) (no-opt-in artifact and governance-membership guards). Offline observer tests are now active; deferred slices retain strict xfail. Eight observer scenarios run in [evals/observer.yaml](../evals/observer.yaml); bidding and commentary remain [pending](../evals/pending/README.md). Kill criteria are in the draft's Part 4.
- [Offline observer implementation audit, September 7](../audits/observer-implementation-2026-09-07.md): current local verification and delivery boundary for the approved slice.
- [INTENT.md](../INTENT.md) invariants 6, 8, 10, 12, 13
- [harness/routing.py](../harness/routing.py), [harness/adversarial.py](../harness/adversarial.py), [harness/verify_evidence.py](../harness/verify_evidence.py), [harness/live_scorecard.py](../harness/live_scorecard.py)
- [docs/ladder.md](../docs/ladder.md), [docs/brains.md](../docs/brains.md)
