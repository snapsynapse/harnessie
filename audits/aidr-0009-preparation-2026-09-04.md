# AIDR-0009 preparation and accepted observer packet

Date: 2026-09-04. Review base: `c75cd3b`, branch `feature/bidding-and-observer`.
Status: observer-only scope accepted by Sam on 2026-09-07 in AIDR-0009. This preparation synthesis is not an independent position. Original reports are preserved.

Assembly completed, 2026-09-07: at Sam's request, the linked decision record now contains Fable's unchanged original position, attributed extracts from all four readiness reviews, objections/conditions and a comparison of agreement and approval breadth. Original source reports are unchanged. This is editorial assembly of existing material with exposure and metadata disclosures, not a newly conducted common position/objection round. Agreement on observer-first sequencing does not establish agreement to authorize bid-record mode now. Sam subsequently chose the most conservative observer-only scope and bidding deferral; his attributed decision is in Arbitration.

## Review reconciliation

| Source | Finding | Disposition |
|---|---|---|
| [Codex](aidr-0009-readiness-review-codex-2026-09-04.md) | Observer first; whole-file xfail blocks staged delivery | Confirmed. Tests now carry independently removable strict markers grouped by core, commentary, runner, record, selection, and scorecard. |
| [Claude Code](aidr-0009-readiness-review-claude-code-2026-09-04.md) | Scope approval narrowly; record-mode routing needs isolation | Confirmed concern. Existing draft routing test covers a nominal case, not all failure and budget paths. |
| [Antigravity](aidr-0009-readiness-review-antigravity-2026-09-04.md) | Containment must filter before candidate calls; bid cap needs enforcement | Confirmed. `Budget.child()` only inherits remaining headroom; it does not implement `bid.max_usd`. |
| Antigravity | Criterion scoring requires a gate migration | Already addressed: draft section 1.5 and `test_criterion_entries_are_not_verifiable_in_v1` explicitly defer criterion verdicts. |
| [Qwen 3.8](aidr-0009-readiness-review-qwen3-8-2026-09-04.md) | Missing observer context-exclusion test | Draft test exists. Strengthening it with a unique output sentinel remains warranted; current assertions search generic words. Qwen had only the supplied summary. |
| Qwen | Permutation baseline unspecified | Partly addressed: draft specifies shuffling entries across same-class packets. Sample size, randomization protocol, uncertainty, and acceptance threshold remain open. |
| All reviews | Observer first, conditional recommendation, selection deferred | Agreement on sequence, not blanket approval or evidence of calibrated bidding. Different lanes and unequal input access prevent interpreting this as four equivalent replications. |
| Review wording | Passing guards prove byte-identical behavior | Overstated: guards exclude new event kinds/artifacts and governance membership. They do not compare baseline bytes. Expected failures are proposed contracts, not implemented controls. |

The four terminal sessions demonstrate operator-mediated review. They do not establish automatic coordination, shared locking, runtime identity attestation, or a bid protocol. Reports identify runtime surfaces; exact serving model identities were not uniformly recorded. Historic test counts are environment-specific observations.

## Accepted decision

Accepted scope: deterministic offline observation of an existing run, with `harnessie observe RUN_ID`, under the acceptance contract below. Sam has recorded his decision; AIDR-0009 is arbitrated. Bid-record mode is not authorized.

### Included

- Pure event reduction and deterministic JSON/Markdown rendering in `harness/observer.py`.
- CLI registration and validated run-path resolution in `harness/cli.py`, reusing chain verification in `harness/audit.py` and event formats in `harness/events.py`.
- Derived artifacts under `runs/RUN_ID/observer/`, with event citations and no source-log mutation.
- Existing deterministic observer fixtures, including synthetic bid events as input data. Rendering synthetic future events does not require implementing bidding.

### Deferred

- `--follow`, automatic runner observation, commentary, new role kinds, plugins, and all bid modes or schema additions.
- Provider calls and calibration experiments.
- New heuristic observations without a documented deterministic predicate and positive/negative fixtures.

### Acceptance contract

1. Same immutable input bytes and explicit workflow input produce byte-identical JSON and Markdown across separate processes. No current-time fields or filesystem-order dependence. Event-derived timestamps are allowed.
2. Successful observation leaves the source event log byte-identical and writes only to the derived observer directory. Reject path traversal and symlink escapes, including a symlinked observer output directory.
3. Broken chains, malformed JSON, or partial final records produce a nonzero CLI outcome and a minimal integrity diagnostic without narrative claims. Existing broken-chain fixture permits a derived diagnostic file. Missing input also fails explicitly. Never repair or append to the source log.
4. Intact logs containing unknown event kinds remain readable without inventing semantics. Known events with missing required fields produce an explicit diagnostic; absence is not success. Preserve event order and distinguish unfinished runs from completed ones.
5. Each emitted observation has a defined predicate, stable ordering, severity, and valid event sequence references. Golden and negative fixtures must show no false positives for admitted predicates. This is a claim about the versioned fixture set, not every possible run.
6. CLI observation uses no model, agent tools, routing, approval, or runner dispatch. Existing no-opt-in guards remain green. Future runner integration must use a unique narrative sentinel to test every captured agent/verifier message; it remains deferred.
7. Output stays local and is treated as potentially sensitive run material. Avoid copying raw goals, tool payloads, or model prose when structured event metadata suffices. No public artifacts or automatic memory ingestion.
8. Only implemented and approved tests lose expected-failure markers. Deferred tests keep strict markers. Unexpected passes require review, not automatic removal of a whole group.

