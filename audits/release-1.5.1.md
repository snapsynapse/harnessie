# Harnessie 1.5.1 release execution

Status: partial publication. The signed tag and GitHub Release with all four original-build assets are verified. PyPI publication is waiting for the protected `pypi` environment approval; no PyPI or downstream 1.5.1 claim is made yet. Release-preparation PR [#48](https://github.com/snapsynapse/harnessie/pull/48) merged at `2bb78f24ad029db7e1c1545fdc6ab3a39f808c92` after exact-head CI, CodeQL, Scorecard and Pages workflows passed.

## Source and gates

- Security PR [#46](https://github.com/snapsynapse/harnessie/pull/46) merged at `94d950fa700cad046d6ed78f865f1ff3b39e08f6` after the proxy CONNECT accounting review fix. Its exact-head CI, CodeQL and package checks passed. The [local candidate receipt](release-1.5.1-candidate-2026-11-18.md) records 2,319 passing tests, 76 passing evals, hash-locked build, Twine, artifact inspection and clean-consumer smoke. Those retained local artifacts are test evidence, not release assets.
- Adoption PR [#47](https://github.com/snapsynapse/harnessie/pull/47) merged at `ab3333f6e8798b19d069ce103bae23ff47c6506a` after resolving its README conflict. Its exact-head checks and the merged-main CI, CodeQL, Scorecard and Pages workflows passed. The verifier-first example produced exits 1, 0 and 2 against the combined source.
- The 1.5.1 guide served at `https://harnessie.com/.well-known/assistant-guide.txt` is 8,054 bytes, SHA-256 `3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4`; the served sidecar declares the same hash and profile 2.0.0. Sam replaced the single `_assistant-guide.harnessie.com` TXT value. [Cloudflare](release-1.5.1/dns-cloudflare.json) and [Google](release-1.5.1/dns-google.json) DNS-over-HTTPS now return `v=1; sha256=3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4; url=https://harnessie.com/.well-known/assistant-guide.txt`.

## Revised GuideCheck gate

Harnessie's prior [release checklist](../RELEASE_CHECKLIST.md) required a dated hosted GuideCheck Level 4 result for the final guide before publishing the GitHub Release. GuideCheck's hosted verifier changed on November 12, 2026 at `1377fcc` and now deliberately caps results at Level 3 while reporting fetched anchors as unverified. Its current [README](https://github.com/snapsynapse/guidecheck/blob/main/README.md) and [maintenance record](https://github.com/snapsynapse/guidecheck/blob/main/docs/security/maintenance.md) state that limit. The historical 1.5.0 Level 4 result cannot cover the 1.5.1 bytes. On November 19, Sam directed a change to Harnessie's requirement. The revised pre-publication gate is a dated hosted Level 3 result with zero blockers plus independent matching-hash checks of the served guide, sidecar, DNS TXT, repository pins and signed tag source. It does not establish Level 4 or independently verified provenance.

The [post-DNS hosted result](release-1.5.1/guidecheck-pretag.json) and [final pre-publication hosted result](release-1.5.1/guidecheck-prepublication.json) evaluated the 8,054-byte guide under declared profile 2.0.0 at Level 3 with zero blocking findings, four warnings and two informational findings, including `anchor.hosted.unverified`. They fetched matching DNS and repository-file hashes. The four warnings are repository-file independence unestablished, missing `X-Content-Type-Options: nosniff` and HSTS on the served response, and a package-registry anchor 404 before PyPI publication. DNSSEC was not established. An independent clean clone verified the [signed tag and guide hashes](release-1.5.1/tag-verification.txt). The served guide, sidecar, single DNS TXT value, repository pins and tagged guide copies all match SHA-256 `3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4` and 8,054 bytes. This satisfies the revised Level 3 plus independent-check gate, not Level 4.

## Signed tag and GitHub assets

Signed annotated tag `v1.5.1` is tag object `43956fb1120cc53430dcdfa4c16a1ba944b56788`, resolving to `2bb78f24ad029db7e1c1545fdc6ab3a39f808c92`. A clean clone verified its SSH signature under the established signing key. The [GitHub Release](https://github.com/snapsynapse/harnessie/releases/tag/v1.5.1) was published at 2026-11-19T08:12:43Z and triggered [release workflow 44485696953](https://github.com/snapsynapse/harnessie/actions/runs/44485696953) at that exact commit. Its build and asset-attachment jobs passed. The independent [original-build provenance receipt](release-1.5.1/github-provenance.json) verified all four downloaded assets against the repository, release workflow, signed tag and commit:

| Asset | SHA-256 |
|---|---|
| Wheel | `0c586af43e8585ac57abfbef94611c1993587dbf2ca038dba051a4edc3a93255` |
| Source distribution | `b26dcaed78237219e5408229f88327c335688a3659330f397e0eeb9dc7375c6a` |
| CycloneDX SBOM | `f192bc2a5f22d22b05ab6adbc697af37bab2ca28e59609ee0c680e65332a983b` |
| Checksum record | `5864537aa4afaf7984d1c1d7f6923fcef0cdf8e5032c14bb25dd4e55ca22f710` |

The downloaded wheel and sdist passed artifact inspection and Twine; the wheel passed a clean-consumer fresh-install smoke. These are GitHub assets, not yet PyPI files.

## Remaining publication sequence

1. Approve and complete the protected `pypi` deployment in release workflow 44485696953.
2. Independently verify PyPI's immutable files, attestations, and a fresh public-index installation against the four original-build assets.
3. Update the public release-state surfaces and assess Verify Action and Homebrew pins in their own repositories. Engine wrappers remain an independent train.
