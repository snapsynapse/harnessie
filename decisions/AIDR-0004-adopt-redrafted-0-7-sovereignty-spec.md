---
id: AIDR-0004
title: Adopt the redrafted 0.7.0 sovereignty spec (round two of AIDR-0003)
status: arbitrated
date: 2026-07-07
decided: 2026-07-07
arbiter: Sam Rogers
tags: [architecture, roadmap, v0.7, routing, containment, round-two]
---
# AIDR-0004: Adopt the redrafted 0.7.0 sovereignty spec (round two of AIDR-0003)

## Context

Round two of the 0.7.0 adoption decision. AIDR-0003 (arbitrated 2026-07-07) put the original design to a six-model panel, which split 3-3; the arbiter decided not to adopt as first specified and directed a redraft with verifiably scoped claims and harder routing leverage, returning to the same panel. The redrafted ROADMAP.md 0.7.0 responds to the round-one oppose positions with four changes: the containment claim becomes a per-data-class coverage table (structured PII and secrets: boundary-caught; unstructured free-text PII: named as NOT boundary-caught); contained routing explicitly owns that residual (a free-text-sensitive data class never egresses past the local/sovereign tier set); the strip-map lifecycle across resume is designed with fail-closed rehydration (was undesigned); and placeholder impact on gate pass rates becomes a published per-brain scorecard number (was an open question). Routing mechanics, the secrets class, the 0.8 write-safety split, and the byte-identical opt-out are unchanged from round one. The same six models from AIDR-0003 form this round's panel.

## Question

Does the redrafted 0.7.0 specification (coverage-table claim scoping, routing ownership of the unstructured residual, designed strip-map lifecycle, published placeholder-impact deltas) resolve the round-one objections well enough that Harnessie should implement it as the next release?

## Positions

### Position: claude

- agent: claude
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: The redraft converts every round-one objection into a falsifiable claim or a designed mechanism without weakening the architecture; implement it.

Written independently of this round's other positions (none existed at authoring time). Disclosure: this participant authored the redraft under the arbiter's direction, so this position argues for its own work; the round-one oppose arguments it responds to came from other providers.

Round one's strongest attack was DeepSeek's: a boundary known to fail on unstructured data is decoration. The redraft accepts that premise instead of arguing with it — the boundary no longer claims to be a total boundary. The claim is now a coverage table where the unstructured row explicitly reads "not caught by the filter", and the covering mechanism for that row is routing: data the filter cannot classify never leaves the local/sovereign tier set, so the leak path the objection named (free-text PII egressing to an exposed provider) is closed by never-egress rather than by imperfect filtering. This is stronger than any structural-filter alternative, which would have put a model in the filter path and opened the prompt-injection hole the design correctly refuses. The undesigned strip-map lifecycle is now specified with the two properties that matter: secrets never persist anywhere (nothing to leak at rest), and a missing or corrupt map fails closed with no guess-rehydration. Kimi's regulatory-exposure concern is answered by the same table — a scoped, published claim with a named residual and covering mechanism is defensible; a blanket claim was not. The placeholder-soup risk stops being deferrable by becoming a per-brain published number gated by acceptance. What the redraft deliberately does not do is shrink scope: every round-one mechanism ships as before, so the recommend positions lose nothing. Strongest consideration against: the coverage table and never-egress guarantee add eval surface that must all go green before release, and contained routing makes the sovereign/local tier a single point of capability failure for sensitive tasks — if small local brains cannot pass gates on placeholder-laden contained work (the exact delta the new scorecard measures), contained tasks may stall rather than leak, which is the correct failure direction but a real operability cost.

### Position: researcher

- agent: researcher
- model: gpt-oss:120b-cloud
- provider: openai
- stance: recommend
- summary: The redraft resolves all main round‑one objections, so Harnessie should adopt it.

