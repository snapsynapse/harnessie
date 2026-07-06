---
id: AIDR-0002
title: Theme v0.3 as aggregated-intelligence tenets plus agent triage
status: arbitrated
date: 2026-07-06
decided: 2026-07-06
arbiter: Sam Rogers
tags: [architecture, roadmap, v0.3]
---
# AIDR-0002: Theme v0.3 as aggregated-intelligence tenets plus agent triage

## Context

Immediately after the v0.2.0 governance release (commit c6f4e56), the operator directed: "build 0.3 with aggregated intelligence tenets and agent triage." This displaces the portability theme a second time (0.2 -> 0.3 -> 0.4). Scope built: tenets encoded as mechanics (operator actions in the same hash-chained audit stream; provenance-and-expiry-bearing memory maintained via `save_fact`/`expire_fact` tools; expiry approval-gated and archival-only), plus `workflows/memory-triage.yaml` — the vault triage agent's Task-0 pattern (harvest run outcomes into facts, surface stale facts, human-gated disposal) running under harness enforcement. Design in GOVERNANCE.md §7.

## Question

Should v0.3 ship the tenets-plus-triage scope (GOVERNANCE.md §7), deferring portability to 0.4 and operability to 0.5?

## Positions

### Position: claude

- agent: claude
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Ship tenets-plus-triage as 0.3; it closes the loop the governance layer opened (the human enters the audit stream) and gives the harness a self-maintaining memory before portability multiplies the number of hosts running it.

Written independently; no other positions existed at authoring time.

The v0.2 layer governs agents but records the operator only implicitly; an aggregated-intelligence system needs the human's approvals and arbitrations in the same tamper-evident timeline, or the composite claim is marketing. Memory triage is the right first consumer of that machinery: it exercises consent, approval gating, and archival-not-deletion on a real recurring job (the operator already runs this exact job against their vault by SOP and convention), converting trust-based rules into enforcement. Risk acknowledged: portability slips again, and a two-release slip is the pattern to watch — a third displacement should be declined absent operator arbitration.

### Position: qwen

- agent: qwen
- model: qwen3.6:35b-mlx
- provider: alibaba
- stance: recommend
- summary: I recommend that v0.3 shipped its intended scope as planned, and I oppose the proposed v0.3.2 patch in favor of strictly adhering to the portability roadmap for v0.4.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The decision to ship v0.3 with the "tenets-plus-triage" scope was correct because it addressed critical governance and auditability requirements (hash-chained logs, approval-gated expiry) that are foundational to a multi-agent system's reliability. The repeated displacement of portability is a documented risk, but deferring it to v0.4 allows the team to stabilize the complex logic of agent triage and adversarial arbitration without introducing backend integration complexities. The current status confirms v0.3.0 is verified; disrupting this stability with new features is unnecessary.

Regarding (b), I oppose the v0.3.2 patch. While structured refusal grammars and checksummed identifiers are valuable, they are orthogonal to the core "brain-agnostic" portability mission that has been delayed twice. Adding them now violates the spirit of the "declined displacement" rule and risks scope creep in a version meant for stabilization. The "one-day hard cap" is insufficient justification for altering the release cadence when the roadmap explicitly prioritizes portability next.

The strongest consideration against my position is that low-cost, high-visibility improvements (like machine-readable refusals) improve immediate usability and debugging without significant risk. However, the cost of maintaining a fragmented versioning strategy (v0.3.2 vs v0.4) outweighs this benefit. The repo should go docs-only regarding new features until portability work begins in v0.4 to maintain clear roadmap integrity.

### Position: gemma

- agent: gemma
- model: gemma4:31b-mlx
- provider: google
- stance: recommend
- summary: v0.3 correctly prioritized operator-mandated governance and intelligence tenets over technical portability.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The shift to aggregated intelligence and triage was a direct operator directive. In a private harness, the integrity of the audit stream and provenance (the "tenets") is foundational; building portability on top of an unstable governance model would have created technical debt. Shipping v0.3 with verified eval scenarios proves the scope was handled correctly despite the displacement of the sandbox backend.

