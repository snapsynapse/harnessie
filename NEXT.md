# Current state and next work

## Release boundary

Harnessie 1.3.1 is the stable core release on GitHub and PyPI. Its signed tag resolves to `6ddf84429ab8fbfa9ec96e59b283cf7cb341dd6f`; release workflow [34179342988](https://github.com/snapsynapse/harnessie/actions/runs/34179342988) passed. The wheel, source distribution, reproducible CycloneDX SBOM and checksum record have verified original-build provenance. Both PyPI distributions match the GitHub assets and have verified attestations from the protected `pypi` publisher. A clean Python 3.13 public-index installation exercised the observer, evidence-bundle CLI, scaffold and inward manifest.

Homebrew and Verify Action are separately versioned downstreams. Verify Action [0.2.1](https://github.com/snapsynapse/harnessie-verify-action/releases/tag/v0.2.1) and stable `v0` resolve to `97ed2264818fc4c620c03de5cc9522965318079b` and pin core 1.3.1. Its seven-job fixture matrix passed on that exact commit. Homebrew [formula commit 6300214](https://github.com/snapsynapse/homebrew-tap/commit/630021462ef961669a0802d090c7c77c65190932) serves 1.3.1; strict online audit, an installed 1.2.0-to-1.3.1 upgrade, formula tests, linkage and installed CLI checks passed. Engine wrappers remain independently released at 0.1.0.

## Verified evidence

The final 1.3.1 guide earned hosted GuideCheck Level 4 under profile 2.0.0 on 2026-09-08 UTC with zero blocking findings. Sam applied Namecheap DNS after deployment. Served guide, sidecar, DNS and repository hashes agree. The dated Siteline result is 97/100, grade A; the final production search contract checked ten pages with zero defects. [Release execution](audits/release-1.3.1.md) and its [machine-readable state](audits/release-1.3.1-state.json) preserve the exact receipts and their limits.

The initial signed 1.3.0 tag remains unchanged. Its workflow stopped before asset upload or PyPI because GitHub CLI rejected mutually exclusive provenance identity flags. Corrective 1.3.1 uses the exact certificate identity with both source and signer commit checks. [The failed attempt](audits/release-1.3.0.md) remains explicit; it is not a published PyPI package.

## Delivered session scope

1. [AIDR-0009](decisions/AIDR-0009-bid-rounds-and-run-observer.md) records Sam's conservative arbitration: ship offline observation and defer bidding. Its five position sections, objections and attributed human decision remain authoritative. The design draft is supporting evidence; do not reuse record number 0009.
2. The [offline observer](OBSERVER.md) verifies a snapshot of an existing journal and writes cited JSON and Markdown. It makes no model calls, changes no source journal or approval state, and does not resume the runner. Exit 0 means observation succeeded, not that the run passed.
3. Approved maintenance packets 1-3 shipped: hash-locked dependencies, original-build release provenance enforcement, bounded parser properties and refusal fixes. The [maintenance record](audits/maintenance-implementation-2026-09-07.md) separates implementation evidence from the provider results in the release record.
4. The [controlled-review assessment](audits/review-interoperability-2026-09-07.md) delivered source mapping, synthetic proof and a proposed AIDR export contract. No exporter or live panel was authorized or implemented.
5. Accessibility mitigation repaired four serious keyboard-access findings and 22 homepage review candidates. GuideCheck integration and the complete core, Action and Homebrew release train are finished.

## Remaining release order

All external closeout gates are complete: final GuideCheck, core GitHub/PyPI integrity and separately tested Action/Homebrew propagation. Documentation closeout uses the same exact-commit CI and deployed-byte verification requirements.

## Remaining work

No release blocker remains from the approved session scope. These items remain deferred or require a separately accepted packet:

- Accessibility review: 35 threat-model table contrast candidates, one homepage video-caption applicability candidate, and manual keyboard, 200% zoom/reflow and screen-reader checks. Sam explicitly deferred this as nonblocking. The [mitigation audit](audits/accessibility/2026-09-07-mitigation/audit-2026-09-07.md) has zero confirmed violations and 36 incomplete candidates; its gate remains inconclusive. The temporary queue is `handoffs/2026-09-07-accessibility-review.md`, intentionally unprocessed and gitignored. Migrate completed dispositions into the audit directory and delete the handoff when the queue is exhausted. The [roadmap](ROADMAP.md) retains the acceptance bar.
- Bidding, commentary, follow mode, automatic runner integration and model selection remain deferred under AIDR-0009.
- A live controlled-review pilot or AIDR exporter needs a fixed evidence packet, attribution and namespace rules, failure-atomicity acceptance, and human arbitration where needed.
- The sole-maintainer required-check and emergency-recovery proposal remains optional. No new provider-policy settings were activated by this release.

## Adoption direction

The lead adoption surface is `harnessie verify` as a fail-closed intake gate for agent-produced changes. Ringer composes through its process-exit contract; the full harness remains the growth path for consent, ownership, containment, human arbitration and tamper-evident run audit. Component authority and release ordering live in [ECOSYSTEM.md](ECOSYSTEM.md).

## External and optional checks

Live provider evaluations require explicit `HARNESSIE_LIVE=1` opt-in and configured endpoints. CI fixture success is not evidence of a live model verdict. Test counts are dated observations, not permanent contracts. The release candidate recorded 572 passed, one environment-dependent skip, 28 expected failures for deferred features and 62/62 deterministic evaluations.

For terminal startup choices, see [TERMINAL_SESSIONS.md](TERMINAL_SESSIONS.md). Reconcile current Git and provider state before the next task. Private planning remains in `ROADMAP-PRIVATE.md`; do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, or `workspace/`.

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
