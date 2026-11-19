# Harnessie 1.5.1 local candidate verification

Status: local R1 release preparation for security PR #46. The branch began at `6c053dd8409e109310a124685d11e29e1e8e7885` and incorporated the five workflow updates merged to main through `a400b9d39e82132e9aa2a2757474a743513420ae`. The local verification below includes a fix for the PR review's proxy CONNECT usage-accounting finding. The original combined branch `codex/security-release-audit` remains intact; its adoption and sponsorship changes are on the separate `codex/verify-first-adoption` branch. Neither the test wheel nor the proposed release URL is a published 1.5.1 artifact. Published stable core and downstreams remain 1.5.0.

## Candidate identity

| Surface | SHA-256 or value |
|---|---|
| `pyproject.toml` | `417e6f5dd8177f9ceec69d79b53d655783688b4d5041dff9253a1af20cb40d1c` |
| `harness/__init__.py` | `a86656a086bd8bfb33c6efd83715fa266fdd8fad4ae1c1dfddca1a112dfaf50a` |
| `harness/tools/builtin.py` | `2073cec2a59808579b6567fcd157e058908cbd0e30551976f9216f2d109d312a` |
| `harness/verify.py` | `b5f58fd1a98dfb1fb64061b95eba52195a4db1172dff278ec2c391214c7d069c` |
| `harness/models/_transport.py` | `207aa66de0f7fb1d83c56de893fe3dbd6ba5513d92fb5c8e1713bc796c1aaac3` |
| `tests/test_transport_deadline.py` | `be5c19d57daad16a0a9c1a7079e082855f97e776f430f4f1bf68795331700369` |
| `tests/test_bounded_tool_output.py` | `bff4f694b4fd8674aa86cdeedccb655bb0d0f47aa03903d6b5c48185e01eafb5` |
| `docs/MANIFEST.yaml` | `b4a58acf1fbf9e8cc765004e727b8c2b232d88678a4305f79f7ffd0e5c316045` |
| Root and served assistant guides | 8,054 byte-identical bytes; `3afdb258f2f3feb1a32ba3bef615652a3d8314c5261fb89738806c68688aa8b4` |
| Guide sidecar | `a9bb13a561b80ddf87f39514809dd44a9db2ea16e584091bcbb17c1dfcffc5e5` |
| `requirements/manifest.json` | `21b1321884b969a09ca37ae569b2a84cd2bd0ce6ed2266186899f194358beb39` |

## Local gates

- In a fresh CPython 3.12 environment installed from `requirements/release.txt` with pip hash verification, Harnessie 1.5.1 was installed editable without dependency resolution. After the proxy CONNECT fix, `scripts/release_gate.py --locked-build` passed: 2,319 tests passed, 4 skipped, 28 expected failures; 76/76 deterministic evals; configuration, trust and inward manifests, ecosystem and generated docs; isolated wheel and sdist build; Twine, artifact inspection and fresh-install smoke.
- A loopback proxy returning 502 to CONNECT now proves no provider-request byte was sent and usage is known zero. The focused transport suite passed 88 tests. The earlier PR #46 CI was green at `1cec2af`, but exact-commit CI must run again after this fix.
- macOS native Seatbelt tests passed 50/50 before the version bump; three native verifier mimic/probe cases passed. The version bump did not change those runtime paths. The independent adversarial pass and 378 synthetic output-cut cases are recorded in [pre-candidate verification](security-repair-local-verification-2026-11-18.md).
- `scripts/dependency_locks.py` validated runtime, dev and release locks. A dated `pip-audit --disable-pip --no-deps --require-hashes` query found no known vulnerabilities in all three profiles. `git diff --check` passed.
- `node scripts/check-search.mjs` inspected ten sitemap pages with zero defects and zero infrastructure failures.
- Local GuideCheck 2.0.0 reached Level 3 for the 1.5.1 guide: one expected `anchor.independent.missing` blocker, zero warnings. The old 1.5.0 hosted Level 4 receipt does not cover these bytes.

## Retained local test artifacts

These artifacts are in `/private/tmp/harnessie-security-proxy-dist/` and are local review evidence only. A later release workflow must build its own assets from the exact approved tag.

| Artifact | SHA-256 |
|---|---|
| `harnessie-1.5.1-py3-none-any.whl` | `f2937605cb3d92ea57aaefe0a4a239e87b1bc924a3fd8f2f06454509a96586c7` |
| `harnessie-1.5.1.tar.gz` | `fa9013c80b70d31935ba5da91a243683b8839d526a1f1c0ca45aa7e5e96aefff` |

Both retained artifacts passed Twine and `scripts/check_release_artifacts.py`. The retained wheel passed `scripts/fresh_install_smoke.py` in a fresh consumer environment.

## Publication gates

The candidate needs a commit and push, exact-commit Linux bwrap CI and other required checks, a signed tag identity, independent guide anchor and hosted GuideCheck acceptance for this hash, provider-built asset provenance, a GitHub Release, PyPI verification and separate downstream updates. These are distinct actions with their own authority and receipts. Local macOS testing does not establish Linux firejail or Docker parity.
