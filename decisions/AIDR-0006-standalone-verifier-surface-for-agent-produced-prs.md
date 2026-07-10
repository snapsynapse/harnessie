---
id: AIDR-0006
title: Standalone verifier surface for agent-produced PRs
status: arbitrated
date: 2026-07-09
arbiter: Sam Rogers
decided: 2026-07-09
tags: [architecture, verifier, ringer, delivery-surface]
---
# AIDR-0006: Standalone verifier surface for agent-produced PRs

## Context

Harnessie's VerificationGate (harness/verify.py) is embedded: coupled to ProofStore, EventLog, Router, and the workflow loop. It cannot be pointed at an arbitrary workspace and a claims list to yield a verdict.

A concrete external demand shape now exists. The Ringer repo's intake queue (5 open outside PRs, zero maintainer review, sole maintainer self-merging his own work in seconds) consists of agent-swarm-produced PRs carrying self-claimed verification the maintainer cannot cheaply reproduce, including security hardening. Ringer's own conviction, exit code zero as the only accepted evidence, applies to its workers but not to its intake. Independent verification of a PR's claims, delivered as a claim-by-claim report with an exit-code contract, addresses the maintainer's actual bottleneck with zero adoption cost. Full pain inventory, constraint set, delivery sequence, and layer design are in the design draft (see Evidence).

Prior art in this repo: AIDR-0003 through AIDR-0005 shaped the 0.7 sovereignty and routing layer; AIDR-0003 in the aidr repo rejected upstreaming AIDR surfaces into Ringer. Nothing here upstreams; the question is what Harnessie itself reshapes.

## Question

Should Harnessie extract its verifier as a standalone surface (a `harnessie verify` subcommand: workspace plus criteria plus optional deterministic checks in, claim-by-claim verdict report plus exit code out, fail closed), targeted first at independent verification of agent-produced PRs with Ringer's queue as proving ground, or should the effort take another shape: a separate minimal tool with no Harnessie dependency, a recipe-only path with no code change, or deferring extraction and hand-running the first verification reports?

## Positions

### Position: Claude Fable 5

- agent: Claude Fable 5
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Extract `harnessie verify` as a standalone subcommand in the existing package, with a flat report directory rather than the full audit chain, and hand-run the first Ringer report before the code lands.

Written first, before any other position existed. This position was formed during the same working session that produced the design draft; it is independent of other participants but not of the evidence gathering.

Extraction into the existing package is the right shape because the verifier's value is its contract, not its packaging: workspace plus claims in, claim-by-claim verdict plus exit code out, fail closed. A separate no-dependency tool optimizes for an adoption story nobody has asked for yet, and it would fork the verifier logic away from the scorecard and parser-version discipline (PARSER_VERSION in harness/verify.py) that make Harnessie's verdicts trustworthy in the first place. Recipe-only fails on the facts: the verifier is not invokable standalone today, so there is nothing for a recipe to call. Pure deferral wastes the demand window the PR queue evidences.

Two scope guards. First, the standalone surface should carry a flat report directory, not the hash-chained EventLog; the audit chain earns its keep inside governed runs, and dragging it into a one-shot CLI raises the extraction cost for no consumer. If a second consumer wants tamper evidence, that is a later, separate decision. Second, sequencing: the first verification report against Ringer's queue (our own PR #4 first) should be produced by hand-driving the existing gate before the subcommand ships. If hand-running reveals the report format is wrong, we learn it before freezing a CLI contract; if it lands with the maintainer, the extraction proceeds with a real consumer instead of a hoped-for one. Deliver value manually within days, extract within the release after.

The honest risk: a standalone verify that skips the orchestrator also skips containment routing, so a PR branch containing hostile content is judged by whatever model the operator points at it. The subcommand must inherit the sandbox for deterministic checks (it already exists at the gate) and should state plainly that verification of untrusted diffs belongs on models you control.

### Position: Verifier Extraction Advocate

- agent: Verifier Extraction Advocate
- model: glm-5:cloud
- provider: zhipu
- stance: recommend
- summary: Extract the `harnessie verify` subcommand because it directly solves the maintainer's verification gap with delivered reports, leverages existing sandboxing infrastructure, and avoids the duplication and maintenance burden of a separate tool or the infeasibility of recipe-only approaches.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "Claude Opus 4 / Anthropic"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `glm-5:cloud`, vendor Zhipu). Prose is verbatim.

