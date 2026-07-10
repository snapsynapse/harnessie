---
id: AIDR-0007
title: Ship harnessie verify as a GitHub Action
status: arbitrated
date: 2026-07-10
arbiter: Sam Rogers
decided: 2026-07-09
tags: [delivery-surface, verify, github-action, distribution]
---
# AIDR-0007: Ship harnessie verify as a GitHub Action

## Context

`harnessie verify` (AIDR-0006, shipped 0.7.1) verifies a workspace against a claims file with a fail-closed exit contract. It proved out against a real PR queue, but consuming it still requires a local install and hand-built inputs.

A market sweep (2026-07-10) found every named AI PR tool is a static reader that comments on diffs; none executes a PR's claimed checks or adjudicates its body as claims. The verification category is unoccupied. The cheapest credible occupation is CI-native packaging: a GitHub Action that runs in the consuming repo's own compute with the operator's own model endpoint, posts a claim-by-claim summary, and gates merge on the exit code. A hosted App is explicitly out of scope: executing strangers' untrusted PR code is the expensive security problem, and hosting contradicts the sovereignty posture.

The design draft (see Evidence) fixes the contract: inputs, auto-derived-claims provenance, safe-trigger documentation (`pull_request` only), sandbox fail-closed inheritance, structured-table-not-prose output back to the PR, and acceptance criteria including a five-minute stranger install and an end-to-end dogfood PR.

## Question

Should harnessie verify ship as a composite GitHub Action in a new dedicated public repo (`snapsynapse/harnessie-verify-action`, Marketplace-listable, pinned harnessie version, separate release cadence), or should the packaging take another shape: the Action living inside the harnessie repo, a reusable workflow instead of an Action, or no packaging beyond a documented workflow recipe in docs?

## Positions

### Position: Claude Fable 5

- agent: Claude Fable 5
- model: claude-fable-5
- provider: anthropic
- stance: recommend
- summary: Ship it as a composite Action in the dedicated repo, with the docs/workflow recipe published simultaneously as the zero-trust on-ramp, and hold v1 scope to the design draft's non-goals.

Written first; no other positions existed. Formed in the same session that produced the design draft, so independent of other participants but not of the market sweep.

The dedicated repo is the only alternative that gets Marketplace distribution, and distribution is the entire point of packaging: the library already works. Marketplace requires the action at repo root, so alternative 2 (inside harnessie) forfeits the listing to save one repo's maintenance, a bad trade when the action is a thin composite whose CI is a fixture test against a pinned harnessie version. Alternative 3 (reusable workflow) is the same maintenance with materially worse discoverability. Alternative 4 (recipe only) is not nothing, and it should ship regardless as documentation, but a YAML recipe a stranger must assemble is a tutorial, not a product; the five-minute acceptance criterion fails.

Two scope guards worth holding under pressure. First, `criteria: auto` will tempt v2 intelligence (LLM claim extraction from PR bodies). Resist it: auto mode should stay boilerplate-stripping with a provenance stamp, because the moment extraction is smart, the action is grading claims it authored, which is the exact self-dealing the tool exists to refuse. Second, the exit-2 default (`fail-on-cannot-verify: true`) will generate issues asking for neutral defaults. The default is the brand; the relaxation flag already exists for operators who want advisory mode.

The honest risk is maintenance surface: a second public repo, Marketplace review, and a pinned-version treadmill, owned by a solo maintainer. The mitigation is in the design: composite action (no JS/Docker build), offline fixture CI, and the harness itself unchanged. If the treadmill still proves too heavy, the recipe path remains as the fallback that never breaks.

### Position: Infrastructure Pragmatist

- agent: Infrastructure Pragmatist
- model: glm-5:cloud
- provider: zhipu
- stance: recommend
- summary: Ship the composite GitHub Action in a new dedicated public repo to secure Marketplace discoverability for an unoccupied verification category while maintaining release-cadence isolation between the thin action wrapper and the core harnessie tool.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "claude-sonnet-4 / Anthropic"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `glm-5:cloud`, vendor Zhipu). Prose is verbatim.

