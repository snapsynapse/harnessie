# certifi security lock repair, 2026-11-11

## Scope and change

Sam authorized fixing the remaining critical certifi dependency alerts, checks with independent verification, and commit/push, with no inference. Fetched main was clean and synchronized at `ed60ba52d3cd31d795273dfe451c88b5def2718a`. Work is isolated on `codex/certifi-security-fix`.

[Development alert 10](https://github.com/snapsynapse/harnessie/security/dependabot/10) and [release alert 12](https://github.com/snapsynapse/harnessie/security/dependabot/12) identify `certifi==2026.7.22`. The [upstream advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) recommends 2026.10.19 or later after removal of the affected emSign ECC Root CA - G3. Both reviewed locks now pin 2026.10.19.

The existing controlled generator, uv 0.13.4, ran in a disposable CPython 3.12.16 environment. Bootstrap wheels were hash-enforced against official PyPI metadata; no global tool was upgraded. A disposable copy of the inputs temporarily constrained certifi to 2026.10.19, without a broad `--upgrade`. The original inputs were then restored and the unmodified generator ran again with the new pin retained. Only development/release locks and their manifest digests were copied back after validation.

The runtime lock, tooling, input fingerprint, package dependencies, package version and every other locked requirement record and hash remain unchanged. Existing low-severity setuptools alerts 9 and 11 remain separate work. No runtime source or inference transport changed.

## Independent verification

A separate read-only verifier fetched official PyPI metadata independently, compared complete folded requirement records against the starting commit, and confirmed only certifi changed in dev/release. It verified both artifact hashes, all manifest digests and unchanged dependency inputs/runtime lock. All 10 dependency-lock tests passed, including real offline installer refusal of altered wheel bytes and omitted transitive hashes. It independently passed fresh-environment `pip check` and installed development/release lock validation.

The verifier parsed SSL certificate subjects from hash-verified old/new wheels and the installed patched bundle. The old wheel contains emSign ECC Root CA - G3, DER SHA-256 `86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b`; the patched wheel and installed bundle omit it while retaining the other three emSign subjects. This verifies bundled trust-store removal, not the state of every host trust store or an on-path interception test.

| Artifact | SHA-256 |
|---|---|
| certifi 2026.10.19 wheel | `42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b` |
| certifi 2026.10.19 sdist | `035c1e85572b141bf1c3a3eff0e33a8eb74917522f2559075ff8d2fea780a1ae` |
| Development lock | `7d0990c45df562897059757ab0b85c0f9d165afbc2a7c5895a0401b7ccbf362d` |
| Release lock | `56865766b46848a51029380f5d3c0ffa2cffeeecbc1e977c90b2beb4cc74c385` |
| Manifest | `d1e1129c015a7aff8bf4ffe3e1f2fcb48f918c7fef5f0bcb101daabc031b5e9d` |

## Parent acceptance

- Fresh hash-enforced release installation, editable project installation without dependency resolution, `pip check`, and installed dev/release lock validation passed under CPython 3.12.16.
- Full offline suite with native Seatbelt admitted: 1,374 passed, four skipped, 28 expected failures. No inference occurred.
- All 70 deterministic evals, nine configuration documents, outward/inward manifests and ecosystem validation passed.
- Locked package gate passed: generated docs, whitespace, wheel/sdist build, Twine metadata, archive inspection and fresh-install public CLI/mock smoke.
- Patched uv installed the unchanged hash-locked runtime plus the local wheel into another disposable environment; compatibility passed. CycloneDX 7.3.1 generated and validated the release-format SBOM twice with identical bytes, SHA-256 `99691b51dc1f42d492a347fa3bbf4e851a26007803bda2222c8f47fc9712029f`.

No model metadata call, inference, alert dismissal, service change, release tag, package publication or downstream update occurred. GitHub must analyze the pushed default-branch locks and return alerts 10 and 12 as fixed before claiming hosted alert closure. Local correctness and hosted closure are separate checks; exact-commit delivery and returned alert states are retained privately after push.
