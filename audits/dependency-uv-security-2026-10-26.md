# uv security lock repair, 2026-10-26

Scope: repair the controlled release dependency and resolver for [Dependabot alert 8](https://github.com/snapsynapse/harnessie/security/dependabot/8), then stage, commit and push under Sam's explicit instruction. No model inference was needed or run. No runtime API, package version or global tool installation changed.

## Change

GitHub classified the open repository alert as critical. The [upstream advisory](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62) identifies uv versions before 0.13.4 as affected by the compromised emSign trust chain; 0.13.4 removes the root from uv's bundled certificate store.

Main was clean and synchronized at `5cc5868f8d28a890a47e2a16932bfbceeb98b2a8` after fetch. Update `requirements/tooling.json` from 0.11.15 to 0.13.4 for both generator and release-tool pin, then regenerate through `scripts/dependency_locks.py --update` without `--upgrade`. Only uv's version and artifact hashes changed in the release lock. Runtime and development locks remain byte-identical, as do every other release dependency's version and hashes. The manifest records the new input fingerprint and release-lock digest.

The bootstrap used pip in a disposable CPython 3.12.15 environment with the official macOS arm64 wheel's SHA-256 enforced. No network operation used the previously installed vulnerable uv. Every one of the 19 regenerated uv hashes was checked against official PyPI 0.13.4 metadata.

## Checks

- Fresh hash-enforced release installation, editable project installation, pip compatibility check and installed-release lock validation passed under CPython 3.12.15.
- All 10 dependency-lock tests passed, including refusal of altered wheel bytes and omitted transitive hashes.
- All 70 deterministic evals, configuration validation, outward/inward manifests and ecosystem validation passed.
- Locked package gate passed: generated docs, whitespace, wheel/sdist build, Twine metadata, archive privacy and fresh-install public CLI smoke.
- Patched uv created a fresh runtime environment, installed the hashed runtime lock and local wheel, and passed its package compatibility check. CycloneDX 7.3.1 generated and validated the release-format SBOM twice with byte-identical output (SHA-256 `99691b51dc1f42d492a347fa3bbf4e851a26007803bda2222c8f47fc9712029f`). No SBOM or test package was published.

Two full local suite attempts each reported 1,318 passed, four skipped and 28 expected failures, plus two synthetic pilot transport failures. The output-overflow test consistently received `process_timeout`; the other failure moved between the successful-usage and malformed-response fixtures. Both tested transports and fixtures are unchanged. The timeout/usage failures reproduced from a separate untouched archive of the starting commit using the same interpreter. A direct synthetic launch measured approximately 0.711 seconds through a script shebang versus 0.032 seconds through explicit Python, against the fixture's one-second allowance. This supports a host startup sensitivity, rather than a dependency regression; it is not a passing full local suite. No production or fixture limits were widened. The full gate stopped at pytest; the remaining deterministic and locked-package gates above were run explicitly and passed. Exact-commit hosted CI runs the full suite independently and must be checked for delivery acceptance.

The repository alert should close through dependency analysis after the patched lock reaches the default branch. Do not dismiss the alert or infer closure from a local lock check; verify GitHub's returned alert state after push.
