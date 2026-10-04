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

October 3 pilot update: the approved [v4 and v5 attempts](audits/pilot-panel-v4-v5-results-2026-10-03.md) stopped before a completed position. V5 held authentication and stayed within token limits, but used all four stage calls for evidence reads. The immediate next tranche is offline reviewer scheduling: batch reads and reserve the final call for the report, retaining existing limits. This supersedes the final-candidate preparation step in the historical pilot summary below. No further live attempt is authorized.

- The [controlled-review live pilot](audits/controlled-review-pilot-2026-09-09.md) remains the next active tranche. The question and participant direction are confirmed. September 17 [local preparation](audits/pilot-preparation-2026-09-17.md) implements a pilot-only Claude Code transport, Qwen identity receipts and a sealed disposable mock rehearsal. The separately approved [synthetic smokes](audits/pilot-smoke-2026-09-17.md) passed with local Qwen and attributed Claude's synthetic answer to Fable through a stream capture. Claude also reported Haiku usage whose role remains unverified. The [offline stream-adapter correction](audits/pilot-stream-adapter-2026-09-17.md) is implemented and independently verified. It preserves all-model usage. Sam delegated the additional-model decision; the [bounded Haiku exception](audits/pilot-additional-model-policy-2026-09-17.md) permits the exact observed identity under explicit policy, with Fable answer attribution still required. The [offline live wrapper](audits/pilot-live-wrapper-2026-09-19.md) is implemented and independently verified. Local Ollama identity is verified and usage credits were verified off. The authorized [first live attempt](audits/pilot-live-panel-2026-09-19.md) stopped after one Claude call with `stream_malformed`; Qwen was not called. The [panel-v3 budget-fit result](audits/pilot-panel-v3-budget-fit-2026-09-19.md) shows parser/capture success but a Haiku bound exceeded after three Claude calls, before Qwen. The approved [full-workload offline sizing](audits/pilot-workload-sizing-2026-10-01.md) records exact pre-dispatch request metrics for both encodings and rehearses all four stages against all declared evidence. All 16 requests fit the 256,000-byte input/evidence envelope; the largest is 219,150 bytes. Sam directed retaining the complete evidence and using the existing Claude subscription allowance rather than pursuing the earlier 64,000-byte curation proposal. The [Claude authentication-contract repair](audits/pilot-claude-auth-contract-2026-10-01.md) recognizes current first-party OAuth, removes API-key and alternate-provider environment routes, binds the live adapter against auth drift, and still requires separate fresh Max included-allowance and credits-off evidence. The approved [Claude Haiku context policy](audits/pilot-haiku-context-policy-2026-10-01.md) now encodes and rehearses the exact full-evidence per-call and run-wide thresholds offline while preserving the v1 policy. The rehearsal admitted all 16 requests, stopped at human arbitration and made zero live calls. Next: independently verify and seal one final zero-authority execution candidate with fresh CLI, OAuth, Max included-allowance, credits-off and Qwen identity evidence. The final-panel allowance remains zero until that exact candidate receives separate live approval. Human arbitration remains a required post-panel acceptance gate. Export occurs while the run record is open; canonical AIDR arbitration does not resume the source run.
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