The embedded VerificationGate already contains the deterministic-check sandboxing and verifier model logic needed; extraction is a decoupling problem, not a greenfield build. The brief states the gate "cannot be pointed at an arbitrary workspace and a claims list to yield a verdict" — this is the core technical gap. Recipe-only documentation (Alternative 3) fails because there is no existing interface to drive; you cannot document what does not exist. The maintainer ignored prior pitches, so deferring extraction to hand-run reports (Alternative 4) still requires building the extraction surface first — otherwise there is nothing to hand-run. Building a separate minimal tool (Alternative 2) duplicates the sandboxing infrastructure Harnessie already maintains and creates divergence risk between two verification implementations.

The extraction approach delivers immediate value: actual verification reports against Ringer's queue, not proposals. The fail-closed semantics (exit codes 0/1/2) and claim-by-claim verdict report format match what the maintainer needs to adjudicate agent-produced PRs without reproducing claimed test runs. Security hardening PRs requiring adversarial review get the fresh-context verifier model judgment the brief describes. The proving ground is real and waiting — five open PRs, zero maintainer review, burner accounts making untrusted claims. Extraction turns Harnessie's existing verification capability into a deliverable surface that meets the zero-adoption-cost constraint: the maintainer receives reports, not a tool pitch.

### Position: independent-1

- agent: independent-1
- model: gpt-oss:120b-cloud
- provider: openai
- stance: recommend
- summary: Extract the verifier as a `harnessie verify` subcommand, delivering a self-contained CLI that can be run against any PR workspace with deterministic-check input and produce claim-by-claim verdicts.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "gpt-4o-mini"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `gpt-oss:120b-cloud`, vendor OpenAI open-weight). Prose is verbatim.

The Ringer maintainer's pain point is the lack of trustworthy, reproducible evidence for agent-generated PRs; his only accepted signal is a zero exit code from the internal harness, which he cannot obtain for external contributions. Embedding verification inside Harnessie's existing gate already provides deterministic sandboxing, so exposing that capability via a thin CLI adds virtually no engineering overhead while delivering exactly the artifact the maintainer needs: a reproducible report (per-claim pass/fail) and a single exit code that can be scripted into his intake pipeline. Because the subcommand re-uses the same verification model and deterministic checks, it preserves the security guarantees of the original gate and avoids the risk of "untrusted-diff" handling that a completely separate tool would introduce.

Alternative 2 (a brand-new minimal tool) would require re-implementing the deterministic sandbox and re-training or porting the verifier model, incurring duplicated effort and potential divergence in behavior — exactly the kind of risk the brief warns against. Alternative 3 (recipe-only) offers zero development cost but forces the maintainer to manually orchestrate the gate, which defeats the "zero adoption cost" requirement; the manual steps would likely be ignored as previous pitches were. Deferring extraction (Alternative 4) postpones solving the immediate backlog and provides no measurable improvement to the maintainer's workflow, risking continued security-critical PRs sitting unreviewed.

By delivering a `harnessie verify` subcommand, the maintainer can integrate a single command into his CI or local script, automatically fetch a PR branch, run deterministic checks (if desired), and obtain a concise verdict report. This satisfies the brief's constraints: no upstream changes to Ringer, no new licensing complications, and a verifiable surface that can be adopted instantly with zero friction.

### Position: delivery-first

- agent: delivery-first
- model: minimax-m3:cloud
- provider: minimax
- stance: recommend
- summary: Extract a `harnessie verify` subcommand — it is the only option that delivers the reproducible, exit-code-bearing report the Ringer maintainer will actually consume, and reuse of the existing gate keeps the build cost inside what the brief permits.

Transcribed from an isolated position sweep (identical brief, no other positions visible; self-reported identity matched the serving tag). Prose is verbatim.