The verification category is empty. Every named competitor in the sweep reads static diffs and comments; none executes claimed checks or adjudicates PR bodies as claims. First-mover advantage in an unoccupied category demands discoverability, and GitHub Marketplace is the canonical discovery surface for CI components. The brief's explicit note that Marketplace listing requires an action at the root of its own public repo is not incidental: it signals that Marketplace presence is a distribution objective, not a nice-to-have. A dedicated repo unlocks that surface; embedding the action inside the harnessie repo forecloses it.

The separate release cadence is a feature, not overhead. The action pins a tested harnessie version and CI-validates against a fixture workspace with a mock model. This insulation protects action consumers from core harnessie churn while the solo maintainer iterates on the verification engine. Version coupling (Alternative 2) creates implicit synchronization risk: a core harnessie release could break the action's pinned expectation, forcing either premature action releases or stale core pinning in a single-repo setup. The dedicated repo model makes the contract explicit: action releases are deliberate, version-pinned, and independently versioned.

A reusable workflow (Alternative 3) fails the acceptance criteria's friction target. Reusable workflows require the consumer to reference a remote workflow file, understand the caller syntax, and often duplicate secret configuration across repositories. The acceptance bar, a stranger reaching merge-gating in under five minutes with one workflow file, is best met by a Marketplace-listed action with a single `uses:` stanza and documented secret wiring. A docs-only recipe (Alternative 4) fails even more severely: copy-paste drift, no automated updates, no discoverability signal, and no CI enforcement of the documented path.

The solo maintainer constraint argues for the thinnest possible action surface. A composite action wrapping `harnessie verify` with staged inputs, secrets plumbing, and structured output formatting is precisely that thin layer. The dedicated repo adds negligible maintenance burden beyond the action itself: no backend, no hosted service, no GitHub App. The security posture (fail-closed on missing sandbox, explicit `pull_request` trigger documentation) is clearer when isolated in an action-focused README rather than buried in a broader tooling repo. Ship the dedicated repo.

### Position: AI_Arbiter_01

- agent: AI_Arbiter_01
- model: gpt-oss:120b-cloud
- provider: openai
- stance: recommend
- summary: Ship harnessie verify as a composite GitHub Action in a new dedicated public repository.

Transcribed from an isolated position sweep (identical brief, no other positions visible). The model self-reported as "gpt-4o-mini"; metadata above is corrected to the serving endpoint's tag (Ollama Cloud `gpt-oss:120b-cloud`, vendor OpenAI open-weight). Prose is verbatim.

The verification niche is currently empty, and a Marketplace-listable Action offers the most discoverable entry point for adopters who need a drop-in gate on PR merges. A dedicated repo decouples the Action's release cadence from harnessie's core library, allowing rapid iteration on CI-specific concerns (e.g., runner compatibility, artifact handling) without forcing a new harnessie version on downstream users. This separation also keeps the core repo lean, avoiding the extra CI load and Marketplace-listing requirements that could slow down core development.

Security considerations favor a separate repo because the Action's workflow runs only on the consumer's CI; the Action itself merely invokes the already-sandboxed harnessie binary. Hosting it elsewhere eliminates any perception that the core harnessie repo is a distribution channel for executable code, reducing attack surface and simplifying supply-chain audits. Moreover, a dedicated repo can enforce the "pull_request only, never pull_request_target" policy in its own README and CI, providing a clear, auditable boundary that a reusable workflow inside the core repo might blur.

While a reusable workflow is simpler to author, it lacks Marketplace visibility and cannot be version-pinned independently of harnessie releases, leading to brittle downstream pipelines. Publishing only a documented recipe would place the burden of correct packaging on every user, increasing friction and likely limiting adoption. Therefore, the composite Action in a new public repo best balances discoverability, security, maintainability, and the solo maintainer's capacity to ship a stable, version-pinned artifact.

### Position: marketplace-distribution

- agent: marketplace-distribution
- model: minimax-m3:cloud
- provider: minimax
- stance: recommend
- summary: Ship as a composite GitHub Action in a new dedicated public repo to capture the unoccupied verification category through Marketplace discoverability, accepting a bounded solo-maintainer cost in exchange for decoupled release cadence.

