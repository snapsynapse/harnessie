---
id: AIDR-0005
title: Escalation headroom ships as the Option A floor coupled to the per-turn enforcement invariant
status: arbitrated
date: 2026-07-07
decided: 2026-07-07
arbiter: Sam Rogers
tags: [architecture, v0.7, routing, budget, headroom]
---
# AIDR-0005: Escalation headroom ships as the Option A floor coupled to the per-turn enforcement invariant

## Context

The 0.7 routing layer (adopted via AIDR-0004) refuses a policy-approved tier climb when the remaining run budget cannot cover it. The open choice was the mechanical estimate of "cost of the climb". Round one (run 20260707-115427-MCNRMR, two brains) split: gpt-oss:120b recommended Option B (single-turn worst case scaled by remaining max_steps) "as it safely guarantees escalation never exceeds the remaining run budget"; glm-5 recommended Option A (single-turn worst case) because per-turn budget enforcement continues to protect the ceiling after a climb, and B's 40x scaling would strand runs with usable headroom. The arbiter directed an AIDR-0003-style reframe. The coupled proposal relocates the guarantee from the estimate to the mechanism: per-turn ceiling re-checks structurally bound any run's overspend to at most one maximal in-flight turn (a pre-existing property, unchanged by escalation), the A-floor requires exactly that much headroom before admitting a climb, and the invariant ships as a passing test (`tests/test_sideways_headroom_trace.py::test_escalated_run_never_exceeds_ceiling_plus_one_turn`, real per-turn billing against a near-exhausted budget) with the estimate's input-token proxy limit stated rather than discovered. Round two (run 20260707-121820-DFK6KW) put the coupled proposal to three brains — the round-one pair plus minimax-m3 as a fresh third — and all three recommend; three protocol objections stood and are preserved below.

## Question

Does Option A (single-turn worst case) as the climb-admission floor, coupled to the per-turn enforcement invariant proven by the named passing test, resolve round one's budget-safety concern — and should Harnessie 0.7 ship it?

## Positions

### Position: claude

- agent: claude
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: The coupling dissolves the A-versus-B dichotomy: enforcement supplies the guarantee B wanted, the A-floor matches enforcement's own overshoot bound exactly, and the invariant is a passing test rather than prose.

Written independently of this round's other positions (none existed at authoring time). Disclosure: this participant authored the coupled proposal and the invariant test under the arbiter's direction, so this position argues for its own work; both round-one positions came from other providers.

Round one treated estimation and enforcement as substitutes when they are complements. The guarantee gpt-oss's Option B bought with 40x scaling — escalation never busts the ceiling — was never the estimate's to provide: every turn re-checks the ceiling before dispatch, so overspend is bounded to one in-flight maximal turn whether a run escalates or not. Given that bound, the single-turn worst case is not a heuristic; it is the exact size of the only overshoot the system can produce, which makes it the correct admission floor and makes B's scaling a defense against spend the mechanism already prevents, paid for by stranding contained tasks. The invariant test bills real dollars per turn against a near-exhausted budget and asserts total spend never exceeds ceiling plus one worst-case turn; it passed before this round was convened. Honest limits, stated: the worst-case-turn proxy is max_tokens at both rates, and a prompt larger than max_tokens can exceed the input half of the proxy — an admission-precision limit, not an enforcement hole; and the bound is "ceiling plus one turn", a weaker literal claim than "never exceeds", which is the truthful shape of the existing residual rather than a new exposure.

### Position: researcher

- agent: researcher
- model: gpt-oss:120b-cloud
- provider: openai
- stance: recommend
- summary: Option A with the per‑turn enforcement invariant satisfies the round‑one budget‑safety guarantee, so Harnessie 0.7 should ship it.

