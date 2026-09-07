# Maintenance packets 1–3 implementation evidence

Date: 2026-09-07. Scope: Harnessie core on `codex/release-maintenance`, based at merged main `7246529`. Sam approved implementation of dependency locks, release provenance and the bounded parser property pilot, then authorized proceeding with delivery. The local verification checkpoint below preceded commit and PR checks; Git history and the PR carry delivery evidence. No version bump or package publication is included.

## Implemented scope

1. Runtime, development and release requirements are fully pinned with SHA-256 hashes and explicit universal markers. The reviewed uv 0.11.8 generator captures dependency/build/tooling inputs and lock digests. Drift and malformed locks refuse. Linux/macOS CI uses hash-enforced installs followed by no-dependency, no-isolation project installation and consistency checks. The locked package gate verifies active installed pins. The original public-constraint package job and fresh consumer remain independent. Weekly refresh produces a reviewable patch artifact with read-only repository permission. See [lock policy](../requirements/README.md).
2. Release builds attest wheel, source archive, SBOM and checksum bytes with an immutable GitHub action pin. Original build provenance is verified before attachment and before recovery, binding repository, workflow, certificate identity, tag, source commit and signer commit. Historical missing provenance refuses; recovery never re-attests downloaded bytes. Existing protected PyPI attestations remain. See [provenance contract](../RELEASE_PROVENANCE.md).
3. Seven bounded deterministic properties cover evidence intake and structured verdicts, with 200 examples per property, explicit container/string/payload limits and a 500 ms example deadline. Invalid-path cases assert refusal before model or check dispatch. Minimized regressions and three deterministic evals are retained.

## Defects found and fixed

- A list or object in a structured claim's `status` raised `TypeError` during set membership. It now yields `cannot_verify`. Verdict parser identity advances from 2 to 3 so prior parser-specific scorecards cannot be reused as current evidence.
- A NUL-containing evidence path raised `ValueError` from path resolution. It now returns the documented `file.unsafe_path` refusal before dispatch.

The initial property run demonstrated both crashes. It also exposed an incorrect test expectation for the existing digest-error code; that assertion was corrected to `file.hash_mismatch` without changing the valid runtime behavior. Replaying the two new malformed-status evals against the unchanged base parser produced `TypeError`; the current parser refused both, and the valid-claim control passed under both versions.

## Verification observed

| Check | Result |
|---|---|
| Final combined gate in clean, hash-locked CPython 3.12 environment with macOS sandbox access | 572 passed, 1 skipped, 28 existing deferred-feature expected failures, 18.00 seconds |
| Property pilot plus ordinary regression cases | 9 tests passed, 9.43 seconds |
| Deterministic evals | 62/62 passed |
| Lock drift and actual offline pip enforcement | 10 tests passed; modified wheel bytes and an omitted transitive hash refused |
| Native macOS arm64 release-lock installation | Passed with hash enforcement, no-isolation editable install and pip consistency check |
| Linux x86_64 CPython 3.12 release-lock resolution | Dry-run passed; this is resolution evidence, not Linux execution |
| No-index build | Wheel and source archive built with `PIP_NO_INDEX=1` and `--no-isolation` |
| Locked package gate | Installed pins, wheel/source build, Twine, archive inspection and fresh-consumer smoke passed |
| Configuration and manifests | 9 authoring documents, 21 outward files, 16 inward files and 4 ecosystem components passed |
| Public-source checks | Generated docs current; search contract 10 pages, zero defects/infrastructure failures |
| Workflow source | Three YAML files parsed; all embedded shell steps passed syntax checks |

The provenance tests exercise local inventory/digest refusal and the CLI's required verification policy arguments using subprocess doubles. They do not prove a real GitHub signature or hosted authorization. The locked build still trusts the Python/pip bootstrap, runner and operating-system package substrate; it is not a fully hermetic build claim.

The earlier restricted run reported 563 passed and 9 skipped. The final run added one malformed-checksum encoding regression and exercised eight previously sandbox-skipped cases with elevated execution. It reran the complete source and package gate after the final code changes; the counts are observations of those environments, not interchangeable claims.

## Remaining acceptance and ownership boundaries

- Run the changed CI on the delivered commit to establish hosted Linux/macOS and locked-package execution. No hosted result from the earlier observer PR is reused for these changes.
- Verify all four newly attested downloaded assets during a separately authorized release or controlled rehearsal. No attestation publication or release occurred in this local implementation pass.
- The weekly refresh workflow is implemented but has not executed on GitHub in this pass.
- Stable package version and public release-surface preparation remain steps 4–6 of the larger plan. Project version stays 1.2.0; local test builds are not a replacement release.
- GuideCheck and a11y work remains with the concurrent session. No website, guide, trust-anchor or accessibility artifact was changed here. Reconcile that session before beginning those release surfaces.
- Sole-maintainer provider-rule activation, all bidding modes, commentary, follow mode, runner integration and model selection remain outside this scope.
