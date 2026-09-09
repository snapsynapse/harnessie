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

- The [controlled-review live pilot](audits/controlled-review-pilot-2026-09-09.md) is approved as the next active tranche. Before dispatch it needs the confirmed decision question, a disposable hash-frozen evidence root, two exact participant model/provider instances, and explicit egress and spend approval. Human arbitration is a required post-panel acceptance gate. Export occurs while the run record is open; canonical AIDR arbitration does not resume the source run.
- The broader [capability program](audits/capability-program-readiness-2026-09-09.md) is active. Automatic deterministic runner observation is ready to implement. Bid record, commentary and follow mode need bounded design and guard tranches. Bid-driven selection remains gated on record-mode calibration evidence and its own human-arbitrated AIDR.
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