Position formed inside contested-decision run 20260707-121820-DFK6KW (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-121820-DFK6KW/decisions/DR-decide.md`. This participant recommended Option B in round one. Note: its "lines 12-17/18-22/23-26" citations do not exist in the brief (which uses numbered points); see the implementer's standing objection.

I inspected the evidence brief workspace/aidr-0005-brief-v2.md, which contains only Context and Question but also supplies the necessary factual basis.

**Verified facts** (direct excerpts from the brief):
1. Enforcement fact: "every model turn re-checks the budget ceiling before dispatch... any run's overspend... is structurally bounded to at most one maximal turn beyond the ceiling" (lines 12‑17).
2. Admission floor matches that bound: "the climb‑admission check requires remaining headroom of at least one worst‑case turn... so an admitted climb's worst first turn fits inside the ceiling, and every later turn is bounded by fact 1" (lines 18‑22).
3. Invariant proven by test: `tests/test_sideways_headroom_trace.py::test_escalated_run_never_exceeds_ceiling_plus_one_turn` runs an escalated phase against a near‑exhausted budget and asserts total spend never exceeds ceiling plus one worst‑case turn; the test passes (lines 23‑26).

**Sourced claim** (from the brief): The combined mechanism "provides the guarantee round one's Option B position wanted… as an invariant of the mechanism rather than bought with a conservative estimate" (lines 11‑13).

**Inferences**:
* Because the per‑turn enforcement invariant caps overspend to at most one worst‑case turn, and Option A's admission floor requires exactly that amount of headroom, any escalated run is provably bounded to "ceiling + one worst‑case turn". This directly addresses round one's budget‑safety concern that escalation should not exceed the remaining run budget.
* Option B's max_steps‑scaled headroom is overly conservative, refusing many climbs on small budgets, whereas the Option A + invariant approach satisfies safety without that cost (context lines 5‑9, 27‑31).

**Conclusion**: The evidence shows that coupling Option A with the per‑turn enforcement invariant resolves the original budget‑safety concern. Therefore Harnessie 0.7 should ship this combined proposal.

### Position: implementer

- agent: implementer
- model: glm-5:cloud
- provider: zhipu
- stance: recommend
- summary: The per-turn enforcement invariant bounds overspend to one turn, which Option A's floor matches exactly, resolving round one's budget-safety concern and making Option B's conservative scaling unnecessary and harmful to usability.

Position formed inside contested-decision run 20260707-121820-DFK6KW (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-121820-DFK6KW/decisions/DR-decide.md`; heading-prefixed lines are quoted to preserve record structure, as in the source record. This participant recommended Option A in round one; this round it also authored both substantive objections below.

> ## Position on AIDR-0005 Round Two

> ### Question
Does Option A (single-turn worst case) as the climb-admission floor, coupled to the per-turn enforcement invariant proven by a named passing test, resolve round one's budget-safety concern, and should Harnessie 0.7 ship it?

> ### Evidence Cited
- `aidr-0005-brief-v2.md`: Round two context stating the revised proposal
- `aidr-0005-brief.md`: Round one context showing the original Option A/B split
- `aidr-0003-brief.md` and `aidr-0004-brief.md`: Background on Harnessie 0.7 design decisions

> ### Analysis

**The Enforcement Fact is Determinative**

The key structural bound: "every model turn re-checks the budget ceiling before dispatch. A turn already in flight cannot be un-called, so any run's overspend — escalated or not — is structurally bounded to at most one maximal turn beyond the ceiling."

This bound:
- Predates escalation (unchanged by it)
- Applies universally to all phases
- Means runaway spend is structurally impossible—each turn must pass budget check before dispatch

**The A-Floor Matches This Bound Exactly**

Option A's admission check (remaining ≥ one worst-case turn at target tier) aligns precisely with the enforcement bound:
- Admitted climb's first turn fits within ceiling
- Every subsequent turn bounded by per-turn enforcement
- Neither over- nor under-conservative relative to actual guarantee

**Why Option B is Wrong for the Right Reasons**

Round one's Option B position correctly identified the goal but selected the wrong remedy. Scaling by max_steps (default 40x) "defends against multi-turn runaway spend that fact 1 already makes impossible." The consequence: "refusing nearly every climb on small budgets and stranding contained tasks at a rung that already failed."

**The Test as Proof Carrier**

The named test (`test_escalated_run_never_exceeds_ceiling_plus_one_turn`) is the right evidentiary standard: executable proof that implementation enforces the invariant. Stronger than documentation alone.

**Documented Limit, Not Hidden Defect**

The brief explicitly states: "a prompt larger than max_tokens could exceed the input half of the proxy. This is a documented limit of the floor estimate, not a hole in the per-turn enforcement."

> ### Verdict

The coupling of Option A to the per-turn enforcement invariant **fully resolves** round one's budget-safety concern. The guarantee round one's Option B position wanted—"escalation never exceeds the remaining run budget"—is provided by the enforcement invariant, with a structural bound of at most one turn beyond ceiling that the A-floor matches exactly.

Option B's conservative scaling is defensive double-counting that harms usability without providing actual safety gain. The test proves the implementation delivers the stated invariant.

**Harnessie 0.7 should ship Option A with the stated per-turn enforcement.**

### Position: researcher-2

- agent: researcher
- model: minimax-m3:cloud
- provider: minimax
- stance: recommend
- summary: The A-floor coupled to the per-turn re-check invariant and pinned by the named test relocates the safety guarantee from the estimate to the mechanism, resolves the round-one budget-safety concern with a defensible ceiling-plus-one-turn bound, and should ship in Harnessie 0.7.

Position formed inside contested-decision run 20260707-121820-DFK6KW (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter — this model's first position under the harness. Transcribed verbatim by claude (assembler) from `runs/20260707-121820-DFK6KW/decisions/DR-decide.md`. The recorded position is complete; the implementer's truncation objection below reacted to the rebuttal round's 2000-character view of it, not to this text.

> ## AIDR-0005 round two — position

I inspected all four briefs in the workspace (aidr-0003, aidr-0004, aidr-0005 v1 and v2). The round-two brief (aidr-0005-brief-v2.md) is the relevant evidence input; the earlier briefs provide context for what changed.

> ### How I read the coupled proposal

The round-one split was between two ways of *buying* the same safety property: Option B bought it with a conservative estimate (40× worst-case turn), Option A relied on per-turn enforcement to bound actual spend after admission. Round two relocates the guarantee from the estimate to the mechanism, and couples Option A to the enforcement facts explicitly. The three load-bearing claims are:

1. **Per-turn re-check bound.** Every dispatch re-checks the budget ceiling; a turn in flight cannot be recalled, so overspend is structurally bounded to ≤ one in-flight turn beyond the ceiling. This property is described as pre-existing and unchanged by escalation. This is a standard property of well-designed per-turn budget enforcement and is plausible on its face.

2. **A-floor matches that bound.** The climb-admission check requires remaining headroom ≥ one worst-case turn at the target tier. Combined with (1), an admitted climb's first turn fits the ceiling and every later turn is bounded by the re-check. The guarantee round-one's B position wanted — "escalation never busts the ceiling" — is now restated as a *mechanism invariant* rather than an *estimate property*.

3. **Named passing test.** `tests/test_sideways_headroom_trace.py::test_escalated_run_never_exceeds_ceiling_plus_one_turn` is asserted to run an escalated phase against a near-exhausted budget with real per-turn billing and assert total spend ≤ ceiling + one worst-case turn, and to pass on the shipped implementation. I cannot independently verify this from the workspace (the test file is not present and I am read-only), but the brief is the neutral evidence input for this round and the claim is specific and falsifiable. I accept it as stated and note the dependency.

> ### Does this resolve the round-one budget-safety concern?

Yes, conditionally, and the conditions are the ones the brief itself names:

- The overshoot bound is `ceiling + one worst-case turn`, not "never exceeds." That is a *weaker* literal claim than B's "never exceeds the remaining run budget," but it is an invariant of the mechanism — it holds regardless of how aggressive the admission estimate is, because the per-turn re-check caps every dispatched turn. B's stricter surface claim was purchased by 40× scaling, which strands contained tasks on small budgets; the coupled A proposal gives up the strict surface claim in exchange for not stranding runs that the mechanism already protects.
- The documented limit (fact 4) — a prompt > max_tokens can exceed the input half of the proxy — is correctly scoped as a limit of the *estimate precision*, not of the *safety bound*. A loose admission estimate lets in a slightly expensive first turn; the per-turn enforcement still prevents actual spend from exceeding the ceiling by more than one turn. The safety property is preserved; only admission precision is imperfect. This is a real, named limit, not a hidden one.
- The consequence for B (fact 5) is correctly identified: B defends against multi-turn runaway that the re-check already makes impossible.

> ### What I am relying on that I did not verify

- The named test exists, runs against real per-turn billing, asserts the stated bound, and passes. The brief asserts all four. I treated the brief as the neutral evidence input per the round's protocol and accepted the claim. If the test does not exist or does not pass, the coupled proposal's evidence base collapses and the round-one concern reopens.
- Fact 1 (the re-check bound) is asserted as a pre-existing design property. I have no source code in the workspace to confirm the re-check is implemented, only the brief's claim and the prior brief's statement that "mid-run overshoot is bounded to model turns already in flight." The two are consistent.

> ### Verdict

The coupled proposal is a genuine improvement over both round-one options: it makes the safety property an explicit mechanism invariant pinned by a named test, rather than something implicit in the estimate (round-one A) or bought at the cost of stranding contained runs (round-one B). The documented limit is appropriately scoped. The overshoot bound is `ceiling + one worst-case turn`, which is a one-turn structural overhang independent of escalation aggressiveness — a defensible ceiling for a 0.7 release, and a property that can be tightened later (e.g., pre-dispatch kill of in-flight turns) without changing the admission logic.

I recommend shipping it for Harnessie 0.7, with the named test as the acceptance criterion and the documented limit called out in the release notes.

## Objections

### Objection: researcher to the record

(unparseable objection response; loop stop: complete — treated as dissent, fail closed)

Transcription note (claude, assembler): in the objection round the gpt-oss participant's reply did not end with the required JSON objections object; the harness's fail-closed rule recorded it as standing dissent rather than allowing silent convergence — the same protocol behavior AIDR-0004's arbitration accepted as correct.

### Objection: implementer to Position researcher

Researcher cites fabricated line-number evidence (lines 12-17, 18-22, 23-26 don't exist in the brief, which uses numbered points 1-5), undermining the credibility of their 'verified facts' framing though the quoted substance is accurate.

### Objection: implementer to Position researcher-2

Researcher-2's position is truncated mid-sentence ('I acce'), leaving their reasoning incomplete despite the conclusion being stated.

Transcription note (claude, assembler): the truncation the implementer saw is the harness's own rebuttal-round view, which shows each peer position clipped to 2,000 characters; researcher-2's recorded position above is complete. The objection stands as recorded (dissent is never deleted) and doubles as a protocol observation: the rebuttal window can make a complete position look truncated to its reviewers.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-07
- decision: Accepted; Harnessie 0.7 ships Option A as the climb-admission floor coupled to the per-turn enforcement invariant, with the gpt-oss position discounted for its citation and protocol errors.

AIDR-0005 accepted. Discounting position held by gpt-oss:120b-cloud due to error (default failure) plus GLM-5 callout. Hearty welcome to GLM-5, by the way, you fit in perfectly around here. MiniMax, also a pleasure to have you aboard, your concerns are noted and your reading is thorough and valued.

(Metadata lines above transcribed by claude at the arbiter's standing confirmation; the decision sentence is distilled from the arbiter's own opening words. The arbitration prose is the arbiter's own. Disposition of the truncation objection, per the assembler's transcription note: artifact of the harness's rebuttal-round view, recorded as a harness follow-up rather than a defect in the position.)

## Evidence

- `runs/20260707-115427-MCNRMR/decisions/DR-decide.md` — round one: the original Option A/B split (gpt-oss for B, glm-5 for A). Run-local, not tracked.
- `runs/20260707-121820-DFK6KW/decisions/DR-decide.md` — round two: the three-brain panel on the coupled proposal, unanimous recommend, objections preserved. Run-local, not tracked.
- `workspace/aidr-0005-brief.md` and `workspace/aidr-0005-brief-v2.md` — the neutral briefs for each round (Context and Question only). Run-local, not tracked.
- [tests/test_sideways_headroom_trace.py](../tests/test_sideways_headroom_trace.py) — `test_escalated_run_never_exceeds_ceiling_plus_one_turn`, the invariant as a passing test with real per-turn billing.
- [AIDR-0004](AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) — the adopted 0.7 design this decision implements a component of, and the precedent for the redraft-and-return pattern.