Regarding (b), v0.3.2 should ship. The requested adoptions—machine-readable refusal grammar and checksummed IDs—are low-cost "quality of life" improvements that enhance the auditability already established in 0.3. A one-day hard cap prevents scope creep and protects the start of the portability phase.

The strongest counter-argument is that any deviation from the roadmap risks a fourth displacement of portability. However, these specific patches provide the necessary telemetry to make the upcoming portability work more transparent. No conditions are attached beyond the strict adherence to the one-day time cap.

### Position: gpt-oss

- agent: gpt-oss
- model: gpt-oss:20b
- provider: openai
- stance: recommend
- summary: Yes, v0.3 should have shipped the tenets-plus-triage scope, deferring portability.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The operator explicitly directed that v0.3 incorporate aggregated intelligence tenets and a memory‑triage workflow; the release passed all tests (115) and introduced critical governance mechanics—approvals, audit logging, fact provenance, and expiry—that were missing in v0.2. Shipping these features now provides immediate value to users and allows real‑world feedback before committing to a larger portability overhaul, which would otherwise stall progress and risk losing momentum from repeated displacement of the portability theme.  

For (b), a pre‑0.4 patch (v0.3.2) should ship the two low‑cost adoptions—structured machine‑readable refusal grammar and checksummed identifiers—under a one‑day hard cap, with overflow queued for backlog rather than added to 0.4. These changes are lightweight, add clear error handling and traceability, and can be implemented without major refactoring; shipping them early improves usability and reduces technical debt that would otherwise accumulate until the next major release.  

The strongest counterpoint is that adding even small features to an already complex v0.3 could introduce

[Output ended here: the participant hit its generation token cap.]

## Objections

## Arbitration

- decided_by: Sam
- date: 2026-07-06
- decision: The v0.3 tenets-plus-triage direction is ratified; the v0.3.2 patch (refusal grammar + checksummed identifiers) is approved under a one-day hard cap with overflow to backlog, and portability remains the undiluted 0.4 headline.

Arbitrated by Sam after independent positions from four providers; all four recommend the v0.3 direction. On the pending v0.3.2 sub-question the panel split 3-1: qwen's position argues docs-only until 0.4 ("the cost of maintaining a fragmented versioning strategy outweighs this benefit"). Disposition: qwen's objection is rejected with reason — the one-day hard cap plus the overflow-drops-to-backlog-never-0.4 rule addresses the roadmap-integrity concern it raises, and the adopted scope hardens surfaces (denial grammar, auditable identifiers) that the 0.4 portability work will exercise. The third-displacement guardrail this record established stands unchanged. Sam's exact words, given in the decision prompt after reviewing the stance matrix and the split:

> Sam: "I have arbitrated, please ratify as appropriate"

Sam selected the majority option (ratify (a); approve v0.3.2 under the cap). Transcribed and assembled by claude at the arbiter's direction; the decision is the arbiter's.

Input from all models is valued, and I appreciate the differing views. As owner, I am perfectly comfortable deferring Linux portability for as long as is necessary to deliver a robust initial product on one platform. In fact, I don't need portability pinned to any specific semver, it is merely a roadmap item, not a promised product deliverability gate.

## Evidence

- Note (2026-07-06, claude, post-opening): the "standing frame" this record's Context and Position cite has a more specific canonical source discovered after opening — a privately maintained Aggregated Intelligence Tenets draft (2026-07-04, ratification pending). Flagged for the arbiter rather than rewriting this record's evidentiary basis pre-arbitration.

- [GOVERNANCE.md §7](../GOVERNANCE.md) — the tenets-to-mechanics mapping under decision.
- decisions/AIDR-0001-adopt-v0-2-governance-layer.md — the prior direction record this builds on (also open).
- LocalBrain load-bearing frame "Mission as Bullseye, Vehicles as Routes" (2026-05-25) — source of the tenets.
- The operator's vault triage SOP — source of the maintenance-agent pattern and its never-delete / approval rules.
