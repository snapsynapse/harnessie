# One-call Qwen streaming review outcome, 2026-10-26

Scope: Sam explicitly authorized one Qwen review with fresh metadata and a new proposal, the existing 20-minute and 4,096-token limits, and no retries. This is the consumed outcome of that single call. It is not a completed review, panel result or human arbitration.

## Approval and dispatch

Main was clean and synchronized at `7eca99def415882ac7ec9a633e925a79a1a1e0f1`. The [independently verified wrapper](pilot-streaming-execution-wrapper-2026-10-26.md) and all reviewed source/test hashes remained unchanged. Fresh metadata at 18:54:34.371840 UTC showed local Ollama client/server 0.40.11 and pinned Qwen digest `sha256:22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.

New private root: `runs/qwen-streaming-review-live-2026-10-26/`. Proposal seal: `9a6fc31146b496294f957257c23d6f173ff0582379d4e1a88011a48f25854c13`. The exact 212,263-byte request retained SHA-256 `86d9e69ec9d93568b389fdf0f10ab57ebb4f2efdfd06a2dee2bb09d53ce0425e`; reversing only its streaming fields reproduced the original 212,224-byte request. All 17 frozen source bodies remained intact. The question remained whether Harnessie should proceed with a bounded bid-record contract after its named exposure and budget gates while leaving dispatch selection unchanged.

An explicit approval record bound the new action and seal, expiring at 19:24:34.386205 UTC. Fresh-context reviewer `/root/streaming_verifier` passed pre-dispatch checks of the proposal, exact/reverse request, all 72 bound implementation hashes, reviewed source/test hashes, saved identity, permissions, approval, freshness and runway. The exclusive guard was consumed at 18:56:17.963969 UTC. No earlier candidate or consumed approval was reused.

Limits remained one call, 1,200 seconds, 4,096 output tokens, 256,000 input/evidence bytes and 128,000 retained response bytes plus one overflow sentinel. No tools, retry, model substitution, cloud fallback, service change or timeout extension occurred.

## Result

- Primary outcome: `output_limit_exceeded`, after 1,141.49 seconds, about 19 minutes 1 second. The 1,200-second timeout was not reached; `timeout_source` is null.
- First received body byte: 1,074.78 seconds, about 17 minutes 55 seconds after transport start.
- Private capture: 128,001 bytes, overflow detected, incomplete; SHA-256 `9862773cda8f1e772bd232539b447feaed9430cb15904e5d1c7c1f65b2a0ef74`. The receipt matches retained bytes. The HTTP child was killed and exited; raw data remained private.
- Independent inspection: zero answer-content bytes, 2,584 reasoning-fragment bytes, no complete review or stance, zero final usage receipts. All input/output/cache token usage and actual dollar cost remain unknown, not zero. The 4,096-token ceiling is not established as the stopping cause.
- Refusal diagnostics additionally identify incomplete capture/frame/review and missing model usage. No parsed accepted-review file was created. Semantic acceptance and human arbitration remain false.

The retained prefix has 559 complete JSON frames and no completed-stop frame. Its complete textual fragments total 2,584 bytes; at least 125,417 retained bytes are framing, metadata or the incomplete final fragment. Those byte counts are not token accounting. The inherited non-streaming byte bound is a demonstrated streaming bottleneck here; partial private reasoning is not a substitute for the requested review.

The bounded server-log supplement records cancellation of task 2 and an all-slots-idle observation after the client stop. Correlation uses timing, route and counter continuity, without a shared request ID. This supports cessation of the correlated task, not global server inactivity; the immutable transport diagnostic retains `server_cancellation_confirmed: false`.

## Independent postflight and next boundary

The same fresh-context verifier independently checked the consumed attempt, receipt/hash parity, stream interpretation, unknown usage, unchanged request/implementation, private permissions, pre/post physical identity and unexpired authority at saved completion (19:15:19.445194 UTC). It passed integrity verification. It made no model, metadata, network, service, credential or Git writes. Integrity verification does not turn the incomplete result into a review.

This attempt is consumed and cannot be retried. Any next implementation work should first address the bounded wire-envelope budget offline, separately from the unchanged output-token cap, with retained failure/accounting guarantees and independent review. No larger byte limit or subsequent inference is authorized by this result. The existing pilot still lacks a valid isolated Qwen position; v8's objections, open export and Sam's arbitration remain incomplete. Durable pickup stays in NEXT.md and the private Qwen handoff.
