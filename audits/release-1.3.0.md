# Harnessie 1.3.0 release execution

Scope: Harnessie core, followed by its separately versioned Verify Action and Homebrew distribution. Engine wrappers retain their independent release train. Source baseline: local GuideCheck commit `98283d1393353041686199b7ee638b10a3fbcf36`, rebased onto main `a734a8f28fd9955b3a152ed15e96742b3c370a92` for this release branch.

## Authority and accessibility disposition

Sam authorized full publishing on 2026-09-07 local time, 2026-09-08 UTC:

> let's hold off on the accessibility review as it's not a direct blocker. please proceed with other items that are blocking release, and let's complete the full release package publishing

This supersedes the earlier publication hold and the requirement to complete the remaining accessibility review before 1.3.0. The four confirmed serious violations and 22 review candidates were repaired. The remaining 35 table-contrast candidates, one video-caption applicability candidate and manual keyboard/zoom/screen-reader acceptance remain deferred follow-up. The automated result remains inconclusive, with zero confirmed violations; no manual pass or complete accessibility conformance is claimed. The unprocessed queue remains `handoffs/2026-09-07-accessibility-review.md`, and durable baseline/mitigation evidence remains in `audits/accessibility/`.

GuideCheck for final 1.3.0 bytes, exact-candidate checks, dated live Siteline evidence and release integrity remain required. Sam applies Namecheap DNS updates; the assistant supplies exact values and verifies public results. Signed commits and a signed version tag use the existing configured signing key. No provider-policy change or model call is needed.

## Candidate and publication order

1. Prepare coherent 1.3.0 version, changelog, observer documentation, public machine resources and profile-2.0.0 guide/sidecar/trust pins. Public source and package-channel claims remain distinct until publication is verified.
2. Run the full hash-locked local gate, build/archive inspection, fresh-consumer smoke, generated documentation, search and manifest checks. Deliver by reviewed PR and verify exact-merge CI and Pages.
3. Compare final served bytes, create the authorized signed immutable source tag, confirm tag URL identity, and obtain Sam's final matching DNS TXT update. Run hosted GuideCheck requiring profile 2.0.0 and retain the exact receipt. Obtain a dated live Siteline 90+ result.
4. Publish the GitHub Release only after those gates. Its workflow builds and attests the four final assets once, verifies original provenance, attaches the assets and publishes those same distributions through the protected PyPI environment.
5. Independently verify GitHub asset digests/provenance, PyPI metadata/attestations and a clean public-index consumer. Then test and publish the Verify Action update and Homebrew formula. Record exact revisions and any remaining lag.

## Execution evidence

Publication is authorized and in progress. The machine-readable state is [release-1.3.0-state.json](release-1.3.0-state.json). Earlier 1.2.0 GuideCheck and package receipts remain historical evidence and cannot qualify the changed guide or new assets. Final revisions, gates and provider receipts will be added as observed.

### Local candidate gate

The full hash-locked release gate passed with 572 tests, one environment-dependent skip, 28 expected failures for deferred features, 62/62 deterministic evals, nine authoring documents, 21 outward and 16 inward manifest entries, nine generated docs, wheel/sdist inspection and a fresh-install observer smoke. The search contract covered ten pages with zero defects or infrastructure failures. The initial run exposed missing required release-boundary wording in NEXT.md; the corrected full rerun passed. These are candidate results, not published-artifact evidence.
