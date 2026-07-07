---
id: AIDR-0003
title: Adopt the 0.7.0 sovereignty cascade routing and containment boundary design
status: arbitrated
date: 2026-07-07
arbiter: Sam Rogers
decided: 2026-07-07
tags: [architecture, roadmap, v0.7, routing, containment]
---
# AIDR-0003: Adopt the 0.7.0 sovereignty cascade routing and containment boundary design

## Context

ROADMAP.md carries a full 0.7.0 design: sovereignty cascade routing (named cascade policies over the existing reformulate/effort/tier gate ladder, containment-constrained ladders, sideways provider fallback distinct from upward escalation, a sovereign tier slot, a reserved pre-gate, escalation headroom, routing_trace) plus a containment boundary (deterministic PII strip/rehydrate at the provider adapter, a stricter secrets class, tool-output scrubbing, per-tool rehydration grants) with eval-shaped proof (canary leak evals, gate-integrity canaries, bundle-identity brain claims). The scope was re-cut 2026-07-07: three write-safety items (blast-radius ceilings, declared-write-path conflict refusal, maiden-voyage rule) moved to a new 0.8.0 milestone because they bound write damage, not data exposure, and had no 0.7 acceptance coverage. The named prerequisite, budget-safety hardening, closed 2026-07-07 (headroom-scoped child budgets with live charge-through). The roadmap gates 0.7 implementation on this record: the harness's own governance decides its routing layer.

## Question

Should Harnessie 0.7.0 implement the sovereignty cascade routing and containment boundary design as specified in the ROADMAP.md 0.7.0 section (2026-07-07 re-cut), with its stated acceptance criteria, as the next release?

## Positions

### Position: claude

- agent: claude
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Implement the re-cut 0.7.0 as specified; routing and the boundary are one claim and are correctly shipped together, with the write-safety split making both milestones falsifiable.

Written independently; no other positions existed at authoring time.

The sovereignty claim is only mechanical if routing and containment land together: a containment-constrained ladder is meaningless without data classes, data classes are assigned by the boundary, and redaction legitimately transforms a task's allowed ladder. Shipping either half alone produces a claim that is half operator-habit, which is exactly what 0.7 exists to end. The re-cut strengthens the milestone rather than shrinking it: the three write-safety items had no acceptance coverage in the 0.7 bar and bound a different resource (write damage, not data exposure), so moving them to 0.8 gives each milestone a single falsifiable theme. The design also respects the codebase as it stands — it is policy scoping over the shipped gate ladder, not a new escalation engine, and the sideways-fallback rule (refusals and availability failures move across a tier, never up it) closes a real containment leak that up-tiering on refusal would open. The prerequisite that made escalation headroom honest (child budgets with live charge-through) is already landed and test-proven. Risks I weigh and accept: the boundary's regex-only filter will miss unstructured PII (mitigated by the canary evals stating what is and is not caught), and placeholder-soup may depress small-model gate pass rates (an open question the evals must answer before the sovereign tier is marketed). Neither risk is reduced by deferral.

### Position: researcher

- agent: researcher
- model: gpt-oss:120b-cloud
- provider: openai
- stance: oppose
- summary: The design's unresolved PII detection gaps and incomplete acceptance criteria make full implementation in 0.7.0 premature.

