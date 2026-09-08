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

### Candidate delivery and live discovery

Signed candidate commit `437612ce174e4c0cfdb2b5513978a21e9a6a4de4` passed [CI](https://github.com/snapsynapse/harnessie/actions/runs/34177214851) and [CodeQL](https://github.com/snapsynapse/harnessie/actions/runs/34177214733), then [PR 14](https://github.com/snapsynapse/harnessie/pull/14) merged as `27baa3015eb93c8ebf979ae8a425a95ea568ca86`. Exact-merge CI, CodeQL, Scorecard and [Pages](https://github.com/snapsynapse/harnessie/actions/runs/34177326461) passed. The optional model verifier supplies no independent model-review evidence when its configured invocation is skipped.

[Live Siteline](release-1.3.0/siteline.json) measured 97/100, grade A, at 2026-09-08T01:40:11.850Z using scanner 2.0.0 and rubric 2.3.0. This meets the 90+ release bar. Its CTA warning has no concrete target evidence and remains an opportunity; the scanner's inferred SaaS/commerce classification is not a product claim. This is a homepage and discovery-resource scan, not a full-site accessibility audit. The [production search check](release-1.3.0/production-search.log) covered ten sitemap pages with zero defects and infrastructure failures.

The current Scorecard review found the already scoped branch-policy/sole-maintainer, optional coverage-guided fuzzing and badge gaps, repository-age limits, and a public-constraint installation pin warning. Controlled dependency locks and separate consumer-resolution coverage remain intentional. No provider-policy expansion was made for the score.

### Final guide verification before packaging

After Sam updated the final Namecheap value, [hosted GuideCheck](release-1.3.0/guidecheck-prepublication.json) fetched the 7,766-byte 1.3.0 guide at 2026-09-08T01:41:49.634507Z and earned Level 4 under profile 2.0.0 with zero blocking findings. Guide SHA-256 is `5e00fa6903e0d42c49e9a25c08eec19116b04bf01ee0daf8c4d7d754b58b0793`; the fetched sidecar matches and DNS is the one qualifying independent anchor. Repository bytes match but do not qualify independently. Four warnings are retained: two response-header limits, unestablished repository independence, and the expected pre-publication PyPI URL 404. The DNS anchor meets the independent-channel requirement without the registry. No runtime Level 5 claim follows from `level5_ready`. The immutable tag-source URL will be checked after the final tag is created and before GitHub Release publication.

### Signed tag and GitHub publication

[PR 15](https://github.com/snapsynapse/harnessie/pull/15) passed exact-head checks and merged as `bc40ae94265180e21498cbd6dff4f23b52342593`; its exact-merge platform/package/CodeQL/Scorecard checks and Pages passed. All [22 served resources](release-1.3.0/live-prepublication.json) matched that revision. Signed tag `v1.3.0`, object `d760edb39eca38e5eb56b0da2e6ae6830d992ff6`, peels to that commit. A clean shallow clone verified the ED25519 signature using the existing configured public key. The sidecar tag-source URL returned HTTP 200 before publication.

[GitHub release 384397522](https://github.com/snapsynapse/harnessie/releases/tag/v1.3.0) was published at 2026-09-08T01:49:25Z. This started the asset-build and protected-publisher workflow; their outcomes are recorded separately below.

### Failed publication and corrective version

[Release run 34177934310](https://github.com/snapsynapse/harnessie/actions/runs/34177934310) passed exact-tag tests, built all four assets and signed their provenance, then failed before upload because GitHub CLI rejects simultaneous `--signer-workflow` and `--cert-identity`. No assets were attached and nothing reached PyPI. The signed tag remains unchanged. The correction retains the exact certificate identity, both commit checks, tag ref and hosted-runner restriction; 11 policy tests pass and a real CLI negative control accepts the corrected flags and refuses a file without attestations. The assistant selected corrective version 1.3.1 within the authorized full-publication task to preserve the immutable 1.3.0 tag and original-build identity. See [1.3.1 execution](release-1.3.1.md).
