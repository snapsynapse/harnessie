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

October 3 pilot update: the [offline scheduling repair](audits/pilot-reviewer-scheduling-2026-10-03.md) is committed at 793338b. The separately approved [v6 attempt](audits/pilot-v6-results-2026-10-03.md) followed the reading/reporting schedule but its fourth Claude response refused with conflicting_model_evidence: one model label, two assistant message/request identities. Qwen was not called and no position or export completed. The fourth response also reported output above the requested token limit. The [offline diagnosis](audits/pilot-v6-offline-diagnosis-2026-10-03.md) now reproduces both identity and intermediary-message barriers and confirms that requested output tokens are not independently enforced after response. Recommended next: define a narrow continuation contract and post-response output threshold before implementation; optionally approve a separate one-call local Qwen smoke. Qwen remains unattempted in this panel, not failed. No repair or further live attempt is authorized by the consumed v6 approval. This supersedes the next-step instructions in the historical pilot summary below.

### Pilot pickup queue

1. Define the narrow Claude continuation contract before changing parser admission. The v6 stream has two same-model message/request identity groups and an intermediary synthetic user event. Preserve session/model attribution, unique formatter linkage, terminal payload equality, native-tool exclusions and complete usage. An isSynthetic marker alone is insufficient trust evidence.
2. Decide and implement, after scope approval, a post-response output-token refusal threshold. The requested 4,096 setting is not currently enforced on reported output. Retain usage on refusal; test exact-limit and one-over cases. Do not raise limits to make the attempt pass.
3. Prepare a fresh one-call local Qwen smoke driver and exact proposal. Synthetic input only, no tools or decision evidence, fixed loopback, 120 seconds, 4,096 input/evidence bytes, 1,024 requested output tokens, 128,000 output bytes and no retry. Retain request/hash, attempt guard, before/after identity, raw and normalized usage, elapsed time and outcome. Execute only after separate live approval. Qwen passed a September 17 smoke; October 3 identity checks are not current inference proof.
4. After approved corrections, run regression checks and independent verification, then prepare a new zero-authority full-panel candidate with fresh account and identity evidence. Preserve all 17 sources, existing resource limits and the four-stage order. Obtain approval of that exact proposal before live dispatch. V6 is consumed and must not be reused.
5. If a future panel completes, export its open record and stop for Sam's human arbitration. Then reassess the next capability tranche, automatic deterministic runner observation. Do not infer implementation authority from pilot completion.
6. Track the two intermittent transport timing-test failures observed during the worker's scheduling test run. The independent 201-test pilot run passed; that does not explain or resolve the earlier failures. Investigate only if they recur or before relying on those timing checks for a new acceptance claim.

The [controlled-review pilot](audits/controlled-review-pilot-2026-09-09.md) remains the active tranche. Earlier preparation, transport, auth and policy work is retained in the dated pilot audits; do not repeat it. [V6 results](audits/pilot-v6-results-2026-10-03.md) and [offline diagnosis](audits/pilot-v6-offline-diagnosis-2026-10-03.md) own the latest findings. Browser/CLI account correspondence remains independently unverified; refresh and reconcile it during future preflight. Export occurs while the record is open; exported arbitration does not resume the source run.

### Other pending work

- Reconcile `ops/search-indexing.md` against the dated September 21 audit: ten sitemap pages, three previously requested pages observed indexed, and `/ringer.html` still pending at that observation. Preserve do-not-repeat actions and distinguish historical evidence from fresh Console state. The scoped queue remains `handoffs/2026-09-21-search-indexing-audit.md`; no Console mutation is implied.
- Review the CodeQL dependency PRs #33-36 observed open during this session, refreshing their current state before acting. No merge was performed.
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
