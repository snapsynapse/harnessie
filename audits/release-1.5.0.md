# Harnessie 1.5.0 release execution

Started 2026-10-06 from `main` at `5913591fd943` after Sam accepted the Harbor and OpenEnv interoperability plan, approved its phases 0 through 4 as delivered on 2026-10-05, and authorized the 1.5.0 release through the signed tag and GitHub Release, with Verify Action and Homebrew bumps prepared alongside and pushed after PyPI publication. Signed commits and an annotated signed release tag retain the established release policy. No package is published until the recorded gates pass.

## Scope

The release adds harness identity on every result, tool-contract break metrics with the first measured brains, ATIF-v1.7 trajectory export (`harnessie atif`), Harnessie as a Harbor verifier and as a Harbor external agent, richer `model_turn` and `tool_result` events, the tool-contract eval suite, a dependency lock refresh resolving the open urllib3 alerts, a working default local tier, and Linux portability for two pilot tests. [Release notes](../RELEASE_NOTES-1.5.0.md) describe behavior and limits. The four acceptance audits are [live scorecard](live-scorecard-2026-10-05/README.md), [ATIF export](atif-export-acceptance-2026-10-05.md), [Harbor verifier](harbor-verifier-acceptance-2026-10-05.md) and [Harbor agent](harbor-agent-acceptance-2026-10-05.md).

Accessibility remains deferred under Sam's standing instruction; no fresh manual or automated accessibility pass is claimed for this release. The Qwen controlled-review pilot continues on its own queue and is unchanged by this release.

## Guide

The 1.5.0 guide changes only its version fields, review date, coverage sentence and one classification sentence (ATIF export joins observation and AIDR export as a file-writing command needing separate execution authority). It is 8,054 bytes, SHA-256 `f6f1ce225d2dcafe7e2b9da5e1b8539099e6a602a8d827dd02ed02f0159bc631`. The served copy, sidecar (`immutable-release-url` https://github.com/snapsynapse/harnessie/tree/v1.5.0) and `docs/MANIFEST.yaml` pins agree. The local reference verifier (GuideCheck 2.0.0) reports one blocking finding, `anchor.independent.missing`, which is the expected state until the DNS TXT anchor is rotated; the DNS record still carries the 1.4.1 hash at preparation time.

The DNS value Sam must set on the existing `_assistant-guide` TXT record, single value, before hosted acceptance:

Literal
```text
v=1; sha256=f6f1ce225d2dcafe7e2b9da5e1b8539099e6a602a8d827dd02ed02f0159bc631; url=https://harnessie.com/.well-known/assistant-guide.txt
```

Any further guide byte change invalidates this value and restarts the checkpoint.

## Candidate and deployment completed

The release commit is `4ccf3f304bca0c88c8997c0a0cf33a909145d3ef` on `main`. The locked release gate passed on it: 1,240 tests, 4 skipped, 28 expected failures, 70/70 deterministic evals, trust and inward manifests, authoring validation, dependency locks, the ecosystem manifest, the ten-page search contract, Twine, artifact inspection, the private-path sweep and the fresh-install smoke. Exact-commit ci (37423763122), CodeQL (37423763128), Scorecard (37423763227) and Pages (37423762389) passed. [Live comparison](release-1.5.0/live-bytes.json) verifies eleven served resources byte for byte; the [production search contract](release-1.5.0/production-search.json) covers ten pages with zero defects. The [Scorecard review](release-1.5.0/scorecard-review.json) records the eight sub-10 checks with dispositions unchanged in kind from 1.4.1.

The signed `v1.5.0` tag object is `bbf51b69cfd942af616ace2d752d26b33c337eac`, pointing to that commit. [Verification](release-1.5.0/tag-verification.txt) confirms the SSH signature from the local checkout and a clean clone, GitHub's own verification, and the exact 8,054-byte guide in the clone and on the served site. The sidecar's immutable release URL answers 200.

A local build from the exact commit produced wheel `58cceb921aee68124514894fad072ff76fa1ff066eb99c7ccbb3996e944b06c5`, sdist `fdab8e5a7ccb6d291925eb3f72a60c26b46cf35feda446762de439ba1cb21ad5` and a reproducible CycloneDX 1.6 SBOM `99691b51dc1f42d492a347fa3bbf4e851a26007803bda2222c8f47fc9712029f` ([digests](release-1.5.0/local-build-SHA256SUMS.txt)). These are pre-publication checks; the published assets are built once by the release workflow from the tag.

The [pre-DNS hosted checkpoint](release-1.5.0/guidecheck-before-dns.json) evaluated the served 1.5.0 guide under profile 2.0.0 at Level 3 with one blocker, `anchor.independent.mismatch`: the DNS TXT record still carries the 1.4.1 hash. Four warnings: repository-file evidence does not establish independence (expected under the 1.0.0-strict anchor policy), the served response lacks `X-Content-Type-Options: nosniff` and HSTS headers (GitHub Pages hosting; unchanged from earlier releases), and the package-registry anchor returns 404 because 1.5.0 is not yet on PyPI. Sam has the exact replacement value above.

## Progress

Pending at this point in the record: DNS rotation and hosted GuideCheck acceptance, GitHub Release and PyPI publication through the protected environment, independent package verification, and downstream propagation. Each completed step is appended below with its evidence; [machine-readable state](release-1.5.0-state.json) mirrors them.
