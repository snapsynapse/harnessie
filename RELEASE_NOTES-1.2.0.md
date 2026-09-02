# Harnessie 1.2.0: verify agent-produced changes

Harnessie 1.2.0 makes `harnessie verify` the smallest independently useful adoption surface. It binds claims to exact evidence, runs deterministic checks before model judgment, and derives a fail-closed exit from complete required-claim coverage. The full harness remains the growth path for consent, ownership lanes, containment, human arbitration, and tamper-evident audit.

## Highlights

- A v1 evidence bundle binds stable claim IDs to an exact Git revision and dirty state, content-addressed diffs and proof files, and recorded deterministic checks. Unsafe paths, stale state, missing bindings, and hash drift refuse before model dispatch.
- Structured claim results classify every required claim as `reproduced`, `refuted`, or `not_verifiable`. Overall exit 0, 1, or 2 follows deterministically from complete claim coverage; legacy raw criteria remain compatible.
- OpenAI Responses is now a first-class adapter for current reasoning models, stateless encrypted-reasoning replay, strict function tools, response validation, and usage accounting.
- Synthetic Ringer fixtures and trace metrics cover the adoption seam exposed by the first public Ringer cohort, including duplicate denials, repeated tool calls, work steps, token use, and claim coverage.
- Parallel copies of one denied tool call count as one failed turn, allowing a verifier to recover without weakening the tool allowlist.

## Verification and supply chain

- The repository release gate composes the full test suite, 51 deterministic evals, authoring validation, inward and outward trust manifests, generated documentation, artifact inspection, `twine check`, and fresh-install smoke.
- The GitHub release workflow checks out the exact annotated tag, verifies tag/version/commit identity, runs the release gate under admitted Linux bubblewrap confinement, and builds the wheel and source distribution once.
- Those exact distributions are attached to this release with a reproducible CycloneDX 1.6 runtime SBOM and SHA-256 record, then sent unchanged to PyPI through Trusted Publishing and its protected `pypi` environment. PyPI attestations remain enabled.
- The v1.2.0 tag is annotated but not locally GPG-signed. No project policy requires a maintainer-key tag signature, and adding a long-lived local key would create another identity and rotation surface. The compensating evidence is the exact protected tag commit, GitHub workflow identity, PyPI OIDC attestations, immutable release assets, SBOM, and recorded SHA-256 digests.
- The public OpenSSF Scorecard API returned no result for this repository on 2026-09-01. This is recorded as not yet measured, not as a zero or a pass. The absence is accepted for 1.2.0 because the release gate, full commit-pinned workflow, protected environment, OIDC publication, attestations, SBOM, and immutable digests are independently verified; a repository-owned Scorecard workflow remains a post-release measurement task.
- Tag `v1.2.0` peels to release commit `5bb46378464d3636b43762ededc507beb8f7ddf8`. Exact-tag CI run [33581149207](https://github.com/snapsynapse/harnessie/actions/runs/33581149207) passed, and the [GitHub Release](https://github.com/snapsynapse/harnessie/releases/tag/v1.2.0) was published on 2026-09-02 UTC.
- The original release run [33581366424](https://github.com/snapsynapse/harnessie/actions/runs/33581366424) built and verified the release artifacts but failed only while attaching them because its no-checkout job lacked explicit repository identity. The exact artifacts were recovered and attached without rebuilding. Recovery run [33583589070](https://github.com/snapsynapse/harnessie/actions/runs/33583589070) then verified their checksum record and published those same bytes to PyPI through the protected environment.
- SHA-256 digests are wheel `9d1b92c3204db49154f1a1d997bcdd3aa4e3bb2fd11b22f83336dab339f65b47`, source distribution `b0f0c769dd43853b2b724b1c5cb70f1eaea35e07d6f0d2224cdaf2946103c49d`, CycloneDX SBOM `9d42d77bdeefecd3c44193b58c9e954f1d5970d48781453a70fea6093b5db0b6`, and checksum record `3a8d78321f2d6d5de23a4ab85a810e8fc8599bc38e9f52ce63a8856634e492f0`.
- PyPI's integrity record binds the release to `snapsynapse/harnessie`, `.github/workflows/release.yml`, the `pypi` environment, and recovery commit `e4103620faf47ff40043bb4dada71dcab0fdde88`. Both distribution attestations verified, their PyPI hashes match the GitHub Release assets, and a clean Python 3.13 public-index install reported package version 1.2.0 and exposed `--evidence-bundle` and `--evidence-root`.

## Trust and downstream boundaries

- Manual keyboard-only, 200% zoom/reflow, and screen-reader testing was not completed before publication. On 2026-09-01 the release owner explicitly authorized a one-time 1.2.0 waiver after reviewing that gap. Automated Lighthouse 13.4.1 checks scored 1.00 with no failing accessibility audits on the homepage and all nine generated routes, but that evidence is not represented as a substitute for assistive-technology testing. The manual gate remains required for later releases.
- The 1.2.0 assistant guide, served copy, provenance sidecar, and repository trust pins move together. Its new DNS TXT anchor and hosted GuideCheck run are separate external gates. The 1.1.0 Level 4 receipt remains dated historical evidence and is not inherited by the new guide bytes.
- Harnessie Verify Action [v0.2.0](https://github.com/snapsynapse/harnessie-verify-action/releases/tag/v0.2.0) and stable `v0` resolve to commit `bc6f94f93cade0e722f525bd0b387005b88cd3a2`. Its [seven-job CI run](https://github.com/snapsynapse/harnessie-verify-action/actions/runs/33584285698) passed, including valid, failing-check, stale-bundle, advisory, legacy, and unsafe-trigger cases.
- Homebrew tap commit `118ca530971f3d4b5fb6100f117f14a96b464fb8` pins the 1.2.0 source distribution at the PyPI digest above. Strict online audit, a real installed 1.1.0 to 1.2.0 upgrade, formula test, linkage, package metadata, and evidence-bundle CLI smoke passed.
- Engine wrappers retain their independent probe-gated release train because 1.2.0 consumes no new versioned wrapper seam.

The complete change record is in [CHANGELOG.md](https://github.com/snapsynapse/harnessie/blob/v1.2.0/CHANGELOG.md#120-2026-09-01).