Position formed inside contested-decision run 20260707-102143-KCMUWR (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-102143-KCMUWR/decisions/DR-decide.md`.

**Verified fact**: The ROADMAP.md 0.7.0 (re‑cut 2026‑07‑07) proposes a "sovereignty cascade routing" system that adds named cascade policies, a `sovereign` tier slot, containment‑constrained ladders, sideways provider fallback, escalation headroom checks, and a detailed `routing_trace` — and a "containment boundary" that strips/re‑hydrates structured PII at the provider adapter, enforces a stricter secrets class, scrubs tool‑output, and uses per‑tool rehydration grants ( source: aidr-0003-brief.md, lines 9‑23).

**Sourced claim**: The brief lists several **known open questions** that directly affect the feasibility and safety of the proposed design: regex‑only filtering may miss unstructured PII, placeholder substitution could lower pass rates for small models, and mapping persistence across resume is undesigned ( source: aidr-0003-brief.md, lines 31‑34).

**Sourced claim**: The "maiden‑voyage rule"—a key write‑safety safeguard—was moved from 0.7 to 0.8 because it "had no 0.7 acceptance coverage" ( source: aidr-0003-brief.md, lines 24‑27).

**Inference**: Because the design's acceptance criteria do **not** yet cover critical safety aspects (e.g., write‑damage containment) and there remain unresolved technical risks (PII detection gaps, model‑performance impact, persistence handling), implementing the full sovereignty cascade routing and containment boundary in the 0.7.0 release would likely expose the system to data‑leakage and functional regressions. Therefore the prudent course is **not** to include the complete design in the next release.

**Conclusion**: Based on the evidence, the next release should defer the full implementation until the open questions are resolved and the acceptance criteria are expanded.

### Position: implementer

- agent: implementer
- model: glm-4.7:cloud
- provider: zhipu
- stance: recommend
- summary: Recommend proceeding with 0.7.0 implementation as specified; the design demonstrates disciplined scoping, production-proven foundation, concrete verification, and appropriate handling of open questions through opt-in compatibility and measurable acceptance criteria.

Position formed inside contested-decision run 20260707-102143-KCMUWR (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-102143-KCMUWR/decisions/DR-decide.md`; heading-prefixed lines are quoted to preserve record structure, as in the source record.

> ## Position Analysis

I have reviewed the neutral evidence brief for AIDR-0003 regarding whether Harnessie 0.7.0 should implement the sovereignty cascade routing and containment boundary design.

> ### Evidence Summary

The proposal consists of two coupled halves:

**Routing**: Policy scoping over gate ladders with cascade policies, tier ladders, escalation reasons, containment-constrained ladders, sideways provider fallback (explicitly never upward to prevent containment leaks), a `sovereign` tier slot between `local` and `frontier`, a `reserved:` pre-gate for work classes that never reach any model, escalation headroom, and `routing_trace` recording.

**Containment boundary**: Deterministic strip/rehydrate at the provider adapter with provenance from PAICE.work PBC production PII code, structured PII replacement with stable placeholders, stricter secrets class (halt-not-warn on egress), tool-output scrubbing, and per-tool rehydration grants starting deny-all.

**Proof mechanisms**: Canary leak evals (seeded fake PII/secrets, zero bytes in any egress), gate-integrity canaries, and bundle-identity brain claims.

**Re-cut scope**: Blast-radius ceilings, declared-write-path conflict refusal, and maiden-voyage rule were moved to 0.8.0 because they bound write damage rather than data exposure and lacked 0.7 acceptance coverage.

**Prerequisite status**: Closed as of 2026-07-07 - parallel phases now run on headroom-scoped child budgets with live charge-through.

**Known open questions**:
1. Regex-only filtering misses unstructured PII
2. Placeholder substitution may depress small-model gate pass rates
3. Mapping persistence across resume is undesigned

> ### Position

I recommend proceeding with the 0.7.0 implementation as specified, with the following reasoning:

**Strengths supporting recommendation:**

1. **Focused scope**: The re-cut demonstrates disciplined scoping - features that bound write damage rather than data exposure were appropriately moved to 0.8.0, keeping 0.7.0 focused on containment.

2. **Production-proven foundation**: The containment boundary adapts code with provenance from PAICE.work PBC production PII code, reducing implementation risk.

3. **Backward compatibility**: Phases that do not opt in behave byte-identically to 0.6, allowing incremental adoption without forced migration.

4. **Concrete verification**: The proof mechanisms (canary leak evals, gate-integrity canaries, bundle-identity brain claims) provide measurable acceptance criteria rather than vague assurances.

5. **Prerequisite closure**: The parallel phases budget prerequisite is already closed, removing a dependency blocker.

6. **Containment-first design**: The sideways fallback (never upward on refusal) and sovereign tier slot show thoughtful containment engineering rather than naive escalation.

**Caveats and mitigations:**

The open questions are significant but not disqualifying:
- **Regex-only PII filtering**: This is a known limitation of the current approach, but the canary leak evals provide concrete verification that the implemented filtering works as specified. Future enhancements can address unstructured PII.
- **Small-model gate pass rate depression**: This is a performance trade-off, not a correctness issue. The opt-in nature allows users to evaluate this trade-off for their use cases.
- **Mapping persistence across resume**: This is explicitly noted as undesigned, which is acceptable for a 0.7.0 release focused on containment rather than full lifecycle management.

The design represents a principled, scoped approach to data containment with measurable verification and backward compatibility. The open questions are appropriate for a 0.7.0 release and do not undermine the core containment objectives.

### Position: deepseek

- agent: deepseek
- model: deepseek-v4-pro:cloud
- provider: deepseek
- stance: oppose
- summary: The design ships known containment gaps and underspecified failure modes that make it unsafe for a release that claims to strengthen data-exposure controls.

Position formed in an isolated cloud inference run from the neutral brief (Context and Question only): this participant was shown no other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The proposal is ambitious and directionally correct: tiered routing with sovereignty slots, deterministic PII scrubbing, and canary-based proof are all valuable. However, the brief itself lists three open questions that are not merely cosmetic. First, "regex-only filtering misses unstructured PII" is a direct admission that the containment boundary can leak. A system that claims to prevent egress of secrets and PII but relies solely on regex is shipping a false sense of security; adversaries and even accidental data shapes will bypass it. Second, "placeholder substitution may depress small-model gate pass rates" is not a performance footnote—it means the scrubbing mechanism can silently degrade the quality of downstream model outputs, potentially causing functional regressions that users will discover in production. Third, "mapping persistence across resume is undesigned" means that if a run is interrupted, rehydration may fail or, worse, map placeholders incorrectly, corrupting results. These are not edge cases; they are fundamental to the containment guarantee the feature purports to provide.

The re-cut already deferred write-safety and blast-radius controls to 0.8.0 because they lacked acceptance coverage. The same discipline should apply here: the containment boundary has no demonstrated coverage for unstructured PII, no validated performance impact on gated models, and no design for stateful recovery. Shipping with these known holes undermines the trustworthiness of the entire release and sets a precedent that "known leaky" is acceptable. The strongest counterargument is that the current 0.6 release has no containment at all, so even a leaky boundary is an improvement, and the open questions can be addressed incrementally. But a security boundary that is known to fail on unstructured data is not a boundary—it is a decoration. Harnessie should not claim a capability it cannot deliver; the release should be delayed until the regex limitation is at minimum replaced with a structural approach, and the mapping persistence is designed.

### Position: kimi

- agent: kimi
- model: kimi-k2.5:cloud
- provider: moonshot
- stance: oppose
- summary: The 0.7.0 specification should not ship because its regex-only PII detection admits unstructured data leakage and its undesigned mapping persistence creates undefined failure recovery behavior.

Position formed in an isolated cloud inference run from the neutral brief (Context and Question only): this participant was shown no other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines (one typo, "unddesigned", corrected in the summary line only; prose untouched).

While the cascade routing architecture is sound—particularly the prohibition on upward tiering for refusals which prevents containment leaks—the containment boundary relies on regex-only filtering that explicitly "misses unstructured PII." Shipping a containment system with a known, uncapped leakage path for free-text PII creates false assurance and regulatory exposure. Additionally, "mapping persistence across resume is undesigned," meaning the rehydration state needed to restore user-facing output after a failure has no defined lifecycle or consistency model, risking production incidents. The provenance from PAICE.work PBC validates the structured PII handling but does not transfer to the regex gaps. The strongest consideration against this position is that the routing improvements—including sideways fallback and sovereign tiering—provide immediate availability and policy benefits, and the structured PII/secrets protections are already production-proven. Delaying 0.7.0 withholds these concrete gains for a perfectionist standard when the acceptance criteria already mandate zero-byte canary leaks for seeded data.

### Position: minimax

- agent: minimax
- model: minimax-m2.1:cloud
- provider: minimax
- stance: recommend
- summary: The sovereignty cascade routing and containment boundary design provides essential safety mechanisms for multi-tier LLM routing that justify adoption, despite meaningful concerns about unstructured PII filtering and small-model gate pass rate impacts.

Position formed in an isolated cloud inference run from the neutral brief (Context and Question only): this participant was shown no other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The routing architecture addresses a genuine operational need: tiered model selection with controlled escalation and strict containment boundaries. The sideways fallback (never upward) correctly prevents containment leaks when models refuse requests. The `sovereign` tier and `reserved:` pre-gate provide useful architectural primitives for production deployments.

The containment boundary design is sound in principle. Deterministic strip/rehydrate at the provider adapter with provenance from production PII handling suggests real-world maturity. The halt-not-warn stance on secrets is appropriate for safety-critical systems. Per-tool rehydration grants using the approval-policy grammar adds necessary granularity.

However, I must acknowledge the strongest counterargument: **regex-only filtering for unstructured PII is a known blind spot** that could result in sensitive data escaping containment. Free-text fields, natural language in prompts, or generated content may contain PII that pattern matching simply cannot detect. This is not a theoretical concern—it is a documented limitation. Additionally, placeholder substitution depressing small-model gate pass rates could disproportionately harm cost-conscious deployments.

These are real risks, but they are **known risks** that can be mitigated with complementary controls (additional filtering layers, monitoring, model-specific tuning). The design's overall structure is defensible, and the alternative—releasing without containment—poses greater danger. The canary leak evals provide empirical validation that the team can iterate on.

## Objections

It would seem the objections listed are more about the claim than about the mechanisms underneath. This is helpful but not exactly what I was aiming for.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-07
- decision: Do not adopt 0.7.0 as specified; redraft the spec for verifiable claim scoping and stronger routing coverage, then return to the same panel for a second round.

Let us not adopt v0.7.0 at this time. Let's redraft what it is and ensure that the new spec changes are correctly scoped for claims to be more verifiable. Also there's an opportunity to do more here with routing that may help. Once redrafted let's return to these same models with a better form of the question for a second round.

(Metadata lines above transcribed by claude at the arbiter's explicit confirmation; the decision sentence was proposed to and approved by the arbiter. The arbitration prose is the arbiter's own.)

## Evidence

- [ROADMAP.md 0.7.0 section](../ROADMAP.md) — the design under decision, including acceptance criteria and the 0.8 split rationale.
- [CHANGELOG.md Unreleased](../CHANGELOG.md) — the 2026-07-07 re-cut and the budget-safety prerequisite closure.
- [docs/threat-model.md](../docs/threat-model.md) — the shipped safety claims the containment boundary extends.
- `runs/20260707-102143-KCMUWR/decisions/DR-decide.md` — the contested-decision run record (gpt-oss and glm positions formed under harness isolation; hash-chained events log alongside). Run-local, not tracked.
- `workspace/aidr-0003-brief.md` — the neutral brief every external participant received (Context and Question only). Run-local, not tracked.
