# Release checklist

The promotion path for a tagged Harnessie release. Steps that touch the
network or public state (PyPI, GitHub releases, DNS) are operator acts and
are marked OPERATOR. Everything else is a working-tree change committed on
`main` before the tag.

## 1. Land the release content

- [ ] All milestone acceptance criteria green (`ROADMAP.md` for the version).
- [ ] `python3 -m pytest -q` clean; note the exact `N passed / M skipped`.
- [ ] `python3 -m harness.cli eval` clean; note `K/K`.
- [ ] `python3 -m harness.cli verify-manifest` passes.
- [ ] `git diff --check` clean.
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
      `registry-url`, `last-reviewed`; correct the verification counts in the
      acceptance checklist to match step 1.
- [ ] Copy to `docs/.well-known/assistant-guide.txt` (must be byte-identical).
- [ ] `docs/.well-known/assistant-guide-manifest.txt`: recompute
      `guide-sha256` and `guide-bytes`; set `guide-version` and
      `immutable-release-url` to the new tag.
- [ ] Re-pin the three guide files in `docs/MANIFEST.yaml`.
- [ ] `tests/test_guide_artifacts.py` and `tests/test_trust_manifest.py` green.

## 4. Build and verify artifacts

- [ ] `rm -rf dist build harnessie.egg-info && pyproject-build`.
- [ ] `twine check dist/*` PASSED for wheel and sdist.
- [ ] Sweep the sdist for private paths and scrub-list terms:
      `tar tzf dist/*.tar.gz | grep -iE 'ROADMAP-PRIVATE|handoffs|runs/|workspace/|\.env'`
      returns nothing, and the artifact bytes contain no scrub-list term.
- [ ] LICENSE and NOTICE present in both artifacts; metadata `Version` correct.
- [ ] Fresh-venv install smoke: import the package and run `harnessie --help`.

## 5. Tag and publish

- [ ] Commit steps 2-3 on `main` and push.
- [ ] Annotated tag `git tag -a vX.Y.Z -m "..."`, push the tag.
- [ ] OPERATOR: `gh release create vX.Y.Z dist/* --title ... --notes-file ...`
      (attaching the built artifacts makes the sidecar
      `immutable-release-url` resolve).
- [ ] OPERATOR: `twine upload dist/*` (irreversible; a PyPI version can be
      yanked but never replaced). Verify a fresh `pip install harnessie`
      from the live index.
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
      re-confirmation.

## 6. Close out

- [ ] `NEXT.md` current state reflects the shipped version.
- [ ] `ROADMAP.md` milestone marked shipped.
- [ ] `python3 scripts/ecosystem_status.py` reports the action and Homebrew
      core pins matching the released version, or `NEXT.md` names the
      intentional lag, owning repository, and follow-up pull request.
- [ ] Release notes record the core, verify-action, Homebrew formula, and
      engine-wrapper versions observed at close-out.
