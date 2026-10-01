# Pilot response retention repair

Scope: approved offline repair after the [first live panel attempt](pilot-live-panel-2026-09-19.md). No inference or account-setting changes are part of this repair. The consumed run remains immutable.

## Result

The live Claude transport now reserves a private capture directory before inference and writes its bounded stdout bytes durably before parsing. Every successful or refused response receipt links the absolute capture path, SHA-256, byte count, process outcome and completeness flag. Capture errors refuse progression and retain any usage available from the in-memory response; the ordinary loop cannot redispatch the provider.

`scripts/pilot_capture.py` owns exclusive, consume-once directories and files, with fsync barriers and modes 0700/0600. Existing paths, symlinked ancestors and traversal refuse. Partial files survive write failures. An overflow retains at most the configured byte ceiling plus the one-byte overflow sentinel and is explicitly incomplete. Unknown process failure, absent return code, timeout and absent bytes cannot claim completeness.

`scripts/pilot_stream.py` adds stable non-content diagnostic reasons and line/byte offsets or event positions to refusals. Existing failure codes and acceptance conditions remain intact, including model, tool, session and terminal-output binding. Usage evidence survives malformed responses when the terminal usage map can be read.

`scripts/pilot_claude_code.py` records capture and parser diagnostics in its receipt. `scripts/pilot_live.py` supplies the capture store for every live Claude request. Execution manifest version 2 binds this capture contract and output path, so an older manifest cannot silently dispatch through the new implementation.

## Evidence boundaries

- This captures Claude inference stdout only. Authentication output is excluded; stderr and Qwen response retention are unchanged. Older standalone replay seams can omit a capture store; the guarded live entry point requires it.
- Files contain exact captured bytes, including potentially private provider metadata or response text. They are operator-private local evidence, not sanitized logs, decision exports or publishable fixtures. The record contains hashes and diagnostics, not copies of raw output.
- Capture occurs after the bounded subprocess returns and before parsing. A process crash before this persistence boundary can still leave only an uncertain dispatched attempt. There is no automatic retry or claim of complete crash-time stream capture.
- No original response from the failed first panel can be recovered by this repair. Its exact parser failure remains unknown. No parser rule was relaxed on a guess.
- The earlier smoke's `sanitized_stdout` field was replayed offline. The retained new artifact contains exactly that derivative's bytes, not the original lost panel stream. Fable attribution, the bounded Haiku policy and all usage totals matched the historical replay.

## Verification

The full offline suite passed 868 tests, with 9 skipped and 28 expected failures. Focused root integration passed 69 tests before the final capture-contract mutation case was added. Distribution manifests, generated-document parity, whitespace checks, wheel and source-distribution exclusion checks passed. Both distributions exclude the pilot code/tests, private runs and browser artifacts.

Offline injected tests cover successful and malformed stream capture, auth exclusion, timeout and overflow evidence, disk/fsync/metadata-write failures, collisions, zero additional inference on failure, receipt linkage in the shared ledger, and all four stages through the live entry point. That injected path uses the real exporter, leaves private streams out of the decision export, and resumes at `needs_arbitration` with zero new calls.

Independent review passed 95 focused tests and found no remaining defect. `runs/pilot-response-retention-2026-09-19/verification.json` binds the final source/test hashes, historical replay, package checks and unchanged consumed-run evidence. No live inference, metadata calls, browser actions or account changes occurred during this repair.

## Next execution decision

The proposed next attempt uses a fresh packet root and run identity with the same question, evidence disclosure, four-stage order and ceilings. It adds mandatory private Claude response retention; it does not increase calls, token limits or policy exceptions. The new proposal has zero live allowance and no approval file. Fresh billing and identity evidence and a new execution decision are required before dispatch. Credits must remain off and Qwen must stay local. Any failure consumes its attempt and stops; it does not authorize an automatic rerun.

The candidate is `runs/pilot-dispatch-candidate-2026-09-19-v2/`, 26 files and 200,991 bytes, with the unchanged packet seal `626322d26c8bca5dd1afaf351612336eaa038aef504b106ad80f445dcfece742`. The execution proposal is `runs/pilot-response-retention-2026-09-19/execution-proposal.json`, digest `8b51ebed503028ea43c4211a0fe34d415e78682fe23b1ae038908642426be043`. Its disclosure hashes, policy and limits match the consumed run. Historical provider identities and the prior credits-off observation are labeled as requiring refresh; they are not fresh readiness evidence.

Proposed executable sequence:

1. Under a new approval for this attempt, refresh Claude version/auth/binary, local Qwen identity and the read-only credits-off check. If evidence or the disclosure changes materially, stop and explain the changed scope. Do not enable credits or change models/services.
2. Bind the refreshed manifest to the approval and use only fresh run `pilot-2026-09-19-panel-v2`. Preserve the consumed first attempt.
3. Run Claude position, local Qwen position, Claude objection and local Qwen objection sequentially. Maximum eight calls per participant and four per stage; 400,000 aggregate reported tokens; 120 seconds and 128,000 stdout bytes per process, plus one overflow-detection byte retained privately. Existing per-call/run Haiku bounds remain unchanged. Stop at the first refusal or unknown outcome; never auto-retry or expand limits.
4. If all stages complete, verify receipts/chains, export the open decision and halt for Sam's arbitration. If any stage fails, retain the bounded raw response and precise diagnostic for offline analysis and stop with a truthful partial outcome.

The original failure remains unexplained, so this new attempt may stop at the same point. The repair makes that next response diagnosable; offline success does not establish live compatibility.

## Subsequent panel-v2 result

Sam approved the new attempt. Its capture succeeded and identified a thinking content block rejected by the parser. See [panel-v2 result and offline correction](pilot-panel-v2-and-thinking-block-2026-09-19.md) for the consumed attempt and current next gate.
