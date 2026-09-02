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
- Exact counts, commit, workflow URLs, digests, PyPI attestation results, and downstream versions are verified during release closeout in `CHANGELOG.md` and `NEXT.md`; they are not invented in advance here.

## Trust and downstream boundaries

- Manual keyboard-only, 200% zoom/reflow, and screen-reader testing was not completed before publication. On 2026-09-01 the release owner explicitly authorized a one-time 1.2.0 waiver after reviewing that gap. Automated Lighthouse 13.4.1 checks scored 1.00 with no failing accessibility audits on the homepage and all nine generated routes, but that evidence is not represented as a substitute for assistive-technology testing. The manual gate remains required for later releases.
- The 1.2.0 assistant guide, served copy, provenance sidecar, and repository trust pins move together. Its new DNS TXT anchor and hosted GuideCheck run are separate external gates. The 1.1.0 Level 4 receipt remains dated historical evidence and is not inherited by the new guide bytes.
- Harnessie Verify Action and Homebrew are separately released downstreams. Do not assume they expose the 1.2.0 evidence-bundle contract until their own pins and gates are verified.
- Engine wrappers retain their independent probe-gated release train because 1.2.0 consumes no new versioned wrapper seam.

The complete change record is in [CHANGELOG.md](https://github.com/snapsynapse/harnessie/blob/v1.2.0/CHANGELOG.md#120-2026-09-01).