Position formed inside contested-decision run 20260707-104319-1MG564 (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-104319-1MG564/decisions/DR-decide.md`.

> # Position on AIDR‑0004

**Verified Fact:** The brief lists the round‑one objections as: regex‑only filtering admits unstructured‑PII leakage while the design claimed a “containment boundary” (false‑assurance risk); placeholder‑map persistence across resume was undesigned; and placeholder substitution impact on small‑model gate pass rates was unmeasured. [source: aidr-0004-brief.md]

**Sourced Claims from the redrafted 0.7.0 specification (ROADMAP.md):**
1. A coverage table scopes claim guarantees per data class, stating that structured PII and secrets are caught by the boundary, while unstructured free‑text PII is not caught by the boundary but is covered by contained routing. [source: aidr-0004-brief.md]
2. Contained routing owns the residual unstructured PII, ensuring tasks carrying such data never leave the local/sovereign tier set. [source: aidr-0004-brief.md]
3. A strip‑map lifecycle makes the placeholder map an operator‑boundary artifact stored outside run artifacts; secrets never enter it; on resume the map is reloaded, and a missing or corrupt map triggers a fail‑closed behavior (placeholders remain placeholders, the report names the issue). [source: aidr-0004-brief.md]
4. A measured placeholder‑impact delta is published per proven brain in docs/brains.md, providing a gate‑pass‑rate delta with the boundary on versus off. [source: aidr-0004-brief.md]
5. Evaluation honesty is extended: unstructured canaries must be proven contained by routing (never egressing an exposed tier), rather than being claimed as filtered. [source: aidr-0004-brief.md]

**Inference:**
- The coverage‑table directly addresses the false‑assurance risk by removing the claim that the boundary catches unstructured PII and delegating that responsibility to routing, eliminating misleading assurance.
- Contained routing guarantees unstructured PII never leaves the sovereign tier, mitigating the leakage risk inherent in regex‑only filtering.
- The strip‑map lifecycle design resolves the placeholder‑map persistence issue by providing explicit storage, reloading on resume, and a fail‑closed response to corruption or loss.
- Publishing the placeholder‑impact delta supplies the previously missing empirical measurement of gate‑pass‑rate effects, satisfying the third objection.
- With scoped claims, robust routing for residual data, a designed placeholder‑map lifecycle, and measurable impact data, all primary round‑one objections are resolved; there is no remaining substantive barrier to adopting the specification as the next Harnessie release.

**Conclusion:** The redrafted 0.7.0 specification adequately resolves the round‑one objections, and Harnessie should implement it in the next release.

{"stance":"recommend","summary":"The redraft resolves all main round‑one objections, so Harnessie should adopt it."}

### Position: implementer

- agent: implementer
- model: glm-4.7:cloud
- provider: zhipu
- stance: recommend
- summary: The redrafted 0.7.0 specification resolves all three round-one objections through honest claim scoping, complete placeholder-map lifecycle design, and required impact measurement, making it suitable for implementation as the next release.

Position formed inside contested-decision run 20260707-104319-1MG564 (isolated model context, read-only tool grants, hash-chained event log); served via Ollama Cloud through the harness's openai-compat adapter. Transcribed verbatim by claude (assembler) from `runs/20260707-104319-1MG564/decisions/DR-decide.md`.

I examined the evidence briefs AIDR-0004 (round two) and AIDR-0003 (round one) to form a position on the redrafted Harnessie 0.7.0 specification.

> ## Round-One Objections

From AIDR-0003, the oppose positions converged on three defects:
1. **False-assurance risk**: Regex-only filtering admits unstructured-PII leakage, yet the design claimed a "containment boundary" it could not deliver
2. **Undesigned lifecycle**: Placeholder-map persistence across resume had no specified design
3. **Unmeasured impact**: Placeholder substitution's effect on small-model gate pass rates was unknown

> ## Redraft Analysis

The redraft (AIDR-0004) responds to each:

**Objection 1 (false-assurance) → RESOLVED**: The coverage table replaces the blanket claim. The specification now explicitly states what the boundary catches (structured PII, secrets) and what it does NOT catch (unstructured free-text PII). The residual is owned by "contained routing"—unstructured PII never egresses to exposed tiers at all. The two halves cover each other's blind spots "by construction" rather than by assertion.

**Objection 2 (undesigned lifecycle) → RESOLVED**: Complete strip-map lifecycle is specified: placeholder map stored outside run artifacts, secrets never enter it (resolve from environment at tool boundary only), resume reloads before rehydration, missing/corrupt maps fail closed (placeholders stay placeholders, no guess-rehydration). Clear acceptance criteria for resumed runs and corrupt maps.

**Objection 3 (unmeasured impact) → RESOLVED**: Gate pass-rate delta (boundary on vs off) must be published per proven brain in docs/brains.md. This transforms the unknown concern into a required, measured metric.

Additional improvement (Response #5) extends eval honesty: unstructured canaries must be proven contained by routing, not claimed as filtered—preventing the false-assurance pattern from recurring.

> ## Assessment

The unchanged core mechanics (routing cascade, sideways fallback, sovereign tier, secrets class, etc.) were not the source of objections. The objections were about claim scope, missing lifecycle, and unmeasured impact. All three are substantively addressed. The complementary design—boundary catches what regex can classify, routing contains what it cannot—is sound because containment is enforced by tier constraints rather than content analysis.

The budget-safety prerequisite is closed, removing a dependency block.

The redraft resolves the round-one objections well enough for implementation.

{"stance":"recommend","summary":"The redrafted 0.7.0 specification resolves all three round-one objections through honest claim scoping, complete placeholder-map lifecycle design, and required impact measurement, making it suitable for implementation as the next release."}

### Position: deepseek

- agent: deepseek
- model: deepseek-v4-pro:cloud
- provider: deepseek
- stance: recommend
- summary: The redraft resolves all three round-one objections by scoping claims to a verifiable table, designing the strip-map lifecycle, and publishing placeholder-impact deltas, making the specification honest and implementable.

Position formed in an isolated cloud inference run from the neutral round-two brief (Context and Question only): this participant was shown none of this round's other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own output.

The redraft directly addresses each round-one defect: the coverage table eliminates false assurance by explicitly stating what the boundary does and does not catch; the contained routing design now owns the unstructured-PII residual, ensuring it never egresses to exposed tiers; the strip-map lifecycle is fully specified with fail-closed behavior; and the placeholder-impact delta is measured and published. These changes convert the specification from an overclaimed design into an honest, verifiable one. The strongest consideration against adoption is that the routing containment’s effectiveness hinges on tasks correctly declaring their data class—a human-dependent step that could be misapplied, potentially allowing unstructured PII to leak if a task is misclassified. However, this is a new operational concern, not a failure to resolve the original objections, and the design’s explicit scoping and canary tests mitigate it sufficiently for implementation.

{"stance": "recommend", "summary": "The redraft resolves all three round-one objections by scoping claims to a verifiable table, designing the strip-map lifecycle, and publishing placeholder-impact deltas, making the specification honest and implementable."}

### Position: kimi

- agent: kimi
- model: kimi-k2.5:cloud
- provider: moonshot
- stance: recommend
- summary: The redraft resolves round-one's false-assurance and lifecycle gaps by explicitly scoping boundary claims to structured data, designing fails-closed map persistence, and measuring gate impact, satisfying the arbiter's criteria for implementation.

Position formed in an isolated cloud inference run from the neutral round-two brief (Context and Question only): this participant was shown none of this round's other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own output.

1. **Stance:** recommend

2. **Summary:** The redraft resolves round-one's false-assurance and lifecycle gaps by explicitly scoping boundary claims to structured data, designing fails-closed map persistence, and measuring gate impact, satisfying the arbiter's criteria for implementation.

3. **Argument:** The redraft satisfactorily addresses the fatal defects identified in round one. By replacing blanket claims with a coverage table, it eliminates false assurance: unstructured PII is explicitly acknowledged as beyond the boundary's scope, handled instead by contained routing that constrains data to sovereign tiers. This is a coherent architectural shift that "uses routing harder" as directed. The strip-map lifecycle is now rigorously designed with operator-boundary isolation, fails-closed semantics on corruption, and secret exclusion, resolving the undesigned persistence risk. Publishing placeholder-impact deltas provides the transparency needed to assess small-model gate depression.

The strongest consideration against adoption is that concentrating responsibility for unstructured PII exclusively on contained routing introduces a single point of failure: if task authors misdeclare data classes, or if the unchanged routing mechanics contain latent bugs, sensitive data egresses without the filter even attempting interception. Additionally, the "budget-safety prerequisite remains closed" status is ambiguous—if unresolved, it blocks release regardless of design improvements. Despite these residual risks, the explicit scoping and verifiable lifecycle satisfy the specific objections raised.

{"stance": "recommend", "summary": "The redraft resolves round-one's false-assurance and lifecycle gaps by explicitly scoping boundary claims to structured data, designing fails-closed map persistence, and measuring gate impact, satisfying the arbiter's criteria for implementation."}

### Position: minimax

- agent: minimax
- model: minimax-m2.1:cloud
- provider: minimax
- stance: recommend
- summary: The coverage table scopes claims verifiably, contained routing architecturally closes the unstructured-PII gap, strip-map lifecycle has fail-closed semantics, and placeholder impact is now measured—collectively resolving round-one defects.

Position formed in an isolated cloud inference run from the neutral round-two brief (Context and Question only): this participant was shown none of this round's other positions and had no repository access. Served via Ollama Cloud. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own output.

**Stance: recommend**

The redrafted 0.7.0 substantially addresses round-one objections through concrete mechanisms rather than aspirational claims.

**Summary:** The coverage table converts an overbroad boundary claim into scoped, testable guarantees; contained routing architecturally closes the unstructured-PII gap by preventing egress rather than claiming impossible filter fidelity; the strip-map lifecycle now has explicit fail-closed semantics; and placeholder-impact deltas are now measured rather than speculated.

**Argument:**

The two core defects from round one were (1) false assurance from an unqualified "containment boundary" claim when regex-only filtering cannot structurally exclude unstructured PII, and (2) an undesigned placeholder-map lifecycle. Both are directly addressed: the coverage table explicitly delimits where the boundary applies (structured PII, secrets) and where it explicitly does not (unstructured), while the contained-routing guarantee ensures that which the filter cannot classify never reaches an exposed tier. This is a sound compositional defense.

The strip-map lifecycle now has operator-boundary semantics with fail-closed resume behavior—a meaningful improvement over the placeholder ambiguity in round one. The placeholder-impact scorecard transforms a speculative concern into an empirical one, which is the right epistemic standard.

The strongest counter-consideration is that this design accepts complexity to paper over a fundamental limitation: the filter cannot classify unstructured PII, so the system must route around its absence. One could argue this reveals the boundary concept as aspirational for the general case, not ready for a sovereignty guarantee. However, the design does not overclaim—it explicitly scopes what the boundary guarantees and what routing must cover. This honesty about architectural limits is precisely what the arbiter requested. The composed guarantees (boundary for what it can catch, routing for what it cannot) are defensible.

{"stance": "recommend", "summary": "The coverage table scopes claims verifiably, contained routing architecturally closes the unstructured-PII gap, strip-map lifecycle has fail-closed semantics, and placeholder impact is now measured—collectively resolving round-one defects."}

## Objections

### Objection: implementer to the record

(unparseable objection response; loop stop: complete — treated as dissent, fail closed)

Transcription note (claude, assembler): in the run's objection round the glm-4.7 participant's reply did not end with the required JSON objections object, and the harness's fail-closed rule recorded the unparseable reply as standing dissent rather than allowing silent convergence. Both of its stance-bearing outputs in this round recommend adoption; the objection above is a protocol-conformance artifact preserved verbatim because recorded dissent is never deleted.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-07
- decision: Unanimously accepted; implement the redrafted 0.7.0 specification as the next release.

This has been an excellent round, rich with opportunity to improve process and protocol and expand capabilities and model families. Along the way we can expect that errors will happen occasionally, as seems to have happened with GLM 4.7 this time. It is important that we never paper this over. The default fail handling of that simple JSON error was a true test that proves the intent is being realized. This AIDR is unanimously accepted.

(Metadata lines above transcribed by claude at the arbiter's explicit confirmation; the decision sentence is distilled from the arbiter's own closing words. The arbitration prose is the arbiter's own, and it addresses the standing objection: the fail-closed handling of the GLM 4.7 JSON error is accepted as correct protocol behavior, never to be papered over.)

## Evidence

- [ROADMAP.md 0.7.0 section](../ROADMAP.md) — the redrafted design under decision (2026-07-07 second revision).
- [AIDR-0003](AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md) — round one: the original design, the 3-3 split, the oppose arguments this redraft answers, and the arbitration directing the redraft.
- `runs/20260707-104319-1MG564/decisions/DR-decide.md` — the round-two contested-decision run record (gpt-oss and glm positions formed under harness isolation; hash-chained events log alongside). Run-local, not tracked.
- `runs/20260707-105241-DUJM8J/decisions/DR-decide.md` — clean-convergence re-run of the same question at the operator's direction (the first run's objection round ended in an unparseable reply, recorded fail-closed as the standing objection above): both agents again recommended, the objection round completed with conforming JSON from both, the decide phase CONVERGED without arbitration, and the integrate phase completed — the full workflow ran end-to-end. Corroborates that the standing objection is a protocol artifact, not substantive dissent. Run-local, not tracked.
- `workspace/aidr-0004-brief.md` — the neutral round-two brief every external participant receives (Context and Question only). Run-local, not tracked.
