# Harnessie 1.5.1 release execution

Status: preparation. This is a package release record, not a publication receipt. The 1.5.1 source is merged on `main` at `ab3333f6e8798b19d069ce103bae23ff47c6506a`; the release-preparation commit, signed tag, GitHub Release, PyPI files and downstream pins are recorded here only after provider verification.

## Source and gates

- Security PR [#46](https://github.com/snapsynapse/harnessie/pull/46) merged at `94d950fa700cad046d6ed78f865f1ff3b39e08f6` after the proxy CONNECT accounting review fix. Its exact-head CI, CodeQL and package checks passed. The [local candidate receipt](release-1.5.1-candidate-2026-11-18.md) records 2,319 passing tests, 76 passing evals, hash-locked build, Twine, artifact inspection and clean-consumer smoke. Those retained local artifacts are test evidence, not release assets.
- Adoption PR [#47](https://github.com/snapsynapse/harnessie/pull/47) merged at `ab3333f6e8798b19d069ce103bae23ff47c6506a` after resolving its README conflict. Its exact-head checks and the merged-main CI, CodeQL, Scorecard and Pages workflows passed. The verifier-first example produced exits 1, 0 and 2 against the combined source.
- The 1.5.1 guide served at `https://harnessie.com/.well-known/assistant-guide.txt` is 8,054 bytes, SHA-256 `3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4`; the served sidecar declares the same hash and profile 2.0.0. Sam replaced the single `_assistant-guide.harnessie.com` TXT value. [Cloudflare](release-1.5.1/dns-cloudflare.json) and [Google](release-1.5.1/dns-google.json) DNS-over-HTTPS now return `v=1; sha256=3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4; url=https://harnessie.com/.well-known/assistant-guide.txt`.

## Revised GuideCheck gate

Harnessie's prior [release checklist](../RELEASE_CHECKLIST.md) required a dated hosted GuideCheck Level 4 result for the final guide before publishing the GitHub Release. GuideCheck's hosted verifier changed on November 12, 2026 at `1377fcc` and now deliberately caps results at Level 3 while reporting fetched anchors as unverified. Its current [README](https://github.com/snapsynapse/guidecheck/blob/main/README.md) and [maintenance record](https://github.com/snapsynapse/guidecheck/blob/main/docs/security/maintenance.md) state that limit. The historical 1.5.0 Level 4 result cannot cover the 1.5.1 bytes. On November 19, Sam directed a change to Harnessie's requirement. The revised pre-publication gate is a dated hosted Level 3 result with zero blockers plus independent matching-hash checks of the served guide, sidecar, DNS TXT, repository pins and signed tag source. It does not establish Level 4 or independently verified provenance.

The [post-DNS hosted result](release-1.5.1/guidecheck-pretag.json) evaluated the 8,054-byte guide under declared profile 2.0.0 at Level 3 with zero blocking findings, four warnings and two informational findings, including `anchor.hosted.unverified`. It fetched matching DNS and repository-file hashes. The four warnings are repository-file independence unestablished, missing `X-Content-Type-Options: nosniff` and HSTS on the served response, and a package-registry anchor 404 before PyPI publication. DNSSEC was not established. After the tag exists, independently check the immutable tag source and obtain a final hosted result for the unchanged guide before GitHub Release publication.

## Pending publication sequence

1. Land the final release-preparation commit on main and verify exact-commit CI.
2. Create and independently verify signed annotated tag `v1.5.1` at that commit.
3. Recheck served guide, sidecar, DNS TXT and tagged source; obtain a dated hosted GuideCheck Level 3 result under profile 2.0.0 with zero blockers and preserve the independent matching-hash receipt.
4. Publish the GitHub Release only after the guide gate is resolved. The release workflow must build and attest the wheel, sdist, CycloneDX SBOM and checksums from the tag, attach those original assets, then publish to PyPI through its protected environment.
5. Independently verify all assets and PyPI attestations, install from the public index in a fresh consumer, then update Verify Action and Homebrew through their own release checks.
