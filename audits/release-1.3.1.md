# Harnessie 1.3.1 corrective release

Scope: complete the authorized 1.3 feature release without changing the signed 1.3.0 tag or weakening original-build verification. The feature scope and Sam's explicit accessibility-review deferral remain as recorded in [the 1.3.0 execution record](release-1.3.0.md).

## Cause and correction

The 1.3.0 workflow passed exact-tag tests, built the final assets and signed their provenance. GitHub CLI then rejected the verifier command because `--signer-workflow` and `--cert-identity` are mutually exclusive. The old tests intercepted subprocess calls and did not exercise CLI parsing. Attachment and PyPI jobs correctly remained skipped; the original build outputs were not retained because upload steps followed the failure.

The corrected command uses only the exact certificate identity, which already binds repository, workflow path and tag. Repository scope, source tag, source commit, signer commit, SLSA predicate and hosted-runner restriction remain enforced. The regression asserts exactly one identity selector and both commit bindings. All 11 provenance tests pass. A real GitHub CLI 2.98.0 negative control accepts the corrected arguments and refuses a file without attestations, rather than failing argument parsing.

The build now retains distribution and integrity artifacts even if a later verification step fails, allowing diagnosis or verified recovery of the original bytes. Release attachment still requires a successful build job, and PyPI still requires successful build and attachment jobs. Artifact retention does not authorize publication or bypass provenance checks.

## Release gates

The signed 1.3.0 tag and failed run remain intact. Corrective version 1.3.1 carries the same offline observer, maintenance and accessibility repairs with the publication-tool correction. Its guide differs only in guide-version and registry URL; applies-to remains Harnessie 1.3.x. Final SHA-256 is `ef62ac6ecc50f1f277dda119299d1b145e0aae66a51bcf47ba233e23c072409b` (7,766 bytes). It requires a matching Namecheap DNS change and new hosted receipt before publication.

The existing dated Siteline 97/100 result covers the same feature/site structure before this corrective version label; final deployed-byte and production-search checks will verify the corrective source. A fresh hosted GuideCheck result, signed immutable tag identity, exact-commit CI, original-build verification, PyPI attestations/consumer checks and separately tested downstream publication remain required.

Publication authority comes from Sam's instruction to complete full package publishing. The assistant selected a corrective patch version to preserve immutable release history; no additional feature or provider-policy scope was added. The machine-readable state is [release-1.3.1-state.json](release-1.3.1-state.json).

## Local candidate verification

The locked release gate passed with 572 tests passed, 1 skipped and 28 expected failures; all 62 deterministic evaluations passed. Dependency locks, authoring and manifest checks, generated docs, wheel and sdist inspection, Twine metadata and a fresh installed consumer passed. The search contract checked 10 pages with zero defects. Final publication still requires exact-commit CI and the hosted/provider gates above.
