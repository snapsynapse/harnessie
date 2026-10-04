# Pilot extended timing window

Date: 2026-10-03 (America/Denver)
Scope: experimental pilot only; no released provider or dispatch-selection changes
Authority: Sam requested, "okay, let's repeat with a bigger time window"

## Bounded change

The new candidate explicitly seals harnessie-pilot-timing/1: billing and Claude identity observations remain acceptable for at most 3,600 seconds during execution, and an approval lasts at most 3,600 seconds. Observations must still be no more than 900 seconds old at initial admission. Proposals without the opt-in policy retain their original 15-minute observation rule. Consumed v7 and earlier artifacts remain unchanged.

Before metadata checks and immediately before the first dispatch, the runner requires enough time before the earliest approval, proposal or observation expiry for all permitted calls at their configured timeouts plus a 300-second margin. With 16 calls at 120 seconds, required start runway is 2,220 seconds, or 37 minutes. This is a conservative admission check, not a promise of completion; metadata, tool execution and other overhead can still vary. All pre/post-response authority checks remain active, and an expired run still stops without retry.

The exact post-response authority exception is now retained as receipt.authority_failure inside the hash-chained operator ledger. The original transport status, usage and failure remain distinct. This closes the specific diagnostic gap observed in v7 without reclassifying its historical receipts.

All other constraints remain unchanged: four stages, eight calls per participant, four per stage, no automatic retry, 120 seconds per call, 256,000 input/evidence bytes, 128,000 output bytes, 4,096 aggregate Claude output tokens per response, 800,000 all-model run tokens and existing exact-model/Haiku rules. Claude uses the existing subscription route; Qwen stays local with no model/service/fallback changes. These accounting thresholds are not provider billing guarantees.

## Verification

The worker added 26 offline tests covering strict policy fields, legacy behavior, fresh-at-start admission, runtime expiry, insufficient runway, rechecking immediately before dispatch and usage-preserving expiry refusal with no retry. The focused live/timing suite passed 46 tests; the final full pilot suite passed 280. An earlier run hit the existing 300ms orphan-process PID-marker timing failure; it passed in isolation and the full subsequent run passed. Its intermittent cause is not established by this result.

The separate full-workload rehearsal at runs/pilot-extended-window-rehearsal-v8-2026-10-03/ used the explicit extended policy with real encoders, injected synthetic responses and blocked sockets. All 16 requests were admitted, reaching needs_arbitration with an open export and zero resume calls. Maximum request size remained 221,346 bytes; maximum evidence size remained 196,632 bytes. Synthetic completion is not a live quality or latency claim. Trust and inward manifests passed with 21 and 16 files respectively.

A separate read-only verifier passed the 46 live/timing tests and 65 surrounding regressions. It checked the exact candidate seal, all 26 files including 17 source bodies, all 63 implementation hashes, observation hashes, identity bindings and unchanged non-timing limits. No missing-approval execution was admitted and no provider or browser was contacted by the verifier.

## New candidate

Private wrapper: runs/pilot-candidate-v8-2026-10-03/. Proposal: execution-proposal.json. Packet SHA-256: 4b47b12d9cd11a01ac36b225c39a59bca61358caa9b0f4eccd845c903270d3f4. Proposal canonical SHA-256: 17800171c6c2cdbd3d2a0e0701f62a52b485af4b1704cfc196b6ed6cd025ef3f.

The packet retains the same 17 evidence source files and reviewer instructions as v7, with 26 sealed files totaling 202,354 bytes. Only the new run identity, implementation binding, observations and explicit timing policy change. Browser Usage was refreshed at 2026-10-04 03:33:11 UTC and showed Max (5x), session 4%, weekly 2%, Fable weekly 0%, credits off and auto-reload off. CLI/Qwen metadata was refreshed at 03:33:38 UTC. Browser email and organization fingerprints match the current CLI configured account metadata, but auth status still exposes no authenticated account identifier. This limitation remains disclosed rather than treated as independent token-account proof.

This authority covers one new attempt, not a retry loop. A completed panel exports an open decision record and stops for Sam's arbitration. Record its actual result separately before making a completion claim.
