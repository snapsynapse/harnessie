# Release checklist

Current completed release: [Harnessie 1.5.0](audits/release-1.5.0.md). Core GitHub/PyPI publication and verification are complete: the GitHub Release from signed tag `v1.5.0` carries provenance-verified original-build assets, both PyPI distributions match them and pass publisher verification, and a fresh public-index consumer installed 1.5.0. Downstreams still serve 1.4.1: Verify Action 0.2.2 and stable `v0` pin core 1.4.1 at `9f18d70017f395ef4d15ac5746e30ac633f00f8e` while the 0.2.3 bump is in progress at https://github.com/snapsynapse/harnessie-verify-action/pull/4 (seven fixtures green, not merged); Homebrew 1.4.1 at tap commit `953760f3968200f99658bfb068609532cb9fbf4d` remains current while the 1.5.0 Homebrew 1.5.0 formula is in progress at https://github.com/snapsynapse/homebrew-tap/pull/5, where the exact formula passed `brew audit --strict --online`, a real 1.4.1 to 1.5.0 upgrade, `brew test` and `brew linkage --test`; it is not merged. Engine wrappers remain independently released at 0.1.0.

The final 1.5.0 guide earned [hosted Level 4 under profile 2.0.0](audits/release-1.5.0/guidecheck-prepublication.json) on 2026-10-06 with zero blocking findings and a qualifying DNS anchor before the GitHub Release was published. Its frozen bytes remain unchanged. Sam retained the accessibility deferral for this release sequence; no fresh accessibility pass is claimed.

Historical completed executions: [Harnessie 1.4.1](audits/release-1.4.1.md), including core GitHub/PyPI, Verify Action 0.2.2 and Homebrew 1.4.1, whose guide earned [hosted Level 4](audits/release-1.4.1/guidecheck-prepublication.json) for its own bytes; and [Harnessie 1.3.1](audits/release-1.3.1.md), including core GitHub/PyPI, Verify Action 0.2.1 and Homebrew 1.3.1. The checklist below remains the reusable release procedure; current results live in the dated execution record.

The promotion path for a tagged Harnessie release. Steps that touch the
network or public state (PyPI, GitHub releases, DNS) are operator acts and
are marked OPERATOR. Everything else is a working-tree change committed on
`main` before the tag.

## 1. Land the release content

- [ ] `python3 scripts/dependency_locks.py` passes; locked CI/build environments
      and the separate public-constraint consumer job both pass. See
      `requirements/README.md` for installation and update boundaries.
- [ ] `python3 scripts/release_gate.py` passes. This composes the source
      checks below with generated-doc verification, an isolated wheel/sdist
      build, metadata and private-surface inspection, and a fresh-venv CLI
      smoke test.
- [ ] All milestone acceptance criteria green (`ROADMAP.md` for the version).
- [ ] Any earlier roadmap follow-up still marked open is green or has an
      arbitrated replacement. The current Siteline 90+ gate requires a dated
      live result, not a local scoring prediction.
- [ ] `python3 -m pytest -q` clean; note the exact `N passed / M skipped`.
- [ ] `python3 -m harness.cli eval` clean; note `K/K`.
- [ ] `python3 -m harness.cli verify-manifest` passes.
- [ ] `python3 -m harness.cli verify-inward-manifest` passes.
- [ ] `python3 -m harness.cli validate` passes all shipped authoring documents.
- [ ] `git diff --check` clean.
- [x] For the 1.3.0 scope and corrective 1.3.1 package, Sam explicitly deferred the remaining accessibility review
      and authorized publication; see audits/release-1.3.0.md. Preserve the
      36 unresolved candidates and manual work as follow-up, without a pass claim.
      For later releases, manual accessibility evidence should cover changed routes:
      keyboard-only navigation and controls, 200% zoom/reflow, and at least
      one screen-reader pass. Record the date, route set, OS, browser, and
      assistive technology; do not substitute Lighthouse for this check.
- [ ] `python3 scripts/ecosystem_status.py --validate` passes and
      `ECOSYSTEM.md` still describes the intended dependency direction.

## 2. Version and docs

- [ ] `pyproject.toml` `version` bumped; `description` current.
- [ ] Landing page version pills (`docs/index.html`) match the new version
      (enforced by `tests/test_version_sync.py`; a stale pill is a red suite).
- [ ] `CHANGELOG.md`: cut `Unreleased` into a dated version section; open a
      fresh empty `Unreleased`.
- [ ] Doc pass for any new surfaces (ARCHITECTURE.md, docs/GUIDE.md); run
      `scripts/build_docs_html.py` and commit source + generated HTML.

## 3. GuideCheck resync (if the guide changed)

- [ ] `assistant-guide.txt`: bump `guide-version`, `applies-to`,
      `registry-url`, `last-reviewed`; update the verification language in the
      acceptance checklist to require actual results and tested revision, not
      fixed historical test counts. Select the intended GuideCheck profile
      explicitly; profile 2.0.0 requires matching profile selectors in its sidecar.
- [ ] Copy to `docs/.well-known/assistant-guide.txt` (must be byte-identical).
- [ ] `docs/.well-known/assistant-guide-manifest.txt`: recompute
      `guide-sha256` and `guide-bytes`; set `guide-version` and
      `immutable-release-url` to the new tag.