Transcribed from an isolated position sweep (identical brief, no other positions visible; self-reported identity matched the serving tag). Prose is verbatim.

The brief's most consequential fact is that the verification category is empty. Every named competitor is a static diff reader. That means the relevant buyer, a maintainer who wants CI to actually execute the PR's claimed checks, does not yet have a search reflex for this capability. A documented YAML recipe in the harnessie docs (option 4) and a reusable workflow (option 3) both require that buyer to already know harnessie exists; they don't. A composite Action living inside the harnessie repo (option 2) does not surface in the Marketplace either. Only option 1 puts a "verify PR claims" entry in the channel where the buyer is actually looking. The category being unoccupied is not a footnote; it is the entire reason this brief exists, and it is the reason a second repo is worth the cost.

The "new dedicated repo" framing is not vanity. Marketplace listing is what makes the channel difference real, but the substantive benefit is decoupling release cadence. harnessie is the heavy thing, and it will keep moving: breaking changes, model API shifts, sandbox updates, verifier prompt revisions. A user who pins v1.2.3 of an action wants to know that a bump to harnessie 0.8 does not silently change action behavior. A dedicated repo pins a tested harnessie version, lets the Action's own CI run offline against a fixture with a mock model, and means a faulty Action release can be reverted without entangling the core tool. Co-locating the Action inside the harnessie repo (option 2) fuses those lifecycles: every harnessie PR becomes a candidate Action change, and the Action's CI matrix either grows to retest the world or quietly rots. The brief explicitly names "pinned harnessie version" and "separate release cadence" as features of option 1; that is not decorative wording, it is the load-bearing reason for the structure.

The "solo maintainer" constraint is the obvious objection and it is real but smaller than it looks. A composite Action is a thin orchestrator: an `action.yml` that resolves a claims file, calls `pip install harnessie==X.Y.Z`, runs `harnessie verify`, renders the summary table from the structured output, uploads the report artifact, and gates on exit code. The Python heavy lifting stays in the harnessie repo. The new repo's surface area is `action.yml`, a README, a small offline fixture, and a release tag. The CI described in the brief, offline against a fixture with a mock model, is small and stable. The maintenance tax exists; it is bounded; and it buys visibility that no other option can.

Concretely on the alternatives: option 3 (reusable workflow) is the closest competitor and would be my pick if the acceptance criterion "stranger reaches a claim-by-claim merge-gating check in under five minutes with one workflow file" were the only metric; `uses: org/repo/.github/workflows/verify.yml@v1` does work. But reusable workflows do not appear in Marketplace search, which is where PR-tool buyers actually look, and they are second-class in editor and IDE surfacing. The failure mode is not technical but distributional: the tool exists, works, and is invisible. Option 4 (docs only) fails the brief's own acceptance criterion before the timer starts; the stranger is copy-pasting untested YAML, inheriting whatever harnessie version is latest, and has no upgrade path that does not run through the harnessie docs site. Option 2 keeps things simple at the cost of the Marketplace shelf; the failure mode is that the unoccupied category gets filled by someone else who did take the shelf.

What would change my position: evidence that PR-tool buyers in 2026 are finding verification tools through channels other than the GitHub Marketplace, direct blog discovery, conference talks, a dominant third-party review aggregator. Absent that, the empty shelf is the asset, and a small dedicated repo is the cheapest way to put a labeled, pinned, versioned box on it.

## Objections

none logged

## Arbitration

- decided_by: Sam Rogers
- date: 2026-07-09
- decision: Approved

## Evidence

- [Design draft: harnessie-verify-action](../working/github-action-design.md) — contract, inputs, security posture, shape alternatives, acceptance criteria, non-goals.
- [AIDR-0006](AIDR-0006-standalone-verifier-surface-for-agent-produced-prs.md) — the standalone verify surface this packages; its field proof against a real PR queue.
- Market sweep 2026-07-10 (Perplexity, sonar-pro): CodeRabbit, Greptile, Qodo, Ellipsis, Graphite, Copilot code review, Cursor Bugbot, PR-Agent all static-review-only; none executes claimed checks or adjudicates PR bodies as claims.
