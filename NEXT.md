# Current state and next work

## Release boundary

Harnessie 1.4.1 is the stable core release on GitHub and PyPI. Its signed tag resolves to `296deed2f91cd4c8eeecad82b83f137dd029ea26`; release workflow [34276711096](https://github.com/snapsynapse/harnessie/actions/runs/34276711096) passed. Wheel, source distribution, CycloneDX SBOM and checksums have verified original-build provenance. Both PyPI distributions match the GitHub assets and pass cryptographic publisher verification. A fresh Python 3.13 public-index installation exercised the installed exporter and its actual mock-workflow example.

Homebrew and Verify Action are separately versioned downstreams. Action 0.2.2/stable `v0` and Homebrew 1.4.1 are published and verified; their exact identities and acceptance are recorded in [release execution](audits/release-1.4.1.md). Engine wrappers remain independently released at 0.1.0 because this release consumes no new wrapper seam.

## Verified evidence

The final 1.4.1 guide earned hosted GuideCheck Level 4 under profile 2.0.0 on 2026-09-08 UTC with zero blocking findings. Sam applied the final Namecheap DNS value. The served guide, sidecar, DNS, repository and signed tag agree on SHA-256 `7ab4c0a952109ea10257b1a9859533778261291605ce386708bccb305bbf09dc`. Conformance is not runtime safety or Level 5 enforcement.

The local release gate passed with 718 tests, one live-provider opt-in skip, 28 strict expected failures for not-yet-implemented slices and 66/66 deterministic evaluations. Exact release-commit CI, CodeQL, Scorecard and Pages passed. The dated live Siteline result is 97/100, grade A; production search checked ten pages with zero defects. [Release execution](audits/release-1.4.1.md) and its [machine-readable state](audits/release-1.4.1-state.json) retain exact receipts and limits. Prior [1.3.1 evidence](audits/release-1.3.1.md) remains historical; its guide receipt does not cover current bytes.

## Delivered scope

- The [open-record AIDR exporter](AIDR_EXPORT.md) carries recorded positions and objections into one explicitly named new record, preserves original-role attribution, binds consumed source/evidence hashes, and refuses arbitration or ambiguous input. It is an operator-issued file write outside runner ownership and consent mediation. It makes no model calls, authors no human arbitration and cannot resume the original run.
- The [installed mock example](examples/aidr-export/README.md) exercises actual runner output, repeated roles and dissent, installed CLI export, pinned AIDR 0.1.0 lint, unchanged inputs, a preserved human halt and unsupported-format refusal. Native Windows export remains unsupported.
- The [offline observer](OBSERVER.md) remains the conservative shipped outcome of [AIDR-0009](decisions/AIDR-0009-bid-rounds-and-run-observer.md). Its authoritative human arbitration is unchanged. Exit 0 means observation succeeded, not that the observed run passed.

## Remaining release order

Core and downstream external closeout gates are complete. This documentation closeout records their completed state; its exact-commit CI and deployed-byte checks complete the sequence. Release-state evidence distinguishes each stage; branch push or fixture success alone does not establish customer acceptance or a live model verdict.

## Remaining work

October 3 pilot update: the [offline scheduling repair](audits/pilot-reviewer-scheduling-2026-10-03.md) is committed at 793338b. The separately approved [v6 attempt](audits/pilot-v6-results-2026-10-03.md) remains consumed and incomplete: four Claude calls, zero Qwen calls, no accepted position or export. The [subsequent admission review](audits/pilot-continuation-contract-2026-10-03.md) found that the synthetic intermediary requests continuation after an output-token limit, with no authenticated binding between the two assistant identities. Single-identity admission remains unchanged. Under Sam's subsequent offline-work approval, the experimental Claude adapter now refuses otherwise valid responses whose aggregate reported output exceeds the configured 4,096-token limit, preserving capture and usage. This is a post-response acceptance threshold, not a provider generation or billing cap. Structural refusals retain precedence; v6 is not retroactively accepted. The [earlier diagnosis](audits/pilot-v6-offline-diagnosis-2026-10-03.md) records pre-repair behavior.

### Pilot pickup queue

1. [Output-budget guidance](audits/pilot-output-budget-guidance-2026-10-03.md) now tells the reviewer its actual configured aggregate response ceiling and asks for concise completion while preserving all evidence, citations and uncertainty. Synthetic checks prove notice delivery and completion mechanics, not live token fit. The v6 intermediary is a token-limit continuation, not evidence that a formatting-only exception is safe. Retain single-identity binding and refuse unproven continuations. Any future admission extension needs evidence connecting the identities and preserving the answer; an isSynthetic marker alone is insufficient.
2. The Claude aggregate output-token refusal is implemented in experimental source with exact-limit, one-over, all-model accounting and no-retry regressions. Keep the 4,096 ceiling and existing byte, stage and run limits. Earlier consumed captures, approvals and refusal outcomes remain unchanged.
3. The [isolated local Qwen smoke driver and sealed candidate](audits/pilot-qwen-smoke-preparation-2026-10-03.md) are prepared. The driver binds one synthetic request, strict local residency checks, a durable attempt guard, current identity, implementation hashes and separate exact-proposal approval. Limits remain 120 seconds for inference, 4,096 input/evidence bytes, 1,024 requested and admitted output tokens, 128,000 output bytes and no retry. Metadata/blob preflight passed at October 3 20:19 America/Denver; the candidate has zero live allowance and no approval or attempt. Refresh metadata and seal a new candidate if its 15-minute identity window expires. Qwen passed a September 17 smoke; metadata checks are not current inference proof.
4. After approved corrections, run regression checks and independent verification, then prepare a new zero-authority full-panel candidate with fresh account and identity evidence. Preserve all 17 sources, existing resource limits and the four-stage order. Obtain approval of that exact proposal before live dispatch. V6 is consumed and must not be reused.
5. If a future panel completes, export its open record and stop for Sam's human arbitration. Then reassess the next capability tranche, automatic deterministic runner observation. Do not infer implementation authority from pilot completion.
6. Track the two intermittent transport timing-test failures observed during the worker's scheduling test run. The independent 201-test pilot run passed; that does not explain or resolve the earlier failures. Investigate only if they recur or before relying on those timing checks for a new acceptance claim.

The [controlled-review pilot](audits/controlled-review-pilot-2026-09-09.md) remains the active tranche. Earlier preparation, transport, auth and policy work is retained in the dated pilot audits; do not repeat it. [V6 results](audits/pilot-v6-results-2026-10-03.md) and [offline diagnosis](audits/pilot-v6-offline-diagnosis-2026-10-03.md) own the latest findings. Browser/CLI account correspondence remains independently unverified; refresh and reconcile it during future preflight. Export occurs while the record is open; exported arbitration does not resume the source run.

### Other pending work

- Reconcile `ops/search-indexing.md` against the dated September 21 audit: ten sitemap pages, three previously requested pages observed indexed, and `/ringer.html` still pending at that observation. Preserve do-not-repeat actions and distinguish historical evidence from fresh Console state. The scoped queue remains `handoffs/2026-09-21-search-indexing-audit.md`; no Console mutation is implied.
- The [coordinated CodeQL update](audits/codeql-coordinated-update-2026-10-03.md) aligns all four subactions to the verified 4.38.2 commit and groups future CodeQL version updates. Existing PRs #33-36 remain untouched; #33, #35 and #36 mixed action versions. Hosted CI and Scorecard acceptance for the combined candidate require delivery and fresh workflow results.
- Jev operator help remains an optional planning proposal in `handoffs/2026-09-22-jev-operator-help.md`, not implementation or inference authority.
- The broader [capability program](audits/capability-program-readiness-2026-09-09.md) is active. Automatic deterministic runner observation is ready to implement. Bid record, commentary and follow mode need bounded design and guard tranches. Bid-driven selection remains gated on record-mode calibration evidence and its own human-arbitrated AIDR.
- The [September 17 acceptance and verification assessment](audits/acceptance-and-verification-design-2026-09-17.md) scopes four proposed preparation packets: protected acceptance contracts, verifier independence/evidence requirements, shared calibration with operator review cost, and first-use adoption within existing workflows. They add design candidates to ROADMAP, without changing the approved next runtime tranche or authorizing implementation and live calls.
- The [current Ringer/Ringside comparison](audits/ringer-ringside-interoperability-2026-09-17.md) confirms the process-check integration direction and scopes its remaining timeout, retry, receipt and identity boundaries. Reuse upstream display and evaluation surfaces; public Ringer guide corrections and a pinned compatibility recipe remain proposed work.
- Manually dispatched [dependency-lock-refresh 34379421833](https://github.com/snapsynapse/harnessie/actions/runs/34379421833) passed on exact `main` and preserved a proposal-only artifact. The patch proposes only Hypothesis 6.167.1 to 6.168.0 in the development and release locks plus manifest hashes; it is not applied.
- The sole-maintainer required-check and emergency-recovery proposal remains optional. No new provider-policy settings were activated.

## Adoption direction

The lead adoption surface is `harnessie verify` as a fail-closed intake gate for agent-produced changes. Ringer composes through its process-exit contract; the full harness supplies consent, ownership, containment, human arbitration and tamper-evident audit. Component authority and release ordering live in [ECOSYSTEM.md](ECOSYSTEM.md).

## External and optional checks

Live provider evaluations require explicit `HARNESSIE_LIVE=1` opt-in and configured endpoints. No live model verdict was earned in this release session. Test counts are dated observations, not permanent contracts.

For terminal startup choices, see [TERMINAL_SESSIONS.md](TERMINAL_SESSIONS.md). Reconcile current Git and provider state before the next task. Private planning stays in `ROADMAP-PRIVATE.md`; do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, or `workspace/`.

To re-establish the deterministic baseline in a configured development environment:

Literal
```bash
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli verify-inward-manifest
python3 scripts/build_docs_html.py --check
git diff --check
```
