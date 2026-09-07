# Offline observer implementation evidence

Date: 2026-09-07. Scope: Harnessie core only. Local branch: `codex/approved-followup`, based on remote main `d64d985`, with the preserved `9b30f40` preparation applied as uncommitted changes.

## Authority and scope

Sam Rogers arbitrated [AIDR-0009](../decisions/AIDR-0009-bid-rounds-and-run-observer.md#arbitration) in favor of the most conservative offline-observer slice, following Codex and Antigravity's bidding deferral. The record contains his verbatim decision and all five position sections with six preserved objections/conditions. The four source reports remain byte-identical to their preparation copies. The original Fable position is preserved.

The reference AIDR linter passes. Its mechanical `independent-positions` badge is not evidence of a common blind review: hosted model identities are missing, input access differed, and the record explicitly disclaims that claim. Attribution and human arbitration are recorded without inventing new reviewer statements.

## Implemented behavior

- `harnessie observe RUN_ID` reads an existing event journal snapshot and writes deterministic, cited JSON and Markdown beneath that run's `observer/` directory.
- Snapshot chain verification is shared with the audit module. Malformed input, unsafe paths, invalid interpreted metadata and changing sources refuse; no source log is repaired or appended.
- Halts and incomplete runs retain their status. Unattributed events during parallel phases are not assigned to an arbitrary phase. Routes are not inherited across phases or new activations.
- Output omits raw goals, tool payloads, model prose and bid rationale. Structured metadata can still be sensitive. Synthetic bid fixtures do not implement bidding.
- The pure API can compare claims with an explicitly supplied workflow snapshot. The CLI does not load mutable workflow configuration.
- Each output file is atomically replaced. The pair is not a filesystem transaction; source digests let consumers identify mixed generations. This is offline observation, not a lock against concurrent writers or proof of source authenticity.

The [current output contract](../OBSERVER.md) records diagnostics, interpretation predicates and limitations. No model, runner, plugin or tool dispatch is added to the observation path.

## Verification

Before implementation, removing only the offline expected-failure markers produced 24 failures attributable to the missing observer module. Additional boundary cases were added during implementation. Two later red cases exposed duplicate-key JSON acceptance and source-file replacement during rendering; both now refuse. The draft route fixture was corrected to leave a phase's unevidenced origin unset, and its bid-rationale assertion was changed to omission under the accepted privacy contract.

Final source and package checks passed on September 7:

| Check | Observed result |
|---|---|
| Full pytest suite | 534 passed, 9 skipped, 28 expected failures |
| Deterministic evals | 59/59 passed, including 8 active observer scenarios |
| Authoring configuration validation | 9 documents passed |
| Outward / inward trust manifests | 21 / 16 files passed |
| Ecosystem manifest | 4 components passed |
| Generated documentation check | 9 pages passed |
| Reference AIDR linter | Record passed, subject to the provenance caveat above |
| Local package gate | Wheel and source distribution built; Twine and archive checks passed |
| Fresh-install smoke | Installed CLI observed a halted run successfully; full smoke passed |

The package gate ran after the final observer code changes. It built disposable distributions using the unchanged `1.2.0` project metadata; these are local test builds, not replacements for the published 1.2.0 artifacts. At this verification checkpoint, no version bump, commit, push, release, deployment or provider mutation had occurred. Sam subsequently authorized signed commit, branch push, PR creation and merge after passing checks. Git history and the PR record carry delivery evidence. Git whitespace checks passed.

The tests cover separate-process byte determinism, source immutability, path traversal and link boundaries, stale-output diagnostics, malformed event metadata, duplicate JSON keys, changing source identity, unknown events, halted/incomplete outcomes, parallel ambiguity, payload omission and no model/runner construction. Eval expectation mistakes and unknown keys fail instead of silently passing. The nine skips remain visible; they do not establish live-provider or unavailable-environment acceptance.

## Deferred work

All bidding modes, calibration, model selection, commentary, follow mode, automatic runner observation and new role/schema surfaces remain deferred. Their strict expected failures remain in place. The offline observer does not complete the live Narrate experience. No live model calls were made.

The separately approved [controlled-review assessment](review-interoperability-2026-09-07.md) and [maintenance packets](maintenance-packets-2026-09-07.md) are prepared. They do not implement an exporter, launch a live review panel or change repository provider rules. GuideCheck and a11y-audit remain with the concurrent session.
