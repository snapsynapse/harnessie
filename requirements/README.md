# Controlled build dependencies

These pip-compatible SHA-256 locks cover the controlled CPython 3.12 Linux x86_64 and macOS arm64/x86_64 environments. The runtime package's public dependency ranges and Python support declaration are unchanged. Universal resolution retains platform/Python markers; it is not evidence that every future interpreter or platform was exercised.

- `runtime.txt`: dependencies installed with the final wheel in the SBOM environment.
- `dev.txt`: runtime, development/property-testing tools and build backend.
- `release.txt`: development/build dependencies plus pinned uv and CycloneDX tooling.
- `tooling.json`: reviewed resolver version and supported environment identities.
- `manifest.json`: dependency-input fingerprint and exact lock digests. Release-version-only edits do not invalidate it.

## Validate and install

Run from the repository root in a clean Python 3.12 virtual environment. The Python distribution and bundled pip are bootstrap trust inputs; these files do not lock operating-system packages, GitHub runner images, or Actions.

Literal
```bash
python scripts/dependency_locks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements/release.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
python scripts/dependency_locks.py --installed release
python scripts/release_gate.py --locked-build
```

The locked build checks installed versions before disabling build isolation. Release and locked-package jobs use this path. The separate `package` CI job deliberately resolves public constraints with normal build isolation, retaining independent consumer evidence. Fresh-install smoke also remains a clean consumer, not proof that all permitted dependency versions work.

## Review an update

Install the reviewed release lock first so uv matches `tooling.json`. Regeneration preserves resolutions unless `--upgrade` is supplied. Runtime pins constrain the other profiles so the SBOM environment uses the same runtime versions.

Literal
```bash
python scripts/dependency_locks.py --update --upgrade
git diff -- requirements/
python -m pytest -q tests/test_dependency_locks.py
```

Review changes, then prove clean installs and CI before merging. Changed dependency ranges, build requirements or generator settings without refreshed locks fail validation. The weekly refresh workflow produces a patch artifact only; it cannot commit, push or publish. A maintainer must review and apply it, then run the gates. Generator and fixed release-tool upgrades require explicit edits to `tooling.json`.

The manifest detects drift, not malicious coordinated edits to locks and manifest. Pip enforces artifact hashes and complete transitive coverage during installation. Offline synthetic-wheel tests prove altered bytes and omitted transitive hashes refuse.

Primary contracts: [uv universal resolution](https://docs.astral.sh/uv/concepts/resolution/) and [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/).
