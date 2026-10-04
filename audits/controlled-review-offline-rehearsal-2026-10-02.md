# Harnessie offline mock rehearsal evidence

Date: 2026-10-02 UTC
Outcome: PASS

## Migration provenance

This dated receipt was reconciled from the temporary HardGuard25 controlled-review handoff on 2026-10-03. The source receipt SHA-256 is `fb92458448f888b5febc9835a48259bdfcac15f7b8c0661e8bedfed8eb8efb8d`. Its captured JSON was preserved byte-for-byte as [controlled-review-offline-rehearsal-output-2026-10-02.json](controlled-review-offline-rehearsal-output-2026-10-02.json); both source and destination JSON have SHA-256 `0dfd97d8d7923be440211393f9802d2ccc145e0c7c29a57964680c17a4e71a7d`.

## Pinned source and setup

- Repository: [snapsynapse/harnessie](https://github.com/snapsynapse/harnessie)
- Commit: `4be8438268a4b97dc8a0dbb4ddfd2435e3c9343c`
- Commit tree: `16cf22c72cffec9afec78e94fdda5fdeb07ceaea`
- Reviewed repository guidance and the example's README and demo before execution. No `AGENTS.md` or `.agents/` entries exist at this commit.
- Built an isolated, partial source working copy under `/tmp/harnessie-offline-rehearsal/source` using the approved public GitHub connector. All 66 needed package, schema, fixture, demo, metadata, and instruction files matched their commit-tree Git blob SHA-1s both before and after installation.
- Python 3.12.14, Node v24.19.0, setuptools 84.0.0, PyYAML 6.0.3, jsonschema 4.26.0. Existing dependencies were reused; no registry access was needed.
- Installed Harnessie 1.4.1 from that local source with `PIP_NO_INDEX=1 .venv/bin/python -m pip install --no-index --no-build-isolation --no-deps --no-cache-dir .` (exit 0; stderr empty). CLI help check also exited 0; demo imported the installed package from the isolated venv.

## Rehearsal result

Command from the isolated source root: `.venv/bin/python examples/aidr-export/demo.py`
Exit: 0; stdout: 1,198 bytes; stderr: empty.

The full captured stdout is [controlled-review-offline-rehearsal-output-2026-10-02.json](controlled-review-offline-rehearsal-output-2026-10-02.json). It reports:

- `status: passed`; scripted MockModel only; 8 mock calls and 0 live model calls
- Installed export of open synthetic `AIDR-9999`, with empty Arbitration asserted and export SHA-256 `f036b489f2f872c107ffb68bc0aebff5c2a362d123a63266bdf9a08c6cf66dd0`
- Pinned AIDR 0.1.0 reference provenance/revision and linter passed; the demo asserts its `PASS` receipt and verifies the fixture file hashes
- Source record, journal, and run files unchanged across export/lint; unsupported unclosed-fence formatting refused as `invalid_record` without altering source inputs or leaving output/staging artifacts
- Initial and resumed status both `needs_arbitration`; resume used 0 model calls
- Temporary project was removed after success

## Limits

This validates the shipped local mock/export path only. It does not test independent reviewers, the full-evidence pilot workload, model-provider reachability, subscription status, provider usage, billing, cost, live readiness or the full test suite. Zero live model calls is an execution count, not a zero-cost or provider-billing claim. The example deletes its temporary project and does not retain the linter's raw console line or exported AIDR; only its asserted success and output hash are retained. No source files were edited or pushed; all setup was confined to the disposable `/tmp` copy.
