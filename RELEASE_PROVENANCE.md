# Release asset provenance

Current-source implementation, awaiting hosted acceptance on a new release or separately authorized rehearsal. This supplements the existing protected PyPI Trusted Publisher and its attestations.

## Build and verify

After final bytes exist, the release build attests the wheel, source archive, CycloneDX SBOM and checksum file with `actions/attest` v4.2.2, pinned to `1e69f48acb82d1966a394da916b4c1698aa569d6`. The attesting build job alone receives `attestations: write`; it also needs `id-token: write`. PyPI jobs retain their existing OIDC permissions. Attachment and recovery verification use read access to attestations.

The verifier requires exactly the expected wheel, source archive and SBOM entries in the checksum record. Missing files, links, changed bytes, duplicate entries and unexpected paths refuse before GitHub verification. The checksum file is also an attested subject.

GitHub CLI identity selectors are mutually exclusive. Use the exact `--cert-identity`, which binds the workflow path and tag, rather than combining it with `--signer-workflow`.

Each of four `gh attestation verify` calls enforces the Harnessie repository, `.github/workflows/release.yml` signer, exact certificate identity, tag ref, source commit and signer commit, SLSA provenance predicate and GitHub-hosted runners. Digests are rechecked before a receipt is returned. A valid signature from a different source/workflow is insufficient. A receipt records verification; it is not a new signed attestation.

Use a new directory containing downloaded `dist/` and `release/` files. Obtain the expected commit from the independently checked release tag, not an unverified artifact.

Replace: RELEASE_DIRECTORY -> absolute directory containing dist/ and release/
Replace: RELEASE_TAG -> exact stable tag being verified
Replace: RELEASE_COMMIT -> full 40-character commit resolved from that tag
Customize
```bash
python scripts/verify_release_provenance.py --root "RELEASE_DIRECTORY" --tag "RELEASE_TAG" --commit "RELEASE_COMMIT"
```

Success outputs repository, workflow, tag, commit and four digests as JSON. Missing or rejected provenance exits 2. A current authenticated GitHub CLI supporting the enforced options is required; unsupported flags fail rather than weakening the policy.

## Recovery

Recovery downloads existing assets, resolves the original tag commit, and verifies original build provenance before handing unchanged distributions to PyPI. It never runs the attestation action or creates replacement build provenance. Historical releases without this provenance, including 1.2.0, refuse on the new recovery path and require a separately reviewed recovery decision. There is no implicit legacy bypass.

Checksum agreement cannot prove build identity. Build provenance does not prove source correctness, benign dependencies, reviewer independence or human authorization. Mocked local policy tests do not establish hosted cryptographic acceptance. Record all four downloaded subject digests and successful live verification at release closeout.

Primary contracts: [pinned GitHub attestation action](https://github.com/actions/attest/tree/1e69f48acb82d1966a394da916b4c1698aa569d6) and [GitHub CLI policy flags](https://cli.github.com/manual/gh_attestation_verify).
