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

## Progress

Pending at this point in the record: release documentation tranche, local release gate, exact-commit CI on the release commit, served-byte comparison, signed tag, DNS rotation and hosted GuideCheck acceptance, GitHub Release and PyPI publication through the protected environment, independent package verification, and downstream propagation. Each completed step is appended below with its evidence; [machine-readable state](release-1.5.0-state.json) mirrors them.
