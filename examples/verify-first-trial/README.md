# First trial: checks-only verification

A reproducible worked example of `harnessie verify --no-verifier` against a small artifact. It makes no model calls and denies the check network access. It is a deterministic example, not an external adoption receipt or an independent model review.

## Files

- `claims.md`: the reviewed acceptance criteria (two claims).
- `workspace/slug.py`: a defective `slugify` that keeps punctuation.
- `workspace/test_slug.py`: the check. It exercises both claims with the standard library's `unittest`.
- `fix/slug.py`: the corrected `slugify`.

## Run it

Requirements: Python 3.11+, released Harnessie installed (`pip install harnessie`, or `pipx install harnessie`), and a usable sandbox (macOS Seatbelt, or bubblewrap, firejail or docker on Linux). An unusable sandbox is a refusal, never a skipped success.

Copy the workspace somewhere disposable so the repository stays untouched and the report lands outside the inspected workspace:

```bash
T="$(mktemp -d)" && cp -R examples/verify-first-trial/. "$T" && cd "$T"
harnessie verify --workspace "$PWD/workspace" --criteria "$PWD/claims.md" \
  --check "python3 -m unittest -q test_slug" --report-dir "$PWD/reports/1-defect" --no-verifier
echo "exit=$?"    # 1: the check executed and failed
cp fix/slug.py workspace/slug.py
harnessie verify --workspace "$PWD/workspace" --criteria "$PWD/claims.md" \
  --check "python3 -m unittest -q test_slug" --report-dir "$PWD/reports/2-corrected" --no-verifier
echo "exit=$?"    # 0: the unchanged check passed
harnessie verify --workspace "$PWD/workspace" --criteria "$PWD/claims.md" \
  --report-dir "$PWD/reports/3-no-check" --no-verifier
echo "exit=$?"    # 2: checks-only with no check verifies nothing
```

Each run writes `report.md`, `events.jsonl` and `proofs/` (the captured check output) under its `--report-dir`.

## Recorded result

Recorded 2026-11-18 with Harnessie 1.5.0 installed from PyPI into a fresh virtual environment on macOS (Seatbelt). Absolute paths are shortened to `.../`; nothing else is changed. `criteria_sha256` matches `claims.md` in this directory.

Defect run, exit 1:

```
# Verification report: FAILED

- criteria_sha256: b0cd649f830fb73ff86bb8a3cc7584992f9ec305fe46283b7a48e4dc4d13618d
- verifier model: (none — deterministic checks only)
- harness: harnessie 1.5.0
- checks network: denied
- exit code: 1 (0 verified / 1 failed / 2 cannot verify, fail closed)

## Deterministic checks

### [FAIL] check-1

FAIL: test_punctuation_removed (test_slug.SlugTest.test_punctuation_removed)
  File ".../ws/test_slug.py", line 9, in test_punctuation_removed
    self.assertEqual(slugify("Ready, set: go!"), "ready-set-go")
AssertionError: 'ready,-set:-go!' != 'ready-set-go'
Ran 2 tests in 0.000s
FAILED (failures=1)

## Verifier judgment

(not consulted: deterministic checks already failed: check-1)
```

Corrected run with the same criteria and check, exit 0:

```
# Verification report: VERIFIED

- criteria_sha256: b0cd649f830fb73ff86bb8a3cc7584992f9ec305fe46283b7a48e4dc4d13618d
- verifier model: (none — deterministic checks only)
- harness: harnessie 1.5.0
- checks network: denied
- exit code: 0 (0 verified / 1 failed / 2 cannot verify, fail closed)

### [PASS] check-1

Ran 2 tests in 0.000s
OK
```

No check supplied, exit 2:

```
# Verification report: CANNOT VERIFY

## Deterministic checks

(none supplied)

## Verifier judgment

(--no-verifier with no checks supplied: nothing was verified, failing closed)
```

## What the verdict does and does not mean

With `--no-verifier`, Harnessie reads and fingerprints the criteria but does not interpret or verify each written claim. The verdict rests only on the supplied checks. Here the check happens to exercise both claims; in general a green check can coexist with claims nothing tested. Model-backed verification (drop `--no-verifier` and configure a verifier endpoint) is a separate step with its own requirements; see [docs/GUIDE.md](../../docs/GUIDE.md).
