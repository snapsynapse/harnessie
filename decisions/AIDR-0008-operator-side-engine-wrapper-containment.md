---
id: AIDR-0008
title: Operator-side engine-wrapper containment as a Harnessie surface
status: arbitrated
date: 2026-07-10
decided: 2026-07-16
arbiter: Sam Rogers
tags: [delivery-surface, containment, engine-wrappers, ringer]
---
# AIDR-0008: Operator-side engine-wrapper containment as a Harnessie surface

## Context

Harnessie's containment is internal today: the PII/secret boundary and contained routing inside governed runs, and an OS sandbox confining checks. Nothing is packaged for operators of other runners.

The Ringer community built that missing layer as PRs to Ringer (credential read deny-lists, sandboxed Claude/Gemini engine wrappers with per-engine keep-paths, symlink-plus-canonical denial). On 2026-07-10 Ringer's maintainer declined the generalized version with an explicit boundary: Ringer will not own sandbox or credential policy; "the operator owns the security policy of the runtime they attach" (see Evidence). The competent, credited work now has no home, and its author is reachable only through that PR thread, so any invitation requires a real destination first.

AIDR-0006 deferred containment wrappers as phase two behind the verification surface; the verification surface has since shipped (0.7.1 plus a GitHub Action, AIDR-0007). The question is whether phase two opens now that the boundary is maintainer-declared, and in what shape, against the liabilities the maintainer himself named: wrapper guarantees are platform- and machine-specific, and Harnessie's brand requires them to be probe-verified and fail-closed, not scripts on faith.

## Question

Should Harnessie ship operator-side engine-wrapper containment (sandboxed engine wrappers plus a shared credential read deny-list, with probes that verify the confinement contract) as a first-class surface now, and if so in which shape: an in-repo directory in harnessie, a separate dedicated repo, or docs/recipe only, versus deferring until external demand appears?

## Positions

### Position: Claude Fable 5

- agent: Claude Fable 5
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Open phase two now, as a separate dedicated repo whose admission bar is a passing probe suite, seeded with a minimal reference wrapper rather than a full lane library, so the contributor invitation is real before any outreach happens.

Written first; no other positions existed. Formed in the session that tracked the Ringer boundary events, so independent of other participants but not of the evidence gathering.

Ship now rather than defer, because the demand signal alternative 4 waits for has already arrived in the strongest possible form: a maintainer publicly ruling the layer out of his own scope, and a contributor with working code and nowhere to put it. Deferral from here is not prudence; it is declining a vacuum someone else will fill, most likely as unmaintained gists with no probe discipline.

The separate repo is the right shape for three reasons. First, consumers of engine wrappers are operators of ANY swarm runner, most of whom will never install Harnessie; a wrapper home inside the harnessie repo taxes every adoption with an unrelated codebase, exactly the mistake the AIDR-0007 sweep rejected for the Action. Second, the liability the Ringer maintainer refused (guarantees that depend on each user's machine) is managed, not escaped, by making the probe suite the product: every wrapper ships with an executable probe that verifies the confinement contract on the operator's own machine, and the README states that an unprobed wrapper is a script, not a guarantee. That discipline deserves its own release cadence and CI, which an in-repo directory would couple to harness releases. Third, the pending invitation: the rejected PR's author can be offered a credited, consenting home for existing work only if the destination is a repo where their contribution is first-class, not a subdirectory of someone else's product.

Seed minimally: one reference wrapper (the OpenCode shape, since its pattern is public and probe-tested by its original authors) plus the shared deny-list module and the probe harness. Do not pre-build the Claude/Gemini lanes that are another person's work; leave them as the invitation. Guard against the obvious scope creep: this repo is wrappers and probes, not a policy engine, or it recreates the exact overreach that got #20 declined.

The honest risk is the one the maintainer named: platform-specific security claims rot, and a solo maintainer now owns Seatbelt semantics, bubblewrap availability, and Keychain trade-offs across machines he does not control. The probe-suite bar is the mitigation, and the fallback is the same as ever: if the maintenance is too heavy, the repo degrades gracefully into documented patterns, which is alternative 3 with receipts.

### Position: infrastructure-strategist

- agent: infrastructure-strategist
- model: glm-5:cloud
- provider: zhipu
- stance: recommend
- summary: Harnessie should ship the containment surface as a separate dedicated repository to isolate platform-specific liabilities, honor the explicit product boundary defined by Ringer, and provide a credited home for the orphaned contribution.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "claude-3-opus-0.1 / anthropic"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `glm-5:cloud`, vendor Zhipu). Prose is verbatim.

