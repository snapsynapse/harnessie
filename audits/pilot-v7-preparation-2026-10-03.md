# Pilot v7 preparation

Date: 2026-10-03 (America/Denver)
Prepared from: bd52a30
Status: subsequently approved and consumed; see [v7 live result](pilot-v7-results-2026-10-03.md). The preparation observations below are historical.

## Candidate and separate rehearsal

The new candidate uses the committed aggregate output cap and reviewer budget guidance. It retains all 17 evidence files and the four-stage order: Claude position, Qwen position, Claude objection, Qwen objection. The private wrapper is runs/pilot-candidate-v7-2026-10-03/, with inputs under packet/ and the final proposal at execution-proposal-ready.json. The initial unapproved execution-proposal.json is retained separately. No consumed candidate was reused.

- Packet SHA-256: db89a6ddf8f97d9c8e7b48726ee4215632591e6b59639480b23274764815dd90.
- Final proposal canonical SHA-256: f7de489f9e570ee0e3fddffbbef060f70b8605f08fa653d8f0f97107fb487d48.
- Initial unapproved proposal SHA-256: f8b2a992032b3dad287c6b28b328f38699d5d5d3f2a5e36b40413a0ade75e3b3; replaced for presentation by the final freshness-only reseal.
- Sealed files: 26, including the 17 source files; total sealed bytes: 202,354.
- Runtime and pilot implementation hashes bound by the proposal: 63.
- At preparation, live allowance was zero for both participants and no approval or candidate runtime output existed. A separate bound approval subsequently authorized the single execution recorded in the result audit; the proposal itself remains unchanged.

The separate full-workload rehearsal is retained at runs/pilot-output-budget-rehearsal-v7-2026-10-03/. It has the identical packet SHA-256, uses both real request encoders with injected responses and blocked sockets, and retains all 16 admitted requests. Each stage makes four synthetic requests and receives all 17 sources before synthesis. Maximum encoded request is 221,346 bytes, leaving 34,654 bytes below the 256,000-byte input ceiling. Maximum evidence size is 196,632 bytes.

The rehearsal reaches needs_arbitration, exports the open synthetic record with an empty Arbitration section, and makes zero calls on unarbitrated resume. Its ledger has 65 valid records; the runner chain has 121 events and no breaks; request-metrics integrity is valid. Workload-report canonical SHA-256 is 298ddfb1ebb7cc0960055260e7f62f5bceb86391ba170bda8972dc62deaa6a40. Synthetic token counters establish no provider token requirements, billing or review quality.

## Current observations and account correspondence

Sam shared the existing Comet billing tab after the initial read-only tab list showed only Welcome. The session inspected that existing tab and refreshed Usage without changing settings, using a reset or creating another browser profile. At 2026-10-03 20:44:56 America/Denver, Usage showed Max (5x), current-session usage 4%, weekly usage 2% and Fable weekly usage 0%, with Last updated just now. The Usage credits switch explicitly reported aria-checked=false; auto-reload was off.

At 20:45:48, isolated Claude metadata checks reported version 2.1.287 and claude.ai:oauth:firstParty. The executable hash is sealed in the proposal. Strict local Qwen metadata and FROM blob checks passed with the unchanged model digest 22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643. Its declared harness identity is bound to the newly sealed reviewer prompt, not copied from the earlier smoke or v6 packet.

The browser's visible signed-in email and Account organization identifier both match the corresponding non-secret oauthAccount fields in the local Claude Code configuration, compared through retained SHA-256 fingerprints. The isolated auth status command reports an eligible route but no account identifier. Thus the configured account correspondence is observed, while authenticated browser/token identity equality is not independently proven. This qualified basis and the hashes of the retained observations are included in the proposal's billing evidence. No credentials or raw account identifiers are included in this public audit or the provider disclosure packet.

After independent review of the first proposal, the session refreshed Usage at 20:55:34 and CLI/Qwen metadata at 20:55:40. The displayed allowance and credits state, CLI version/executable/auth class, Qwen identity and configured account identifiers remained unchanged. Those observations are retained as browser-observation-ready.json and identity-observation-ready.json and bound into execution-proposal-ready.json. The packet, disclosure, implementation hashes, run ID, scope and limits are unchanged.

The final earliest 15-minute freshness limit is the billing observation, ending at 21:10:34 America/Denver. The proposal's 24-hour document expiry does not extend that observation window. Before dispatch, refresh stale observations and bind any resulting new proposal digest to the required approval. Current allowance is an observation, not a guarantee of subsequent availability or billing.

## Independent preparation verification

A separate read-only reviewer verified the packet and initial proposal seals, current 17 source files, all 26 sealed files and 63 implementation hashes, the executable and retained observation hashes, and every non-approval predicate in the execution validator. The reviewer checked each stage's retained tool results against source prefixes and complete byte lengths rather than relying only on the workload report's declared coverage flag. Request, ledger and runner chains, empty source/export Arbitration sections and zero resume calls passed. No approval was manufactured to exercise the validator, and no service or model was contacted by the reviewer.

The reviewer then independently checked the final freshness-only reseal at 20:57:07 America/Denver. Differences were limited to proposal timestamps, Claude checked_at, billing checked_at and the added observation hashes. All retained hashes and non-approval predicates passed; authority still refused without approval, and candidate runtime outputs remained absent. The final freshness deadline was independently confirmed as 21:10:34.996 America/Denver.

## Exact proposed scope

One panel with at most eight adapter calls per participant and four per stage, zero automatic retries, 120-second per-call timeout, 256,000-byte input and evidence ceilings, and 128,000-byte output ceiling. The 4,096-token request setting is also the Claude adapter's aggregate post-response output acceptance threshold. The run ceiling remains 800,000 reported tokens across models.

The versioned claude-max-haiku-context/v2 policy admits only the exact previously approved Haiku identity as unclassified additional-model usage. Per-call Haiku ceilings remain 96,000 input including cache and 256 output tokens; run ceilings remain 256,000 input and 2,048 output tokens. All reported model usage and refusal accounting are retained. These post-response thresholds cannot cap usage already generated inside a provider invocation or establish subscription dollar charges.

Claude remains on the first-party subscription route; Qwen remains local loopback only with strict local residency checks. Failure halts the panel. Completion exports the open record and stops for Sam's human arbitration. The proposal authorizes no dispatch-selection changes, automatic retry, replacement route or additional inference after a failed or consumed attempt.

The successful isolated Qwen smoke remains separate evidence for basic transport only. The v6 panel remains consumed and incomplete. Full-evidence review quality, live output-budget compliance and panel latency remain untested by this rehearsal.
