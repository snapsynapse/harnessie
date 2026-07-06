---
id: AIDR-0002
title: Theme v0.3 as aggregated-intelligence tenets plus agent triage
status: open
date: 2026-07-06
arbiter: Sam
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

## Objections

## Arbitration

## Evidence

- [GOVERNANCE.md §7](../GOVERNANCE.md) — the tenets-to-mechanics mapping under decision.
- decisions/AIDR-0001-adopt-v0-2-governance-layer.md — the prior direction record this builds on (also open).
- LocalBrain load-bearing frame "Mission as Bullseye, Vehicles as Routes" (2026-05-25) — source of the tenets.
- The operator's vault triage SOP — source of the maintenance-agent pattern and its never-delete / approval rules.