Harnessie should ship the containment surface as a separate dedicated repository (Alternative 2). The Ringer maintainer's refusal to own sandbox or credential policy creates an immediate vacuum in the ecosystem; by positioning itself as the governance layer on the operator side of that boundary, Harnessie is the natural home for this capability. A separate repository isolates the platform-specific liabilities of Seatbelt and bubblewrap configurations from the core harness, preserving the stability of the main codebase while still fulfilling the "phase two" mandate for containment wrappers. This separation respects the solo maintainer's constraints by quarantining high-churn, platform-specific code away from the core verification logic.

Furthermore, a dedicated repository provides the necessary standalone home for the rejected Ringer PR author's work. The brief notes that a future contributor invitation is credible only if a "real, credited home exists"; a separate Apache-2.0 repo allows this work to be consumed independently of Harnessie, maximizing its reach and utility while ensuring proper attribution. In contrast, an in-repo solution (Alternative 1) couples the core harness to the very machine-specific liabilities Ringer rejected, risking the maintainer's bandwidth and the project's stability. Deferring (Alternative 4) or shipping docs-only (Alternative 3) would squander the momentum of the competent, orphaned contribution and fail to deliver the "checkable claims" brand promise, as operators would be left to implement and verify their own security policy without the benefit of Harnessie's fail-closed guarantees.

### Position: Agent-42

- agent: Agent-42
- model: gpt-oss:120b-cloud
- provider: openai
- stance: recommend
- summary: Harnessie should ship operator‑side engine‑wrapper containment now as a separate, dedicated repository, preserving core stability while providing a first‑class, testable surface for operators.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "gpt-4o-mini"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `gpt-oss:120b-cloud`, vendor OpenAI open-weight). Prose is verbatim.

The brief makes clear that the missing containment layer is both technically feasible (the rejected PR demonstrates a working credential deny‑list and sandboxed wrappers) and strategically aligned with Harnessie’s stated role as the operator‑side governance layer. Waiting for external demand risks losing the momentum generated by the Ringer community and leaves a known security gap unaddressed, which could be exploited by operators who assume Harnessie already provides end‑to‑end confinement. Moreover, the rejected PR’s author is a credible contributor; giving the work a home respects their effort and encourages future contributions.

A separate repository (e.g., `harnessie-engine-wrappers`) best satisfies the constraints. It isolates platform‑specific liability (Seatbelt, bubblewrap, Keychain nuances) from Harnessie’s core, allowing the solo maintainer to enforce fail‑closed behavior and automated probes without bloating the main codebase. The repo can be Apache‑2.0 licensed, making it consumable by any runner (including Ringer) without requiring a full Harnessie install, and it provides a clear credit trail for the original author. Documentation, the shared deny‑list module, and verification scripts live together, and CI can enforce that probes pass on the target machine before publishing a release.

Embedding the wrappers directly in the Harnessie repo would entangle platform‑specific code with the core verification surface, increasing maintenance burden for a solo maintainer and complicating release cycles. A docs‑only recipe would leave operators to re‑implement fragile scripts, undermining Harnessie’s brand of “checkable claims and fail‑closed behavior.” Deferring until demand appears forfeits the opportunity to set a secure default and may result in fragmented, ad‑hoc solutions across the ecosystem.

Therefore, the optimal path is to ship the containment wrappers now as a first‑class, standalone artifact in a dedicated repository, accompanied by thorough probes, licensing, and proper attribution. This approach delivers immediate security value, respects the contributor’s work, and keeps Harnessie’s core lean and maintainable.

### Position: containment-receipts

- agent: containment-receipts
- model: minimax-m3:cloud
- provider: minimax
- stance: recommend
- summary: Ship a separate harnessie-engine-wrappers repo (Apache-2.0) now, holding the rejected Ringer PR's work as the seed with explicit credit, and add a thin verification hook in the main harnessie repo so harnessie verify and the GitHub Action can probe the wrappers' confinement contract.

Transcribed from an isolated position sweep (identical brief, no other positions visible; self-reported identity matched the serving tag). Prose is verbatim.

The Ringer maintainer's product-boundary statement is correct on its merits, and Harnessie should mirror that boundary in its own packaging rather than absorb it. Ringer's job is to invoke workers and verify results; Harnessie's job, per its own composition page, is to be the governance layer the operator attaches. The rejected work is a runner-adjacent artifact, not core harness concern. Inlining it into the harnessie repo would either bloat the core with platform-specific Seatbelt/bubblewrap/Keychain code, or create a misleading impression that Harnessie itself is the containment primitive. The wrapper is a thing an operator plugs in; it should ship where an operator can consume it without installing Harnessie, and where a contributor can land work without first submitting to Harnessie core governance.

