# Harnessie 1.3.1 corrective release

Scope: complete the authorized 1.3 feature release without changing the signed 1.3.0 tag or weakening original-build verification. The feature scope and Sam's explicit accessibility-review deferral remain as recorded in [the 1.3.0 execution record](release-1.3.0.md).

## Cause and correction

The 1.3.0 workflow passed exact-tag tests, built the final assets and signed their provenance. GitHub CLI then rejected the verifier command because `--signer-workflow` and `--cert-identity` are mutually exclusive. The old tests intercepted subprocess calls and did not exercise CLI parsing. Attachment and PyPI jobs correctly remained skipped; the original build outputs were not retained because upload steps followed the failure.

The corrected command uses only the exact certificate identity, which already binds repository, workflow path and tag. Repository scope, source tag, source commit, signer commit, SLSA predicate and hosted-runner restriction remain enforced. The regression asserts exactly one identity selector and both commit bindings. All 11 provenance tests pass. A real GitHub CLI 2.98.0 negative control accepts the corrected arguments and refuses a file without attestations, rather than failing argument parsing.

The build now retains distribution and integrity artifacts even if a later verification step fails, allowing diagnosis or verified recovery of the original bytes. Release attachment still requires a successful build job, and PyPI still requires successful build and attachment jobs. Artifact retention does not authorize publication or bypass provenance checks.

## Release gates

The signed 1.3.0 tag and failed run remain intact. Corrective version 1.3.1 carries the same offline observer, maintenance and accessibility repairs with the publication-tool correction. Its guide differs only in guide-version and registry URL; applies-to remains Harnessie 1.3.x. Final SHA-256 is `ef62ac6ecc50f1f277dda119299d1b145e0aae66a51bcf47ba233e23c072409b` (7,766 bytes). Sam applied the matching Namecheap DNS change after deployment; the final hosted receipt passed before publication.

The existing dated Siteline 97/100 result covers the same feature/site structure before this corrective version label; final deployed-byte and production-search checks will verify the corrective source. The hosted GuideCheck result, signed immutable tag identity, exact-commit CI, original-build verification, PyPI attestations/consumer checks and separately tested downstream publication all completed as recorded below.

Publication authority comes from Sam's instruction to complete full package publishing. The assistant selected a corrective patch version to preserve immutable release history; no additional feature or provider-policy scope was added. The machine-readable state is [release-1.3.1-state.json](release-1.3.1-state.json).

## Local candidate verification

The locked release gate passed with 572 tests passed, 1 skipped and 28 expected failures; all 62 deterministic evaluations passed. Dependency locks, authoring and manifest checks, generated docs, wheel and sdist inspection, Twine metadata and a fresh installed consumer passed. The search contract checked 10 pages with zero defects. Exact-commit CI and all hosted/provider gates subsequently passed.

## Published identities and independent verification

- Core PR 16 merged at `6ddf84429ab8fbfa9ec96e59b283cf7cb341dd6f`. Exact-merge CI `34179004951`, CodeQL, Scorecard and Pages `34179004273` passed. The release tag object is `692af124afe8cd9971fc51347067016b6980ec83`; a clean clone verified its SSH signature and peeled commit. The immutable tag-source URL returned HTTP 200.
- [Hosted GuideCheck receipt](release-1.3.1/guidecheck-prepublication.json), fetched at 2026-09-08T02:13:48 UTC, evaluates profile 2.0.0 at Level 4 with zero blockers and one qualifying DNS anchor. Served guide, sidecar, DNS and repository bytes agree. Four warnings cover response headers, unestablished repository independence and the then-unpublished PyPI URL; no Level 5 runtime claim is made. The first check during DNS propagation returned Level 3 and did not authorize publication.
- [Live byte receipt](release-1.3.1/live-prepublication.json) matched 22 resources to the merged source. Production search checked ten sitemap pages with zero defects or infrastructure failures. The [dated Siteline receipt](release-1.3.0/siteline.json) scored 97/100, A, on the same feature/site structure before the corrective version label; it is not represented as a new full-site scan.
- [GitHub Release 384404763](https://github.com/snapsynapse/harnessie/releases/tag/v1.3.1) was published at 2026-09-08T02:14:04Z. [Workflow 34179342988](https://github.com/snapsynapse/harnessie/actions/runs/34179342988) passed the exact-tag gate, single final build, reproducible SBOM generation, original attestation verification, attachment and protected PyPI publication. The normal required-reviewer approval was applied under Sam's full-publishing authorization; no check or provenance bypass was used.
- [Independent GitHub asset verification](release-1.3.1/github-provenance.json) downloaded all four assets and required the exact certificate identity, repository, source tag, source and signer commits, hosted runner and SLSA predicate. Both PyPI files match these exact digests. `pypi-attestations` 0.0.30 cryptographically verified both distributions; the public publisher is repository `snapsynapse/harnessie`, workflow `release.yml`, environment `pypi`. [PyPI integrity](release-1.3.1/pypi-integrity.json) and [clean public-index consumer](release-1.3.1/pypi-consumer.json) record the outcomes.
- [Downstream evidence](release-1.3.1/downstream.json) records Verify Action 0.2.1/stable v0 at `97ed2264818fc4c620c03de5cc9522965318079b`, with seven exact-merge CI jobs passed and a clean-clone verified signed tag. Homebrew PR 2 merged as `630021462ef961669a0802d090c7c77c65190932`; strict online audit, the real 1.2.0-to-1.3.1 upgrade, formula test, linkage and installed CLI checks passed. Engine wrappers remain independently released at 0.1.0.

## Remaining scope

No release blocker remains from the approved session scope. Accessibility review remains explicitly deferred: 35 table-contrast candidates, one video-caption applicability candidate and manual acceptance. The automated audit is inconclusive despite zero confirmed violations. AIDR-0009 continues to defer bidding, commentary, follow mode, automatic runner integration and model selection. The controlled-review exporter/pilot and sole-maintainer policy proposal require their own accepted packets.

## Publication metadata closeout

Current-source docs now identify core 1.3.1, Action 0.2.1/stable v0 and Homebrew 1.3.1 as published; the final guide receipt is linked from human and machine surfaces. The guide and sidecar bytes remain unchanged. Closeout regression checks passed: 572 tests, one skip, 28 expected failures, 21 trust files, generated-doc freshness, four-component ecosystem validation with matching downstream pins, and ten-page search contract with zero defects.
