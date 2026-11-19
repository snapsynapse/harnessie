# Security repair local verification, 2026-11-18

Status: local source verification, not a release candidate or published repair. The worktree is based on `920f002b3780bec566aec1492fd783a44df21a1e`, three commits ahead of fetched `origin/main` at `6c053dd8409e109310a124685d11e29e1e8e7885`. The final repairs and this receipt are uncommitted. The package still identifies itself as 1.5.0, so the build below is a test artifact and must not be published as 1.5.0.

## Source and lock identity

| Path | SHA-256 of tested bytes |
|---|---|
| `harness/tools/builtin.py` | `2073cec2a59808579b6567fcd157e058908cbd0e30551976f9216f2d109d312a` |
| `harness/verify.py` | `fde97bd4e73a7a5e8574e053bb1618af9dafbcc6e300d318457e4f54449136bb` |
| `harness/runner.py` | `85e7cef1271172b5e01c805dff1a430d06f52866857d83cad755a5c7d34a8208` |
| `harness/models/_transport.py` | `2c9d85bb0f9089dcc26ab1a982fc73e15963da872de7ca34d9fb194d6b3705b9` |
| `tests/test_bounded_tool_output.py` | `9217eb6c8752cf4264650ac9b373114198e6b717564ce7915f224c21df21828e` |
| `pyproject.toml` | `3de54bf6418b88a3d77d3ff79e5480b717325033a9653464f4bf524a124017a2` |
| `requirements/manifest.json` | `21b1321884b969a09ca37ae569b2a84cd2bd0ce6ed2266186899f194358beb39` |

The lock generator was uv 0.13.4. Dev and release locks now pin setuptools 84.2.1; all other pins and the runtime lock remain unchanged. `scripts/dependency_locks.py` passed offline validation. `pip-audit --disable-pip --no-deps --require-hashes -r requirements/{runtime,dev,release}.txt` returned no known vulnerabilities for each profile on this date. This is advisory database evidence at query time, not a guarantee against undisclosed issues.

## Local gates

- Fresh CPython 3.12 environment installed the release lock with `pip --require-hashes --only-binary=:all:`; `pip check` passed. Harnessie was installed editable with no dependency resolution before the gate.
- `scripts/release_gate.py --locked-build` passed: 2,318 tests passed, 4 skipped, 28 expected failures; 76/76 deterministic evals; nine authoring documents and both manifests; ecosystem, generated docs and whitespace checks; isolated wheel and sdist build; Twine, artifact inspection and fresh-install smoke.
- A later correction to current Homebrew and Verify Action claims changed `docs/agents.json`, `docs/api/v1/index.json`, both LLM text copies and their trust-manifest hashes. The manifest, ecosystem, generated-doc and whitespace checks passed again; `scripts/release_gate.py --skip-core --locked-build` then passed build, artifact inspection and fresh-install smoke against those final documentation bytes. Runtime source and tests were unchanged between gates.
- Native macOS Seatbelt tests passed 50/50 with local socket access. Three native verifier mimic/probe cases also passed: an artifact mimicking `sandbox_apply` stayed FAILED and a genuine wrapper refusal was CANNOT VERIFY.
- Independent read-only review found no reproducible bypass or false positive in the third-round verify exit precedence, resume last-writer binding, or Content-Length changes. A separate pass tried 378 synthetic cap-crossing cases across seven credential shapes and found zero exposed prefixes. These exploratory cases were not retained as a standalone fixture; the local regression suite covers representative `read_file`, `run_shell`, model-input and event-log cases.

## Remaining release boundaries

- The output-cap repair withholds the trailing unfinished non-whitespace token. A single oversized minified JSON value or URL may produce only a truncation marker. `SECURITY.md` and `CHANGELOG.md` disclose this behavior.
- Native Linux bwrap, firejail and Docker coverage for these repairs has not been run locally. CI must establish the required bwrap gate on the exact candidate commit; firejail and Docker need separately provisioned environments.
- Select a new version, update package and release surfaces, rerun the locked gate on the exact candidate bytes, then obtain publication authority for commit, push, tag, GitHub/PyPI release and downstream updates as separate steps. The uncommitted worktree and its test artifact are not a release.