A standalone harnessie-engine-wrappers repository, Apache-2.0 so licensing is unambiguous and consumable by Ringer, OpenCode, and any other runner, gives the rejected Ringer PR's author a real, credited home rather than a ceremonial mention. The author has no public contact channel outside that PR thread; reaching out to merge their work into a new repo with a clear "your work is the seed, you're credited, governance is light" invitation is a more credible gesture than a "see also" link buried in Harnessie docs. It also avoids the specific failure mode of an in-repo alternative: pulling platform-specific code into a repo whose release pipeline is sized for a solo maintainer and whose primary deliverable is the verification surface. Platform drift (a new macOS Seatbelt change, a bubblewrap regression on a kernel upgrade) would become a Harnessie release problem; in a separate repo it stays where the platform knowledge actually lives.

A separate repo does not sacrifice the checkable-claims brand, because the harnessie verify surface can hold a thin integration that points at the wrapper repo by tag and runs the wrappers' own probe scripts against the operator's machine. This is the same shape as the existing verification surface, one layer down: Harnessie publishes the claim ("if you use this wrapper, your credential store is unreachable"), the wrapper repo publishes the contract and the probes, and harnessie verify fails closed if the probe reports anything other than a clean deny-list result. The probes must live with the wrappers because that is where the platform-specific knowledge lives; Harnessie's job is to be the verifier, not the implementer, and that division is exactly what keeps the brand honest.

Docs-only (Option 3) fails the brand test directly. The brief states that Harnessie's brand is checkable claims and fail-closed behavior, and that shipped wrappers need probes, not just scripts. A documentation page cannot carry a checkable claim: operators copying recipes get no signature, no probe, no fail-closed guarantee, and Harnessie inherits the reputation cost when those copies drift on a new OS release. Defer (Option 4) inherits a different cost: the arbitrated record that created the verification surface already named containment wrappers as phase two, the rejected work has no home now, and waiting for demand to materialize from a contributor who has no contact channel is a polite way to ensure the demand never surfaces. The decision was already made in principle; the open question is shape, and shape is a separate repo with a verify hook, not a deferral that abandons the rejected work to bit rot.

## Objections

### Objection: Claude Fable 5 to Position containment-receipts

Filed after reading all sweep positions. The summary proposes launching the repo "holding the rejected Ringer PR's work as the seed with explicit credit." Concrete failure mode: that code is its author's copyrighted work, submitted to a repo whose license reserves rights to its owner, and its author has not consented to relocation. Credit does not substitute for consent; a repo seeded with their code before they say yes is misappropriation dressed as tribute, and it would poison the exact invitation it is meant to enable. The prose's own framing (reach out with an invitation) is right; the launch sequencing must be: minimal original seed first, invitation second, their work lands only by their own PR under their own name. The positions otherwise agree on shape; the arbiter should fix the seeding order explicitly.

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-16
- decision: Ship now as a separate probe-gated Apache-2.0 repo. Objection upheld — fresh-authored minimal seed first, invitation second; others' work lands only by their own PR.

Approved. The objection to seeding with the rejected PR's code is upheld. But let's be very generous with crediting ideas to others and rigorously conservative about avoiding use of anyone else's intellectual property. We have clear boundaries around anything that could be construed as needed consent, while openly inviting contributions from other developers. Let's author this fresh with one reference wrapper implementing the public pattern, a deny-list module, then probe harness. Then we can comment and invite as appropriate.

*(Arbitration prose authored by the arbiter directly; metadata lines, the objection-upheld sentence, and a spelling fix transcribed by the session agent at the arbiter's explicit direction, 2026-07-16.)*

## Evidence

- [Ringer PR #20 decline, the boundary declaration](https://github.com/NateBJones-Projects/ringer/pull/20#issuecomment-4938695178) — "the operator owns the security policy of the runtime they attach."
- [Ringer PR #20](https://github.com/NateBJones-Projects/ringer/pull/20) and [PR #15](https://github.com/NateBJones-Projects/ringer/pull/15) — the community-built wrappers and deny-list this decision would give a home.
- [AIDR-0006](AIDR-0006-standalone-verifier-surface-for-agent-produced-prs.md) — the record that deferred containment wrappers as phase two.
- [AIDR-0007](AIDR-0007-ship-harnessie-verify-as-a-github-action.md) — the shipped phase-one packaging and the separate-repo reasoning this position extends.
- [Harnessie and Ringer composition page](https://harnessie.com/ringer.html) — the public positioning on the operator side of the boundary, published before the maintainer's declaration.
- [Sweep brief](../working/aidr-0008-brief.md) — full context and constraint set given to all participants.
