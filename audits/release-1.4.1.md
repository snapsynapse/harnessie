# Harnessie 1.4.1 release execution

Started 2026-09-08 from merged commit `2dc316ece292b6e510750188275f8d5b8c04f526`. Sam selected 1.4.1, merged the exporter completion and authorized the described sequence: release preparation, final validation, GuideCheck acceptance, core publication, then Action and Homebrew propagation. Signed commits and annotated signed release tags retain the established release policy. No package is published until the recorded gates pass.

## Scope

The release adds strict offline export of existing open contested records to AIDR 0.1.0. Recorded dissent and evidence hashes survive, human Arbitration stays empty, the original run remains halted, and unsupported platforms or ambiguous inputs refuse. [Release notes](../RELEASE_NOTES-1.4.1.md) describe behavior and limitations.

Accessibility remains deferred under Sam's session instruction, retained when authorizing this release sequence. No fresh manual or automated accessibility pass is claimed. The existing 36 review candidates and manual work remain follow-up. Bidding, live panels, arbitration import, broader formats and runner integration remain outside scope.

## Reconciliation

PR #19 merged as `2dc316e`; exact-merge CI, CodeQL, Scorecard and Pages all passed. PyPI 1.4.1 returned 404 and no conflicting 1.4 tags existed at preparation. These checks must be repeated before publication. Core and downstreams are currently published at 1.3.1; engine wrappers retain independent version 0.1.0.

The final guide replaces authoring-only publication wording so the release artifact can remain immutable after publication. Its SHA-256 is `7ab4c0a952109ea10257b1a9859533778261291605ce386708bccb305bbf09dc` (8,036 bytes). The DNS anchor still carried the historical 1.3.1 hash during reconciliation; final deployment and the operator's DNS replacement must precede hosted acceptance. The immutable source tag is independently checked in addition to the hosted receipt.

## Progress

Release notes and changelog prepared. The complete local release gate passed: 718 tests, one live-provider skip, 28 expected failures, 66/66 deterministic evals, schemas/manifests, isolated wheel/sdist build, Twine, artifact inspection and fresh installed consumer. The dated Siteline result is 97/100 A. Final CI/deployment, signed tag, hosted acceptance, GitHub/PyPI original-build publication and downstream verification remain pending. [Machine-readable state](release-1.4.1-state.json) records each completed step and the exact identity it covers.
