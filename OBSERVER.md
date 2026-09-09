# Offline observer

Introduced in Harnessie 1.3.0 source; published packages start at the corrective 1.3.1 release. AIDR-0009 authorizes the deterministic offline slice only. Check the installed version before use; the 1.2.0 package does not contain this command.

The observer reads one existing run journal and writes derived JSON and Markdown. It does not construct models, load plugins, start a runner, append events, alter routing, or grant approval. Exit 0 means observation succeeded, not that the run passed. A halted run can be observed successfully.

## Use

Replace: PROJECT_PATH -> absolute path to the Harnessie project containing runs/
Replace: RUN_ID -> existing single run-directory name
Customize
```bash
harnessie --root "PROJECT_PATH" observe RUN_ID
```

Output is `runs/RUN_ID/observer/narrative.json` and `narrative.md`. Errors go to stderr with exit 2 and a stable diagnostic code. No traceback or source payload is printed. There is no follow mode, commentary option, or automatic runner integration.

Run identifiers begin with an ASCII letter or digit and contain only ASCII letters, digits, dot, underscore and hyphen, up to 128 characters. Paths through symlinks and nonregular or multiply linked input/output files refuse. POSIX directory descriptors and no-follow opens are required; unsupported platforms fail closed.

## Input and integrity

The CLI reads a snapshot of `events.jsonl`, limited to 64 MiB, and verifies its sequence numbers and previous-line hashes using the audit module's snapshot verifier. The journal must contain at least one nonblank record and end with a newline. Complete malformed lines, duplicate JSON object keys, nonfinite JSON numbers and malformed interpreted events refuse. No source repair or event append occurs.

The derived output identifies its source SHA-256. A journal that changes during the read/check window refuses with `source_changed`; retry after the run stops. This is offline observation, not a lock on a running writer. Hash-chain validity establishes consistency of the supplied snapshot, not authenticity: a full rewrite, or an unanchored terminal event change, cannot be excluded by the journal alone.

| Diagnostic | Meaning |
|---|---|
| `unsafe_path` | Invalid identifier, unsafe file type/link, inaccessible boundary, or unsupported no-follow operations |
| `missing_input` | Missing, empty or whitespace-only journal |
| `malformed_json` | Invalid UTF-8/JSON, nonfinite JSON constant or excessive parser nesting |
| `partial_record` | Journal does not end with a complete newline-terminated record |
| `chain_break` | Sequence or previous-line link verification fails |
| `invalid_event` | Interpreted event metadata has missing or invalid fields |
| `input_too_large` | Journal exceeds the read limit |
| `source_changed` | Snapshot changed while being observed |

Path checks precede reading; decoding and chain checks precede interpretation. When safe, input failures replace old narratives with a minimal integrity diagnostic, empty phases, and `outcome: integrity_error`. Unsafe paths and changing inputs can leave prior outputs in place; those files are not a successful result of the failed invocation. Check the command exit status and source digest. Files are replaced individually using staged writes. An interrupted publication can leave different generations of JSON and Markdown; compare their source digests and rerun before consuming them together.

## Interpretation and citations

The JSON envelope has `schema_version: 1`, `run_id`, `source_sha256`, `chain`, `outcome`, ordered `phases` and ordered `observations`. Successful outputs include `outcome_seq`. Phase objects contain `name`, source `seq`, `origin`, `execution`, `validation` and their findings. Every finding cites existing sequence numbers. Pre-parse integrity diagnostics can have no sequence citation because no valid event is available.

Required common fields are a nonempty `kind` and a sequential integer `seq`. Unknown event kinds remain uninterpreted. They do not create completion or authority. Optional fields listed below are checked when consumed; raw goals, content, reasons, model prose, bid rationale and unknown payloads are omitted.

| Interpreted event | Required or consumed fields | Meaning |
|---|---|---|
| `workflow_start` | Optional string `run_id` | Starts or resumes a run attempt; clears earlier completion evidence |
| `workflow_done` | Optional map of string `statuses` | Ends an attempt; explicit halt statuses remain halts, not success |
| `phase_start` | Nonempty string `phase` | Marks a phase active; resets its current route and validation attempts |
| `phase_done` | Nonempty strings `phase`, `status` | Records status and ends that phase's active interval |
| `routing_trace` | Nonempty strings `agent`, `tier` | Records the phase's latest evidenced tier and route history |
| `model_turn` | Optional nonnegative integer `tokens` | Sums only explicitly reported token counts, with supporting sequences |
| `check` | Nonempty string `name`, boolean `passed`; optional positive integer `attempt` | Records deterministic check metadata |
| `gate_verdict` | Boolean `passed`; optional positive integer `attempt` | Records gate outcome without copying model reasons |
| `ownership_claimed` | Nonempty strings `agent`, `path` | Records a claim, not proof the file was written |
| `position_recorded` | Nonempty strings `phase`, `label`, `stance`; optional string `provider`, `summary` | Supports only the explicitly defined predicates below |
| Synthetic `bid_recorded` | Nonempty strings `phase`, `tier` | Retains supplied origin metadata only; no bidding implementation |
| Synthetic `bid_outcome` | Nonempty strings `phase`, `tier`; optional list `premortem_scores` | Notes supplied scoring evidence without endorsing it |

An explicit event phase wins. Otherwise, interpretation attaches only when exactly one phase is active. Untargeted events during overlapping phases remain unattributed and produce an informational finding. Route information from one phase is never used to fill another phase's missing route. Execution totals cover observed events across activations; validation attempts describe the latest activation. Missing counters are not proof of zero cost.

`completed` means a completion event is present with no active or unresolved phase status. `needs_human`, `needs_arbitration`, `needs_approval`, `failed` and `cancelled` remain distinct observed outcomes. Missing completion or unfamiliar status semantics remain `in_progress`. This is not independent verification of a passing run.

## Versioned finding predicates

| ID | Predicate and limit |
|---|---|
| `escalation_without_lower_rung_failure` | Same phase and agent climb within local/cheap/mid/frontier without an intervening failed check or gate verdict. Other tier names and effort-only changes are not ranked. This observes missing lower-rung failure evidence, not a policy violation. |
| `scope_drift` | An ownership claim is outside explicitly supplied exact-file or trailing-slash directory declarations. The pure Python API accepts a workflow snapshot for this comparison; the CLI does not load mutable workflow files. |
| `unparseable_output` | A recorded position summary begins with the runtime's unparseable-stance marker. Abstention alone does not establish parsing failure. |
| `provider_monoculture` | At least two positions explicitly report the same provider. Missing providers are not inferred from model names. |
| `premortem_scored` | A supplied synthetic bid-outcome event contains a nonempty scoring list. No scoring or calibration is performed. |
| `ambiguous_phase` | An interpreted event lacks a phase while multiple phases are active. No per-phase attribution is invented. |

Findings are sorted by first cited sequence, phase and ID. Structured labels can still contain sensitive metadata, so output stays local. Markdown escapes dynamic values; citation presence is not an injection defense or proof of reviewer independence.

## Verification and upcoming work

Pytest covers deterministic replay across processes, source immutability, stale-output diagnostics, path boundaries, no runner/model construction, malformed metadata, incomplete/halted runs, parallel ambiguity and payload omission. The active `evals/observer.yaml` suite exercises eight deterministic scenarios; an unknown expectation fails rather than being ignored.

Bid modes, model commentary, related role/schema changes, live-provider calibration, automatic runner observation and follow mode are not implemented by this offline command. They are separately gated slices in the active capability program. The operating ladder's live Narrate experience is not completed by `harnessie observe` today.
