---
id: AIDR-0001
title: Adopt the v0.2 governance layer (consent, ownership, contest, audit)
status: arbitrated
date: 2026-07-06
decided: 2026-07-06
arbiter: Sam Rogers
tags: [architecture, governance, v0.2]
---
# AIDR-0001: Adopt the v0.2 governance layer (consent, ownership, contest, audit)

## Context

Harnessie v0.1 ships an orchestrator/worker/verifier harness with verification gates, routing, and a layered injection defense. The operator has directed v0.2 toward adversarial collaboration and evals as foundational principles, importing lessons from Turnfile (consent-based peer coordination, ownership lanes, maintainer authority) and AIDR (independent positions, preserved dissent, human-only arbitration, earned claims). The proposed design is specified in GOVERNANCE.md: consent-gated worker phases, tool-layer ownership lanes, adversarial contested phases emitting AIDR-shaped decision records, a hash-chained events log with an audit CLI, and red-then-green eval scenarios as the merge discipline. This displaces the previously roadmapped 0.2.0 theme (Linux portability, live-endpoint evals) to 0.3.0.

## Question

Should Harnessie v0.2 implement the GOVERNANCE.md governance layer (consent contract, ownership lanes, contested phases with human-only arbitration, hash-chained audit), deferring the portability milestone to 0.3?

## Positions

### Position: claude

- agent: claude
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Implement the governance layer now; it converts the harness's core differentiators from conventions into code-enforced guarantees, and portability compounds better on top of a governed core.

Written independently; no other positions existed at authoring time.

The v0.1 security posture already rests on the principle that guarantees live in code. Consent, ownership, and arbitration are today the largest surfaces where multi-agent systems still rely on prompt-level convention; enforcing them at the registry, loop, and runner layers is the same move that made v0.1's permissioning credible, applied to governance. The imported mechanics are not speculative: Turnfile's ownership lanes and apply-or-counter review, and AIDR's record lifecycle with structurally earned claims, both shipped and survived real multi-agent sessions. Sequencing governance before portability is lower-risk than the reverse — a Linux backend added later inherits the governed core unchanged, whereas retrofitting consent and ownership onto a widely-deployed harness would break workflow compatibility. Risks acknowledged: scope growth in a solo-operated repo, and per-file ownership having an honest interpreter-write blind spot that only sandbox-profile work can close; both are recorded in GOVERNANCE.md rather than papered over.

### Position: qwen

- agent: qwen
- model: qwen3.6:35b-mlx
- provider: alibaba
- stance: recommend
- summary: The implementation of a robust governance layer prioritizing safety, accountability, and verifiable integrity over portability is the correct strategic choice for an agent orchestration system.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The shift toward adversarial collaboration and strict ownership lanes addresses critical risks inherent in multi-agent systems, specifically regarding prompt injection and unauthorized state modification. By enforcing consent-gated phases and file-level ownership, Harnessie v0.2 establishes a necessary foundation of trust and auditability that is difficult to retrofit later. The inclusion of human-only arbitration and hash-chained logs ensures that failures or disputes are traceable and resolvable, which is essential for any system handling complex, potentially sensitive tasks.

While Linux portability is a valuable engineering goal, it is a non-functional requirement compared to the functional integrity provided by the new governance model. A portable but insecure or unaccountable agent harness poses a higher risk than an unportable but secure one. Deferring portability allows the team to solidify the core logic and safety mechanisms without the distraction of environment-specific constraints, ensuring that the "brain-agnostic" nature of the system is backed by reliable operational guarantees.

The primary counter-argument involves the delay in broader deployment capabilities due to the lack of Linux support. However, this risk is mitigated by the fact that the core logic remains platform-agnostic and the tests pass deterministically. The deferred milestone can be addressed in a subsequent release without compromising the architectural integrity established in v0.2, making this a prudent trade-off for long-term stability and security.

### Position: gemma

- agent: gemma
- model: gemma4:31b-mlx
- provider: google
- stance: recommend
- summary: Prioritizing structural governance over portability establishes a secure, verifiable foundation necessary for safe multi-agent orchestration.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The implementation of consent contracts, ownership lanes, and tamper-evident logging transforms the harness from a simple execution engine into a robust governance framework. In multi-agent systems, the risk of cascading failures or unauthorized state mutation is high; by enforcing "earned claims" and human-only arbitration for contested phases, the system ensures that autonomy does not lead to instability. This architectural rigor is far more critical for early-stage reliability than environment portability.

The primary trade-off is the delay of Linux portability and live-endpoint evals, which limits immediate deployment flexibility. However, deploying a portable system that lacks internal governance would merely scale the risk of unmanaged agent interactions. It is logically sound to solve the "how it behaves" problem before solving the "where it runs" problem.

Future releases should now prioritize the deferred portability milestones to ensure this governance layer can be validated across diverse environments.

### Position: gpt-oss

- agent: gpt-oss
- model: gpt-oss:20b
- provider: openai
- stance: recommend
- summary: The governance layer should have been implemented in v0.2, with the Linux‑portability milestone deferred to a later release.

Position formed in an isolated local inference run from a neutral brief (record Context and Question only): this participant was shown no other position and had no repository access. Transcribed verbatim by claude (assembler); stance and summary lifted from the participant's own header lines.

The primary benefit of adding consent contracts, ownership lanes, contested phases and a hash‑chained audit is that it establishes safety, accountability, and human oversight at every stage of multi‑agent interaction—exactly what adversarial collaboration demands. By locking side‑effecting tools until explicit acceptance and providing an auditable trail, the system mitigates misuse risks while preserving the integrity of independent positions, which are core to AIDR’s philosophy. The fact that 115 tests and all deterministic evals pass indicates that the added complexity does not destabilize the platform.

The main downside is that portability is a tangible feature many users expect; delaying it may hinder adoption or delay integration into existing workflows. Additionally, the governance layer introduces extra engineering overhead—more code paths, stricter tool permissions, and human‑only arbitration—that could slow future development cycles if not carefully managed.

To balance these concerns, proceed with the governance implementation now but commit to a clear roadmap that reintroduces Linux portability in v0.3 or 0.4, ensuring adequate performance testing and documentation of the human arbitration process so users can understand how decisions are made and audited.

## Objections

## Arbitration

- decided_by: Sam
- date: 2026-07-06
- decision: The v0.2 governance-layer direction is ratified as recorded.

Arbitrated by Sam after independent positions were gathered from four providers (anthropic, alibaba, google, openai) at his direction; all four recommend, and no objections were filed. Sam's exact words, given in the decision prompt after reviewing the stance matrix:

> Sam: "I have arbitrated. please ratify as needed"

Transcribed by claude at the arbiter's direction; the decision is the arbiter's, the transcription is mechanical.

This is exactly the kind of input I wanted to see. I look forward to expanding the models providing input, the model-family base, and extending portability to Linux soon.

## Evidence

- [GOVERNANCE.md](../GOVERNANCE.md) — the design under decision.
- [Turnfile OWNERSHIP.yaml + SPEC](https://github.com/snapsynapse/turnfile) — source of the ownership-lane and consent mechanics.
- [AIDR SPEC v0.1.0](https://aidr.work/) — source of the record lifecycle, earned claims, and human-only arbitration rule.
- runs/&lt;id&gt;/events.jsonl (hash-chained, v0.2) — will evidence the governance mechanics operating.
