# Version 1.4.1 preparation

Date: 2026-09-08. Sam selected plain SemVer `1.4.1` for the source package and assistant guide, replacing the proposed separate development-guide identity. Skipping 1.4.0 is intentional. Publication status is recorded separately: source 1.4.1 is unreleased; published core, Action and Homebrew pins remain 1.3.1.

Updated package metadata, guide metadata/sidecar, changelog target, current documentation, machine discovery and planning together. Restored the strict test that guide version equals package version. Rebuilt generated documentation and outward manifest pins. No changes were made to human arbitration records, accessibility, downstream packages or external publication state.

Verification on this working tree:

- 32 version, discovery, guide-artifact and release-check tests passed.
- 66/66 deterministic evals passed; authoring, inward/outward manifests, ecosystem schema and dependency locks passed.
- Nine generated pages are current; ten sitemap pages have zero offline search defects.
- 1.4.1 wheel and source distribution built; Twine, artifact inspection and fresh installed-wheel consumer smoke passed.
- [Local GuideCheck receipt](version-1.4.1/guidecheck-local.json): Level 3, 8,048 bytes, matching local sidecar; exit 1 with the sole blocker `anchor.independent.missing`. Hosted acceptance remains pending for the new bytes.
- Remote tag inspection found no existing `v1.4.*` tags at preparation time. Publication still requires a fresh conflict check across GitHub and the package registry.

The [previous completion audit](aidr-pre-release-completion-2026-09-08.md) retains the earlier full-suite and independent implementation results as a dated snapshot. Its guide and artifact hashes apply to the previous bytes. This version-only pass does not claim a new full release gate, hosted acceptance or publication. Final release notes, exact-commit CI and publication checks remain part of subsequent delivery.

Working-tree fingerprint (sorted source digests, excluding audit artifacts): `fea8dc318c7e8d21740dfca588f5198a9f1730a52d2f8c224557a125dcc50f14`. [Source digests](version-1.4.1/source-digests.json) identify the verified content.

- `harnessie-1.4.1-py3-none-any.whl`: SHA-256 `9952c8f467d47e40033d87e86cf1364307ff81bfd0d1df73ea138489569465eb`
- `harnessie-1.4.1.tar.gz`: SHA-256 `67772356208c2d9c93e8290a204582d04bcfc01e7393077315651ba9466fd825`
