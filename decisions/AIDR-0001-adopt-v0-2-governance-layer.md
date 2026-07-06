---
id: AIDR-0001
title: Adopt the v0.2 governance layer (consent, ownership, contest, audit)
status: open
date: 2026-07-06
arbiter: Sam
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

## Objections

## Arbitration

## Evidence

- [GOVERNANCE.md](../GOVERNANCE.md) — the design under decision.
- [Turnfile OWNERSHIP.yaml + SPEC](https://github.com/snapsynapse/turnfile) — source of the ownership-lane and consent mechanics.
- [AIDR SPEC v0.1.0](https://aidr.work/) — source of the record lifecycle, earned claims, and human-only arbitration rule.
- runs/&lt;id&gt;/events.jsonl (hash-chained, v0.2) — will evidence the governance mechanics operating.