### Verification plan

Run the AIDR guard and observer tests through `.venv/bin/python3`. Add CLI exit-code, malformed-input, path-boundary, and unknown-event fixtures before implementation of those behaviors. A separate-process replay test and source-log immutability test are included in this preparation. During implementation, capture the reason each expected failure fails so unrelated exceptions cannot masquerade as the intended red result. Then run the full suite, deterministic evals, configuration validation, and inward/outward manifest checks. Existing sandbox skips remain visible.

## Preparation-stage contract-to-evidence matrix

The matrix below preserves the September 4 preparation state. Offline observer tests were subsequently activated and implemented under Sam's September 7 approval; current results are in the [implementation audit](observer-implementation-2026-09-07.md). Runner integration and commentary remain expected failures. Read the [current output contract](../OBSERVER.md) for implemented behavior.

The [output contract](observer-output-contract-draft.md) specifies proposed JSON, diagnostics, and citations. The [terminal smoke record](terminal-smoke-test-2026-09-04.md) separates observed startup outcomes from untested behavior.

| Criterion | Evidence | Preparation status | Slice |
|---|---|---|---|
| Replay determinism | `test_observer_replay_bytes_stable_across_processes` | Strict expected failure | Offline observer |
| Source immutability | `test_observer_preserves_source_log_bytes`; replay and CLI assertions | Strict expected failure | Offline observer |
| Path confinement | `test_cli_refuses_path_escape_without_outside_writes`, four variants | Strict expected failure | Offline observer |
| CLI success | `test_cli_success_creates_artifacts_without_runner` | Strict expected failure | Offline observer |
| Integrity refusals | `test_cli_refusal_has_diagnostic_and_no_narrative_claims`, five variants | Strict expected failure | Offline observer |
| Unknown events and incomplete runs | `test_unknown_event_does_not_invent_completion`, two variants | Strict expected failure | Offline observer |
| Payload omission | `test_derived_outputs_omit_raw_payload_canaries` | Strict expected failure; bounded canary coverage | Offline observer |
| Stable citation shape and findings | Existing narrative, escalation, and scope-drift tests | Strict expected failures; full proposed citation grammar still needs assertions | Offline observer |
| No runner invocation | CLI success test replaces runner constructor with refusal | Strict expected failure; separate direct model-factory sentinel still needed during implementation | Offline observer |
| No opt-in artifacts; no governance membership | `tests/test_aidr_0009_guards.py` | Passing narrow guards, not byte-equivalence proof | Existing baseline |
| No agent-context injection | `test_run_with_observe_never_puts_narrative_in_any_agent_context` | Strict expected failure; unique sentinel strengthening deferred | Runner integration |
| Commentary filtering | Existing commentary test | Strict expected failure; citation presence is not a security proof | Deferred commentary |

The CLI and boundary tests are in `tests/test_observer_acceptance.py`; replay tests are in `tests/test_observer.py`. At preparation time, pending YAML scenarios were design fixtures, not executed evals, and absent implementation proved no observer behavior. The offline suite now runs at `evals/observer.yaml`; bidding and commentary scenarios remain pending.

## Bidding prerequisites for a later packet

- Run the draft's five-packet, three-brain probe with identical anchored packets, isolated contexts, recorded model/endpoint/prompt identities, raw replies, parsed bids, and usage. The readiness reviews did not perform it.
- Define a round budget cap and whether worker budget is reserved. Budget exhaustion cannot promise unconditional worker execution when the parent is exhausted. Specify fallback, partial completion, error events, and phase outcomes.
- Filter exposure before any candidate prompt is sent, across record/propose as well as select. Do not classify cloud models as local merely because Ollama listens on localhost.
- Distinguish observed dispatched outcomes from unobserved counterfactual outcomes. Define confidence range, missing-data handling, bundle identities, frozen corpus, permutation procedure, sample uncertainty, and thresholds before selection consumes scores.
- Citation presence is not an injection filter: malicious instructions can cite real sequence numbers. Commentary requires a separate threat review and evidence-support checks.

## Remaining human input

No additional input is required for this preparation. Sam authorized the deterministic observer scope above on September 7. If bidding is added, the additional inputs are the three serving model choices and a resource/spend ceiling for the probe; these are not needed for observer-only arbitration.