- [ ] Re-pin the three guide files in `docs/MANIFEST.yaml`.
- [ ] `tests/test_guide_artifacts.py` and `tests/test_trust_manifest.py` green.

## 4. Build and verify artifacts

- [ ] Build the final artifacts from the exact release commit into an empty
      `dist/` with `python3 -m build`.
- [ ] `twine check dist/*` PASSED for wheel and sdist.
- [ ] Sweep the sdist for private paths and scrub-list terms:
      `tar tzf dist/*.tar.gz | grep -iE 'ROADMAP-PRIVATE|handoffs|runs/|workspace/|\.maiden/|\.env'`
      returns nothing, and the artifact bytes contain no scrub-list term.
- [ ] LICENSE and NOTICE present in both artifacts; metadata `Version` correct.
- [ ] Fresh-venv install smoke: import the package and run `harnessie --help`.

## 5. Tag and publish

- [ ] For the 1.3 release scope, satisfy Sam's 2026-09-07 pre-publication GuideCheck gate:
      final served guide, sidecar, repository pins and DNS TXT agree, and a
      dated hosted result verifies those exact bytes under profile 2.0.0.
      GuideCheck is now in scope; see the candidate and current-guide evidence
      in audits/guidecheck/2026-09-08/README.md. Complete final acceptance before
      publishing the GitHub Release, which triggers the package workflow,
      and before PyPI, Verify Action or Homebrew publication. If immutable
      tag identity is needed, create the approved tag first, then verify
      the guide while the GitHub Release remains unpublished. Independently
      check its immutable tag-source URL and tag-to-commit identity; require
      profile 2.0.0 in the hosted request. Any guide
      byte change invalidates the earlier result. The protected `pypi`
      environment remains a second publication checkpoint; recovery must
      respect this requirement as well. This is an operator checklist gate,
      not a newly implemented workflow enforcement check.
- [ ] Commit steps 2-3 on `main` and push.
- [ ] Record the release-signing decision for this version. If signed tags or
      commits are required, verify the signature from a clean clone before
      publication; otherwise record the explicit rationale and compensating
      immutable digest evidence.
- [ ] Generate the release-level CycloneDX SBOM from the final wheel in a
      clean runtime environment and record its SHA-256 alongside the exact
      release commit and artifact digests.
- [ ] Review the current OpenSSF Scorecard result and resolve or explicitly
      accept release-relevant findings. Do not add a score badge unless the
      result is current and its limits are explained.
- [ ] Annotated tag `git tag -a vX.Y.Z -m "..."`, push the tag. If the release
      requires a signed tag, use the approved signing path instead.
- [ ] OPERATOR: publish the GitHub Release from the exact annotated tag with
      `gh release create vX.Y.Z --title ... --notes-file ...`. The release
      workflow builds once from that tag and attaches its exact wheel, sdist,
      CycloneDX SBOM, and checksum record before PyPI publication.
- [ ] OPERATOR: publish to PyPI through the repository's GitHub Actions
      Trusted Publisher and protected release environment. The workflow must
      build from the exact tag, require the configured environment approval,
      and expose PyPI attestations. A local `twine upload` is an emergency
      fallback only under separate explicit authority and a recorded reason.
- [ ] Verify the immutable PyPI files, integrity metadata, attestations, and a
      fresh `pip install harnessie` from the live index against the recorded
      artifact digests.
- [ ] Download the GitHub wheel, source archive, SBOM and checksum record and
      run `scripts/verify_release_provenance.py` against the independently
      resolved release tag and commit. Record all four verified digests.
      Follow `RELEASE_PROVENANCE.md`; recovery must verify original build
      provenance and must not re-attest downloaded historical bytes.
- [ ] OPERATOR: test the released core version in
      `snapsynapse/harnessie-verify-action`, update the default
      `harnessie-version` pin in `action.yml`, run its full CI, and release a
      new action version plus stable-major tag when the pin changes.
- [ ] OPERATOR: bump the brew tap (snapsynapse/homebrew-tap
      `Formula/harnessie.rb`): new sdist URL + sha256 from PyPI, local
      `brew upgrade snapsynapse/tap/harnessie` + `brew test`, then push.
      The 0.7.1 release shipped with the tap still serving 0.6.0 — README
      lists brew and pip as equivalent installs, so tap lag is version skew
      on a public surface.
- [ ] Do not bump `harnessie-engine-wrappers` merely because core released.
      It has an independent probe-gated train until Harnessie consumes a
      versioned verification seam. If that seam changed, run the wrapper's
      live platform probe and release checklist independently.
- [ ] OPERATOR: update the DNS TXT anchor `_assistant-guide.harnessie.com`
      to `v=1; sha256=<guide-sha256>`, single record, then confirm it
      resolves (DoH) and run the hosted GuideCheck verifier for the Level 4
      re-confirmation. For 1.3.0 this must be completed at the earlier
      pre-publication checkpoint, not deferred to downstream closeout.

## 6. Close out

- [ ] `NEXT.md` current state reflects the shipped version.
- [ ] `ROADMAP.md` milestone marked shipped.
- [ ] `python3 scripts/ecosystem_status.py` reports the action and Homebrew
      core pins matching the released version, or `NEXT.md` names the
      intentional lag, owning repository, and follow-up pull request.
- [ ] Release notes record the core, verify-action, Homebrew formula, and
      engine-wrapper versions observed at close-out.
