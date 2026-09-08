# Harnessie 1.4.1 release execution

Started 2026-09-08 from merged commit `2dc316ece292b6e510750188275f8d5b8c04f526`. Sam selected 1.4.1, merged the exporter completion and authorized the described sequence: release preparation, final validation, GuideCheck acceptance, core publication, then Action and Homebrew propagation. Signed commits and annotated signed release tags retain the established release policy. No package is published until the recorded gates pass.

## Scope

The release adds strict offline export of existing open contested records to AIDR 0.1.0. Recorded dissent and evidence hashes survive, human Arbitration stays empty, the original run remains halted, and unsupported platforms or ambiguous inputs refuse. [Release notes](../RELEASE_NOTES-1.4.1.md) describe behavior and limitations.

Accessibility remains deferred under Sam's session instruction, retained when authorizing this release sequence. No fresh manual or automated accessibility pass is claimed. The existing 36 review candidates and manual work remain follow-up. Bidding, live panels, arbitration import, broader formats and runner integration remain outside scope.

## Reconciliation

PR #19 merged as `2dc316e`; exact-merge CI, CodeQL, Scorecard and Pages all passed. PyPI 1.4.1 returned 404 and no conflicting 1.4 tags existed at preparation. These were preparation-time observations. Core 1.4.1 and Action 0.2.2 are now published; engine wrappers retain independent version 0.1.0.

The final guide replaces authoring-only publication wording so the release artifact can remain immutable after publication. Its SHA-256 is `7ab4c0a952109ea10257b1a9859533778261291605ce386708bccb305bbf09dc` (8,036 bytes). The DNS anchor carried the historical 1.3.1 hash during initial reconciliation; Sam replaced it after final deployment, and hosted acceptance then passed. The immutable source tag is independently checked in addition to the hosted receipt.

## Progress

Release notes and changelog prepared. The complete local release gate passed: 718 tests, one live-provider skip, 28 expected failures, 66/66 deterministic evals, schemas/manifests, isolated wheel/sdist build, Twine, artifact inspection and fresh installed consumer. The dated Siteline result is 97/100 A. Final CI/deployment and the signed tag subsequently completed as recorded below. DNS and hosted acceptance, GitHub/PyPI publication, independent package verification and Action propagation are complete. Homebrew publication is complete. This documentation closeout records all release and downstream receipts; its exact-commit CI and live-byte checks are the final documentation verification. [Machine-readable state](release-1.4.1-state.json) records each completed step and the exact identity it covers.

## Candidate and deployment completed

PR #20 merged as `296deed2f91cd4c8eeecad82b83f137dd029ea26`. Exact-commit CI, CodeQL, Scorecard and Pages passed. [Live comparison](release-1.4.1/live-bytes.json) verifies all 23 checked resources; the [production search contract](release-1.4.1/production-search.json) covers ten pages with zero defects. The signed `v1.4.1` tag object is `8d04b94efa685fcc840852be775d2cf2163d4680`, pointing to that merge. [Clean-clone verification](release-1.4.1/tag-verification.txt) confirms its SSH signature and the exact immutable guide bytes.

The [hosted checkpoint](release-1.4.1/guidecheck-before-dns.json) evaluated the final 8,036-byte guide under profile 2.0.0 at Level 3, with one blocker and no qualifying anchor. DNS still carried the 1.3.1 hash. Sam received the exact replacement value for the existing Namecheap `_assistant-guide` TXT record. Sam subsequently confirmed the change. The [final hosted receipt](release-1.4.1/guidecheck-prepublication.json) earned Level 4 with zero blocking findings and a qualifying DNS anchor before publication.

## Core publication and independent acceptance

[GitHub release v1.4.1](https://github.com/snapsynapse/harnessie/releases/tag/v1.4.1) was published at 2026-09-08T20:45:54Z. Release workflow [34276711096](https://github.com/snapsynapse/harnessie/actions/runs/34276711096) passed. The protected PyPI environment was approved under the authorized release sequence after independent verification of all four original GitHub assets. [Provenance](release-1.4.1/github-provenance.json) binds the wheel, sdist, SBOM and checksums to the signed release tag and commit. No release assets were rebuilt or replaced.

[PyPI integrity](release-1.4.1/pypi-integrity.json) confirms matching distribution hashes and cryptographic publisher attestations for `snapsynapse/harnessie`, `release.yml`, environment `pypi`. The [fresh Python 3.13.9 public-index consumer](release-1.4.1/pypi-consumer.json) passed dependency checks, actual mock workflow execution, installed CLI export, pinned AIDR lint, input preservation, continued human-arbitration halt and safe refusal. The first index lookup and two Action PR jobs encountered ordinary index propagation; unchanged retries passed. No live model verdict was earned.

## Downstream acceptance

[Verify Action 0.2.2](https://github.com/snapsynapse/harnessie-verify-action/releases/tag/v0.2.2) pins core 1.4.1. All seven fixtures passed on merge commit `9f18d70017f395ef4d15ac5746e30ac633f00f8e`. The signed immutable tag and stable `v0` were read back from the remote; stable promotion used an explicit compare-and-swap lease. [Receipt](release-1.4.1/verify-action.json) records identities and limits.

Homebrew 1.4.1 passed strict online audit, a real 1.3.1 to 1.4.1 upgrade, formula test, linkage test and the installed exporter demonstration with zero live calls. [PR #3](https://github.com/snapsynapse/homebrew-tap/pull/3) merged as `953760f3968200f99658bfb068609532cb9fbf4d` from GitHub-verified signed commit `96e81c80b48bd96e5df0e6f031e6525fce96854b`. Remote formula, source checkout and active tap match; both checkouts are clean on main and installed 1.4.1 is verified. No hosted CI is configured for the tap. The [receipt](release-1.4.1/homebrew.json) records each check.
