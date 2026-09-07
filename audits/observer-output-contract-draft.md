# Offline observer preparation contract

Status: September 4 preparation, accepted for the narrow offline slice by Sam on September 7. Current-source contract and interpretation limits are in [OBSERVER.md](../OBSERVER.md); the implementation is unreleased.

## Command and diagnostics

Proposed command: `harnessie --root PROJECT observe RUN_ID`. RUN_ID is one identifier beneath the project's `runs/` directory, not an arbitrary path. Reject traversal and symlink escapes in the run directory, observer directory, and output files before writes. Do not follow unsafe paths to diagnose their contents.

Exit 0 means observation succeeded; it does not mean the observed workflow passed. Nonzero means observation failed. Integrity/path diagnostics go to stderr using the stable codes below; exact nonzero numbers are not yet contractual. No traceback, raw input payload, or synthetic success narrative substitutes for a diagnostic.

| Code | Meaning |
|---|---|
| `unsafe_path` | Invalid run identifier or path escaping the permitted output boundary |
| `missing_input` | No readable source event log |
| `malformed_json` | A complete line cannot be decoded as an event |
| `partial_record` | An incomplete final record is present |
| `chain_break` | Parsed records fail hash-chain/sequence verification |
| `invalid_event` | A known event lacks fields required for its interpretation |

Check path safety first, then input availability and decoding, then chain integrity, then event semantics. No normal narrative is emitted on any error. A safe derived integrity diagnostic may be written with empty phases and `outcome: integrity_error`. Source bytes remain unchanged. Refusing an unsafe path never writes through that path. Existing stale artifacts must not be presented as the result of a failed observation.

## JSON and citations

Successful output consists of `observer/narrative.json` and `observer/narrative.md`.

| Field | Proposed meaning |
|---|---|
| `schema_version` | Integer 1 |
| `run_id` | Observed identifier |
| `outcome` | `completed`, `in_progress`, an evidenced workflow halt status, or diagnostic-only `integrity_error` |
| `chain` | Object with boolean `ok`; failures identify a diagnostic without copying raw event text |
| `phases` | Ordered objects with `name`, `origin`, `execution`, `validation`, and `observations` |
| `observations` | Ordered findings with `id`, `severity`, `phase` (nullable), `seq` (nonempty integer list), and `detail` |

Phase subfields retain the shapes asserted in `tests/test_observer.py`. Severity vocabulary is `info`, `warning`, `error`. Order phases by their first source event; order findings by first cited seq, phase, then id. Every claim cites existing source sequence numbers; Markdown uses `(seq 3)` or `(seq 3, seq 5)`. Static labels do not require citations. Citation validity does not establish that prose is supported or free of injection.

Only source-derived time is permitted. Unknown kinds do not supply success, failure, or authority. Missing completion evidence remains `in_progress`. The first implementation must document which fields it requires for each interpreted event; tests define at least `phase_done.phase` and `phase_done.status` as required. Unsupported interpretations remain absent rather than inferred.

Output uses structured metadata rather than raw goals, tool payloads, or model prose. The canary test proves omission for its named fields only, not universal secret detection. These artifacts can still contain sensitive metadata and stay local. Replay equivalence covers identical input bytes; it does not claim that separately generated runs have identical timestamps or hashes.
