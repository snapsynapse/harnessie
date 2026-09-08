# Harnessie 1.3.1: offline observation and verified release integrity

Published on GitHub and PyPI on 2026-09-08 UTC, with verified original-build assets and PyPI attestations. Verify Action 0.2.1/stable v0 and Homebrew 1.3.1 are also published and tested.

Harnessie 1.3.1 adds offline run observation and strengthens release integrity while retaining the stable 1.x authoring and plugin contracts.

The initial 1.3.0 workflow stopped before asset upload and PyPI publication because of mutually exclusive provenance CLI flags. This corrective release fixes that invocation while preserving exact certificate/workflow/tag and commit verification. The original signed tag remains unchanged.

## Included

- `harnessie observe RUN_ID` verifies an existing local journal snapshot and writes cited JSON and Markdown without model calls, runner integration, source-journal changes or approval changes. Exit 0 means observation succeeded, not that the run passed.
- Hash-verified runtime, development and release locks, including patched uv 0.11.15 tooling, with separate public-constraint consumer coverage.
- Original-build provenance enforcement for the wheel, source archive, CycloneDX SBOM and checksum record. Recovery refuses historical assets without qualifying original provenance.
- Bounded parser properties and refusal fixes for non-string claim statuses and NUL-containing evidence paths. Verdict parser identity advances to 3.
- Keyboard-focusable documentation scrolling regions, visible focus, homepage contrast improvements and preserved text alternatives.
- A current profile-2.0.0 assistant guide, synchronized trust artifacts and complete observer CLI documentation.

## Verification

The full local locked gate passed: 572 tests, one environment-dependent skip, 28 expected failures for deliberately deferred features, 62/62 deterministic evals, both manifests, package inspection and a fresh-install observer smoke. Final source CI covers Linux sandboxed execution, fail-closed execution without a sandbox, macOS, public-constraint packaging and locked packaging.

The final 1.3.1 guide earned hosted GuideCheck Level 4 under profile 2.0.0 on 2026-09-08 UTC, with zero blocking findings. Served, sidecar, DNS and repository bytes agree on SHA-256 `ef62ac6ecc50f1f277dda119299d1b145e0aae66a51bcf47ba233e23c072409b`. This verifies guide provenance and structure, not software safety or runtime execution.

[Live Siteline](https://github.com/snapsynapse/harnessie/blob/main/audits/release-1.3.0/siteline.json) scored 97/100, grade A, on 2026-09-08 UTC. The production search contract passed across ten sitemap pages.

## Scope and follow-up

AIDR-0009 continues to defer bidding, commentary, follow mode, automatic runner integration and model selection. Four confirmed serious accessibility violations and 22 review candidates were repaired. The maintainer explicitly deferred the remaining 35 table-contrast review candidates, one video-caption applicability candidate and manual accessibility acceptance as nonblocking follow-up. The automated audit remains inconclusive, with zero confirmed violations; this release does not claim complete accessibility conformance.

The release workflow builds and attests four final assets, verifies original build identity and publishes the same distributions through the protected PyPI Trusted Publisher. Verify Action and Homebrew propagate separately after core publication; engine wrappers retain their independent release train. [Execution and delivery evidence](https://github.com/snapsynapse/harnessie/blob/main/audits/release-1.3.1.md) records the exact outcomes.

## Published assets

| Asset | SHA-256 |
|---|---|
| harnessie-1.3.1-py3-none-any.whl | `2de49487168fd58ac77c8a7aa44a024a0adb0239571fc2f0292966c9dd5d42cd` |
| harnessie-1.3.1.tar.gz | `fe250f5c86f993ec9af5723e85f42c57f0889c195ad2e57726d8782f827bb520` |
| harnessie-1.3.1.SHA256SUMS | `37b9497b392a61e2fb6c1df0e82303c97168b7adddf979766d3fa52ea5bd8fca` |
| harnessie-1.3.1.cdx.json | `3b82707a4e654a969c969766eacb9e3a68134b5e1fa52c0e0dc75e609f278da6` |

Core tag `v1.3.1` resolves to `6ddf84429ab8fbfa9ec96e59b283cf7cb341dd6f`. Verify Action `v0.2.1` and stable `v0` resolve to `97ed2264818fc4c620c03de5cc9522965318079b`; Homebrew formula commit is `630021462ef961669a0802d090c7c77c65190932`. Engine wrappers remain 0.1.0 on their independent train.
