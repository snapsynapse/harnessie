# Harnessie 1.5.1 local candidate verification

Status: local R1 release preparation. The security-only candidate is uncommitted on `codex/security-release-1.5.1`, based on fetched `origin/main` at `6c053dd8409e109310a124685d11e29e1e8e7885`. The original combined branch `codex/security-release-audit` remains intact; its adoption, sponsorship and Verify Action pin changes are on the separate `codex/verify-first-adoption` branch. Neither the test wheel nor the proposed release URL is a published 1.5.1 artifact. Published stable core and downstreams remain 1.5.0.

## Candidate identity

| Surface | SHA-256 or value |
|---|---|
| `pyproject.toml` | `417e6f5dd8177f9ceec69d79b53d655783688b4d5041dff9253a1af20cb40d1c` |
| `harness/__init__.py` | `a86656a086bd8bfb33c6efd83715fa266fdd8fad4ae1c1dfddca1a112dfaf50a` |
| `harness/tools/builtin.py` | `2073cec2a59808579b6567fcd157e058908cbd0e30551976f9216f2d109d312a` |
| `harness/verify.py` | `b5f58fd1a98dfb1fb64061b95eba52195a4db1172dff278ec2c391214c7d069c` |
| `tests/test_bounded_tool_output.py` | `bff4f694b4fd8674aa86cdeedccb655bb0d0f47aa03903d6b5c48185e01eafb5` |
| `docs/MANIFEST.yaml` | `b4a58acf1fbf9e8cc765004e727b8c2b232d88678a4305f79f7ffd0e5c316045` |
| Root and served assistant guides | 8,054 byte-identical bytes; `3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4` |
| Guide sidecar | `a9bb13a561b80ddf87f39514809dd44a9db2ea16e584091bcbb17c1dfcffc5e5` |
| `requirements/manifest.json` | `21b1321884b969a09ca37ae569b2a84cd2bd0ce6ed2266186899f194358beb39` |

## Local gates

- In a fresh CPython 3.12 environment installed from `requirements/release.txt` with pip hash verification, Harnessie 1.5.1 was installed editable without dependency resolution. `scripts/release_gate.py --locked-build` passed: 2,318 tests passed, 4 skipped, 28 expected failures; 76/76 deterministic evals; configuration, trust and inward manifests, ecosystem and generated docs; isolated wheel and sdist build; Twine, artifact inspection and fresh-install smoke.
- macOS native Seatbelt tests passed 50/50 before the version bump; three native verifier mimic/probe cases passed. The version bump did not change those runtime paths. The independent adversarial pass and 378 synthetic output-cut cases are recorded in [pre-candidate verification](security-repair-local-verification-2026-11-18.md).
- `scripts/dependency_locks.py` validated runtime, dev and release locks. A dated `pip-audit --disable-pip --no-deps --require-hashes` query found no known vulnerabilities in all three profiles. `git diff --check` passed.
- `node scripts/check-search.mjs` inspected ten sitemap pages with zero defects and zero infrastructure failures.
- Local GuideCheck 2.0.0 reached Level 3 for the 1.5.1 guide: one expected `anchor.independent.missing` blocker, zero warnings. The old 1.5.0 hosted Level 4 receipt does not cover these bytes.

## Retained local test artifacts

These artifacts are in `/private/tmp/harnessie-security-split-dist/` and are local review evidence only. A later release workflow must build its own assets from the exact approved tag.

| Artifact | SHA-256 |
|---|---|
| `harnessie-1.5.1-py3-none-any.whl` | `59f7f2ab842675e42f55daa65f67b62f99f4fe99e78cc9d7777a32b9b19fbdb2` |
| `harnessie-1.5.1.tar.gz` | `11f0059b2e7337f9a18d6a7121030033650d0142800f6cc8e48a900ce12845a5` |

Both retained artifacts passed Twine and `scripts/check_release_artifacts.py`. The retained wheel passed `scripts/fresh_install_smoke.py` in a fresh consumer environment.

## Publication gates

The candidate needs a commit and push, exact-commit Linux bwrap CI and other required checks, a signed tag identity, independent guide anchor and hosted GuideCheck acceptance for this hash, provider-built asset provenance, a GitHub Release, PyPI verification and separate downstream updates. These are distinct actions with their own authority and receipts. Local macOS testing does not establish Linux firejail or Docker parity.
