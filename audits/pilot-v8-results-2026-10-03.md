# Pilot v8 live result

Date: 2026-10-03 (America/Denver)
Execution implementation: 8c7c39d
Approved proposal: 17800171c6c2cdbd3d2a0e0701f62a52b485af4b1704cfc196b6ed6cd025ef3f
Status: consumed, incomplete; no retry or further live authority

## Outcome

Sam requested a repeat with a bigger time window. The [verified timing repair](pilot-extended-window-2026-10-03.md) was committed locally before one live v8 invocation. The explicit one-hour observation/approval policy and 37-minute minimum start runway passed. All non-timing limits remained unchanged, including the 120-second per-call timeout.

Four Claude calls passed the unchanged identity and aggregate output checks. Claude's recommend position was recorded at 2026-10-04 03:40:10.785 UTC. Qwen's first response was accepted by the transport guard, but was an end_turn with no tool calls, not a completed position. Its second request timed out and halted the panel. Neither Qwen request contained returned evidence: request-metrics evidence_bytes and tool_results were zero/empty. Do not describe Qwen as having read the source packet or completed its position.

The first Qwen stage turn took approximately 94.82 seconds including local identity and guard overhead. The second took approximately 120.70 seconds including overhead and produced the explicit receipt failure process_timeout. The runner's overall outcome is stage_failed. There is no authority_failure on the refused receipt, and the earliest observation expiry was still roughly 49 minutes away. This is a distinct per-call transport timeout, not recurrence of v7's approval/preflight expiry.

## Accounting and integrity

- Calls dispatched: four Claude, two Qwen. No retry or objection-stage dispatch occurred.
- Claude reported output per call: 326, 918, 837 and 3,064 tokens, all within 4,096.
- First Qwen response: 1,184 input and 350 output tokens, with unchanged local identity.
- Second Qwen response: usage unknown. The request started, but no complete response/usage was returned before timeout.
- Known subtotal: 162,760 tokens including cache. Input 1,192; output 5,495; cache-creation input 145,165; cache-read input 10,908.
- Run usage is null and accounting_complete is false. The known subtotal is not the full run total. Actual dollar cost remains unknown.
- Outcome reports 25 valid ledger records, six admitted request-metrics records and a valid 37-event runner chain.

The second Qwen error turn in runner events is a blocked loop continuation, not another provider dispatch. No Qwen position, objection exchange, open AIDR export or human arbitration exists. All consumed proposal, approval, observations, captures, receipts and runner output remain under runs/pilot-candidate-v8-2026-10-03/. Raw Claude thinking and signatures remain private.

Independent read-only verification passed for these retained facts, not for panel completion. The verifier checked all three audit chains, the still-valid exact proposal seal, four private Claude capture hashes/lengths/permissions and admission results, all 17 Claude source-read requests, both Qwen before/after identities, accounting and the no-retry boundary. Three focused Qwen timeout/latching tests also passed. No provider or browser was contacted by the verifier.

## Diagnostic limits and next scope

The first Qwen reply's raw envelope/content and stop reason at the transport boundary are not retained; the runner event records end_turn with no tool calls, and the next request metrics record a 1,036-byte assistant message. The local server's disposition after client timeout is also not established by these artifacts. Do not infer a server cancellation, zero remaining computation, source-volume bottleneck or a cause for the initial tool-free reply from this result.

The one-hour policy fixed the prior insufficient-start-window problem for this execution. Completion is now blocked on local Qwen stage behavior and latency under the existing per-call limit. Recommended next work is an offline review of Qwen response retention, tool-protocol handling and timeout evidence, followed by a separately scoped local-only probe if approved. Do not repeatedly spend Claude calls to investigate an unresolved local stage. Any increase to the per-call timeout or another live attempt needs a new explicit scope and approval; this consumed run cannot be resumed.
