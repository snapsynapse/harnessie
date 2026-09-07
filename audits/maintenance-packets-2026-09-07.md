# Post-1.2 maintenance implementation packets

Date: 2026-09-07. Scope: Harnessie. The proposals below preserve their preparation baseline. Sam subsequently approved packets 1–3; their local implementation and verification are recorded in [the implementation audit](maintenance-implementation-2026-09-07.md). Packet 4 remains a proposal. No provider rule or release has been changed.

## 1. Hash-verified CI dependencies

Owner files: `pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, a new `requirements/` lock directory and lock validation/update scripts. Keep runtime public constraints unchanged.

Current CI uses Python 3.12 and editable `.[dev]` resolution in each job. Release adds separately pinned uv and CycloneDX tooling. Build isolation can resolve setuptools independently. A lock that covers only pytest would leave material dependency resolution outside its scope.

Proposed implementation:

1. Generate complete SHA-256 requirements for development and release tooling, including transitive and build dependencies. Cover Linux and macOS Python 3.12 with explicit environment markers or separate locks where resolution differs.
2. Install with explicit hash enforcement, then install local source without resolving dependencies or an unpinned isolated build environment. Check installed dependency consistency.
3. Store generator version, input digest and supported environment identity. A deterministic validator rejects changed dependency inputs, missing hashes, duplicate/conflicting entries, and missing lock coverage. Scheduled refresh proposes a reviewable diff; it does not silently update locks during CI.
4. Preserve an independent fresh-install/package job against the public dependency constraints. Passing a pinned environment does not establish the entire supported range. Add a lower-bound compatibility job if that broader claim is desired.

Acceptance: both supported CI environments install from locks; tampered wheel bytes and omitted transitive hashes fail; changing a dependency input without regenerating its lock fails; package/fresh-install checks remain green. Test the isolation boundary explicitly so a build backend cannot be downloaded outside the lock unnoticed.

Hash enforcement requires every dependency to be pinned and hashed. See [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/).

## 2. GitHub release-asset provenance

Owner files: `.github/workflows/release.yml`, release verification script/tests and release checklist. Preserve existing PyPI attestations and protected publication environment.

The existing build job produces final distributions, a reproducible SBOM and a checksum record. The attach job downloads and uploads those outputs; the recovery path can publish prior assets without rebuilding.

Proposed implementation: after final bytes are complete, attest the exact wheel, source distribution, SBOM and checksum file in the build job. Pin the reviewed attestation action to an immutable commit. Grant `id-token: write` and `attestations: write` only to the attesting job, alongside read-only content access. Verify downloaded release assets against both expected subject digests and the repository/workflow identity before accepting closeout.

Recovery must verify existing original build provenance and preserve it. If unavailable, report that limitation and require a separate decision; do not issue new build provenance for downloaded bytes as though recovery built them. A newly attached historical asset is not automatically a newly attested build.

Acceptance: all four asset classes verify after download; modified bytes and incorrect repository/workflow identities fail; checksum subjects agree with downloaded assets; recovery retains original provenance. Hosted acceptance requires a separately authorized release or controlled provider exercise. Local fixtures cannot earn it.

See [GitHub artifact attestation guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations). Resolve the current action commit and verification CLI flags during implementation rather than copying a moving tag into the workflow.

## 3. Bounded parser property-testing pilot

Owner files: `tests/` property tests, bounded checked-in fixtures, development dependencies and the CI test job. First targets: `harness/verify_evidence.py` and structured verdict parsing. Later packets may add workflow/schema, event-journal and resume-state inputs.

Use a property-based generator with a deterministic CI profile: 200 examples per property, bounded strings and collections, depth at most eight, no network or model calls. Target wall time is under 60 seconds for the pilot. Separate measured resource exhaustion from parser semantics; do not hide timeouts by catching every exception.

Properties: valid minimal inputs remain admissible; unsafe paths and digest changes refuse before dispatch; absent required claims cannot produce a passing verdict; malformed JSON/types yield documented refusal/error rather than an uncaught crash. Assert on structured outcomes and use positive controls. Preserve a minimized crash as a normal deterministic regression fixture. Pin the property-testing dependency through packet 1 before CI activation, or explicitly review its interim install path.

Acceptance: bounded CI runtime, reproducible failing seeds, zero external calls, refusal-path spies, and deterministic regressions for every discovered defect. Expanding to all parsers is a follow-up, not the initial pilot.

## 4. Sole-maintainer branch policy

Sam confirmed sole-maintainer operation on 2026-09-07. Current provider observation: active `prime` ruleset targets the default branch with deletion and non-fast-forward restrictions, no bypass actors. Classic branch protection is absent. Preserve `prime` separately.

Propose an additional default-branch ruleset requiring pull requests, resolved review conversations, and current-head checks: `linux-bwrap`, `macos`, `linux-no-backend-fails-closed`, `package`, and CodeQL `Analyze Python`. Before activation, resolve exact check contexts and their GitHub App identity from a real PR, and verify fork PRs emit them. Require an up-to-date branch. Do not require a second human approval or approval of the latest push while no independent reviewer is available.

No routine bypass actor. Emergency recovery: Sam explicitly authorizes a temporary change to the new merge-gate ruleset, records reason, exact before/after settings and affected revision, then restores and verifies it immediately after the recovery PR. Keep deletion/force-push restrictions in `prime` active. Do not require Pages deployment as a pre-merge check because it follows main publication. Preserve the protected PyPI environment and explicit release authorization; branch acceptance is not release authorization.

Activation acceptance: export settings before mutation; exercise a passing PR, a failing required check and a direct-push refusal with Sam's explicit provider authority; rehearse emergency restoration; read back the final rules. Evaluate mode may depend on account capability, so do not assume it is available. Until those checks occur this is a policy proposal, not enforced protection.

See [GitHub ruleset controls](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
