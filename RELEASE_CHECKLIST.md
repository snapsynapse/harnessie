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
- [ ] OPERATOR: bump the brew tap (snapsynapse/homebrew-tap
      `Formula/harnessie.rb`): new sdist URL + sha256 from PyPI, local
      `brew upgrade snapsynapse/tap/harnessie` + `brew test`, then push.
      The 0.7.1 release shipped with the tap still serving 0.6.0 — README
      lists brew and pip as equivalent installs, so tap lag is version skew
      on a public surface.
- [ ] OPERATOR: update the DNS TXT anchor `_assistant-guide.harnessie.com`
      to `v=1; sha256=<guide-sha256>`, single record, then confirm it
      resolves (DoH) and run the hosted GuideCheck verifier for the Level 4
      re-confirmation.

## 6. Close out

- [ ] `NEXT.md` current state reflects the shipped version.
- [ ] `ROADMAP.md` milestone marked shipped.
