# Pilot v6 preparation

Date: 2026-10-03 (America/Denver)
Implementation: 793338b2069a534bc0f28ba416be2d4487467ed9
Status: candidate prepared; exact live execution approval pending

## Candidate and rehearsal

The approved offline reviewer scheduling repair is committed. The fresh candidate retains all 17 evidence files, the existing authentication contract and resource limits, and zero live allowance. Its private records are in runs/pilot-candidate-v6-2026-10-03/. Earlier consumed candidates remain untouched.

Packet SHA-256: ad735ad5036a6317957d6a18828cf36505e1f649f2868cf847df0c46ade71152

Final proposal canonical SHA-256: 8ee97a286d77840525c39ccc9a01c5e4a9a13c0623bf34ad35d57383f0578b11

The separate retained offline rehearsal at runs/pilot-scheduling-rehearsal-2026-10-03/ used the same packet hash. All 16 encoded requests were admitted and all four synthetic stages completed at needs_arbitration. Maximum request size was 220,500 bytes, leaving 35,500 bytes of input headroom; maximum evidence was 196,632 bytes. Ledger integrity passed with 65 records. The exported Arbitration section remained empty. No live provider calls occurred.

Workload report canonical SHA-256: b3c06a6ddaee95e0487c1483f08fb80c598da52e0b09c3269d536f8d0389eaf2

An independent candidate review verified all 26 sealed files, all 17 source matches, implementation binding, unchanged constraints, and absence of approval or runtime output before billing completion. Synthetic rehearsal does not establish live compliance, review quality or provider token requirements.

After billing completion, independent read-only verification confirmed the final proposal hash and every non-approval execution predicate, including identity, executable hash and freshness. At that check the billing observation was 77 seconds old and the Claude identity observation was 46 seconds old. Exact live approval remained absent; no approval object was manufactured for verification.

## Dated preflight observations

At approximately 2026-10-04 00:44:30 UTC (October 3 locally), the shared Comet Usage page was refreshed and showed Last updated just now, Max (5x), current session 3% used, weekly usage 2%, and Fable weekly usage 0%. The Usage credits switch explicitly had aria-checked=false; auto-reload was off. No setting was changed.

At 00:45 UTC, refreshed CLI metadata reported Claude Code 2.1.287 with claude.ai:oauth:firstParty. Local Qwen identity retained digest 22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643 and verified local blob paths. Browser and CLI account equality was not independently compared. Allowance evidence is point-in-time, not a guarantee of future billing or availability.

## Exact proposed live scope

One panel: Claude position, Qwen position, Claude objection, Qwen objection. At most eight calls per participant, four per stage, no automatic retries. Preserve the existing 120-second per-call timeout, 256,000-byte input and evidence ceilings, 128,000-byte output ceiling, 4,096 output tokens per invocation, 800,000 all-model reported-token ceiling and the versioned Haiku context policy. These token ceilings are post-response stop thresholds, not billing caps.

Claude uses the existing first-party subscription route; Qwen remains local loopback only. Retain exact receipts, all-model usage and failures. Halt on a failed stage. If the panel completes, export the open record and stop for Sam's human arbitration. No dispatch-selection change follows from panel completion.

The proposal remains zero-authority. No approval file or live execution was created. Its account and CLI observations have a 15-minute freshness window; stale evidence must be refreshed and bound before dispatch. Push, release and deployment remain separate.