The brief's constraints collapse the choice faster than it first appears. The maintainer adopts nothing; he reads reports. The shape of the deliverable the brief describes — workspace plus criteria plus optional deterministic checks in, claim-by-claim verdict plus exit code out, fail-closed — is the embedded gate's existing logic re-pointed at a different driver. The engineering is decouple-and-IO against ProofStore, EventLog, Router, and the workflow loop, not new model training, not new sandbox design, not new infra. Reusing the gate's deterministic sandbox and fresh-context verifier is what makes the "delivered reports" path affordable; that economy is the whole reason the brief was framed around an existing gate. A separate minimal tool (Alternative 2) duplicates the deterministic sandboxing and the fresh-context judgment loop for a benefit the maintainer cannot perceive, because he consumes the report, not the binary that emitted it. The license reservation and the prior arbitration that rejected upstreaming mean the verifier's home is Harnessie whether we ship a subcommand or a sibling package — the "no Harnessie dependency" framing buys nothing the constraints care about.

Alternatives 3 and 4 fail on evidence the brief already supplies. A recipe-only path is non-viable on the brief's own terms: the gate "cannot be pointed at an arbitrary workspace and a claims list to yield a verdict." It is coupled by design. No recipe decouples ProofStore, EventLog, Router, and the workflow loop without code change, and the maintainer is not going to do that integration work for us — that is precisely the cost shape the brief says is unacceptable. Deferring extraction and hand-running the first reports (Alternative 4) is strictly worse: hand-runs are one-off judgments that are not re-runnable when the next batch of agent-swarm PRs lands, are not auditable against the deterministic layer, and collapse the trust signal the maintainer most needs — that the same gate produced the verdict that would adjudicate the next claim. A hand-run also forfeits the "exit code zero as the only evidence" discipline Ringer applies to its own workers, because a human judgment is not an exit code and carries no hash of the inputs it consumed.

Extraction does carry one real risk the brief flags honestly: the standalone surface skips the orchestrator's containment routing. The subcommand must inherit the gate's deterministic sandbox for any shell-bearing check, and the verifier-model pass must operate on a review-only, summary-mediated view of the diff — no raw-diff execution, no interpretation of attacker-controlled strings as code, and an explicit allowlist of the surfaces the verifier is permitted to read. With those constraints, the subcommand stands as a single, re-runnable deliverable: a report per PR with a per-claim verdict, an exit code, and a content hash of the workspace and criteria it consumed. Ringer's five-PR queue is the right proving ground — it is live, adversarial, contains the security-hardening cases (credential read deny-lists) that will most stress the trust posture, and the burners in the contributor set make the fail-closed exit code 2 a load-bearing signal rather than a courtesy.

## Objections

### Objection: Claude Fable 5 to Position delivery-first

Filed after reading all sweep positions. delivery-first argues hand-running the first report (Alternative 4's mechanism, which my position folds into sequencing) is strictly worse because a hand-run is not re-runnable and carries no exit code or input hash. The concrete failure mode it ignores runs the other way: freezing a CLI contract before any real consumer has read a report risks shipping the wrong report format, and a CLI contract is expensive to change after publication while a hand-run costs one afternoon. The positions agree on extraction; they conflict on whether the first Ringer report precedes or follows the subcommand landing. The arbiter must resolve the sequencing, not the shape.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-09
- decision: Extract harnessie verify; ship the subcommand first, then generate the Ringer reports with it.

Approved. Build harnessie verify first, then use it to make the reports.

(Metadata lines transcribed by the session agent from the arbiter's dictated choice of Option 2; the prose above is the arbiter's own. This resolves the Claude Fable 5 objection on sequencing: rejected in favor of rerunnable, exit-code-bearing reports from the first delivery.)

## Evidence

- [Design draft: independent verification for agent-produced PRs](../working/ringer-pr-verification-design.md) — pain inventory from the Ringer PR stream (2026-07-05 to 2026-07-09), constraint set, three-layer design, delivery sequence, open questions for this sweep.
- [Ringer PR queue](https://github.com/NateBJones-Projects/ringer/pulls) — the evidenced maintainer bottleneck: agent-produced PRs with self-claimed verification, none maintainer-reviewed.
- [harness/verify.py](../harness/verify.py) — the embedded VerificationGate this decision would extract.
- [AIDR-0003 (aidr repo): Ship a Split Decision recipe for Ringer](https://github.com/snapsynapse/aidr) — prior arbitrated reasoning against upstreaming into Ringer; this record inherits that boundary.
