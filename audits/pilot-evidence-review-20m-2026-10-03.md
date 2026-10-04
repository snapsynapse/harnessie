# Full-evidence local review with a 20-minute limit

Scope: one explicitly approved local substantive review, no retries or Claude calls. Decision date: 2026-10-03, America/Denver.

## Authority and input

Following the [consumed five-minute timing probe](pilot-evidence-timing-probe-2026-10-03.md), Sam approved a substantive review but selected a 20-minute per-call timeout instead of the proposed 30 minutes. The approved output ceiling is the original 4,096 tokens. All 17 frozen source bodies remain unchanged, and abstention remains available. No model substitution, cloud fallback, download, service configuration, package release or push is included.

The exact native request is the original [full-evidence handoff](pilot-evidence-handoff-2026-10-03.md): 212,224 bytes, SHA-256 `a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c`. It contains 193,658 source bytes and no current Claude panel response, model-emitted retrieval commands or fabricated tool results.

## Timing and acceptance contract

The opt-in review transport must enforce 1,200 seconds in both its supervisor and HTTP child. The old capture transport and consumed probes retain their 300-second maximum. Input/evidence and response ceilings remain 256,000 and 128,000 bytes respectively.

This new review seals a fresh-at-start identity policy: the preparation identity observation must be at most 15 minutes old initially and immediately before dispatch; a fresh matching physical identity is observed before and after the call. The original preparation observation does not expire the result halfway through an approved 20-minute request. Approval/proposal must provide at least 1,320 seconds of runway before dispatch and remain valid on return. The operator records a 30-minute approval envelope to cover the 20-minute call plus checks; this is not a 30-minute call allowance.

One exclusive attempt guard consumes authority before dispatch. Raw bounded response bytes are retained privately before parsing. Known usage survives later structural, identity, authority or storage failures. A completed response must finish normally and validate against the direct review schema and citation-path rules. Truncation is incomplete, never a completed review. Structural validity is not evidence that citations support findings; semantic assessment and Sam's arbitration remain separate. Even a valid independent position does not complete the panel's objections or export.

The agentic-harness skill informed the explicit timing, provenance, single-use and acceptance boundaries. No new live result is claimed by this preparation record.

## Verification and outcome

- Transport worker: 54 capture tests and 121 combined transport/legacy regression tests passed.
- Review worker: 197 focused tests passed, including 41 new review tests.
- Independent pre-dispatch PASS: 197 review/probe/handoff/capture tests and a separate 121-test legacy transport regression passed; exact full-source parity and private operator scope verified.
- Parent frozen-tree full pilot plus trust/inward manifest suites: 493 passed in 23.28 seconds.
- No live calls occurred during implementation or pre-dispatch verification.

## Consumed result

Implementation was committed locally as `e2a3a6b` before dispatch. Proposal `9aaaeeac2e1cbf449e8fe52ae9c0e90cb54c13e4420b9e1d521d3b675ffa9890` was executed once under Sam's explicit 20-minute scope approval. The private root is `runs/qwen-evidence-review-20m-candidate-2026-10-03/`; previous consumed attempts and full-evidence preparation remain unchanged. The operator bound the human scope approval to the finalized seal without claiming human inspection of the hash.

| Observation | Result |
|---|---|
| Start / stop | October 3, 23:38:56 / 23:58:56 America/Denver |
| Outcome | `process_timeout` |
| Overall / transport elapsed | 1,200.155 / 1,200.006 seconds |
| Both configured timeout controls | 1,200 seconds |
| Returned response bytes | Zero; capture incomplete |
| Client HTTP status / final usage | Unknown / unknown |
| Physical identity | Matching fresh before/after observations |
| Bound implementation files | 68 |
| Local cleanup | HTTP child exited after supervisor cleanup |
| Retry / Claude calls / tools executed | Zero / zero / zero |
| Review / stance / human arbitration | Not received / unknown / none |

The additional `malformed_response` diagnostic comes from parsing the empty retained capture, not an observed malformed model answer. The primary failure is the per-call timeout. Approval remained valid; the new fresh-at-start policy did not reject the result merely because more than 15 minutes had elapsed.

Independent post-run integrity PASS, reviewed October 4: exact request/all 17 bodies, all 68 implementation hashes, matching physical identity, private permissions and one consumed guard/capture verified. Initial identity age was 20.743 seconds; authority runway was 1,799.991 seconds, with 599.836 seconds remaining after execution. Integrity passed, but the substantive review failed to complete.

## Correlated server evidence

The bounded log slice recorded in `server-observations.md` shows task 0 with a 49,808-token prompt and 262,144-token context. Prompt progress reached 49,804 tokens (rounded to 100%) at 779.27 seconds, followed by generation. The last retained generation progress counter is 3,124 tokens, averaging 7.85 tokens/second at that point.

At 23:58:56 the server logged HTTP 500 on the chat/completions route, cancellation of task 0, slot release with context token count 52,950 and no truncation, then an idle slot. These observations strongly correlate by time, route, prompt size and task sequence; there is no cryptographic/shared request-ID binding. They support cessation of the correlated task, not a global hardware-level cessation claim. The immutable client diagnostic keeps its own unconfirmed server-cancellation field.

This attempt passed the earlier input-processing bottleneck and spent roughly the remaining seven minutes generating. The logs do not distinguish reasoning from answer text. None of those token counters is final provider usage, and subtracting context counters is not a substitute for an accounting receipt. The non-streaming request returned no bytes before timeout, so no stance or review can be recovered or accepted from these observations.

## Next boundary

This approval is consumed. Do not retry, extend the running call, resume the old panel or assert an evidence-backed Qwen position.

Recommended next preparation, not yet implemented or approved: bounded private streaming capture so a later timeout retains emitted deltas instead of losing the entire non-streaming response. Preserve final usage only if actually received, distinguish reasoning from answer fields without publishing private reasoning, and refuse incomplete JSON as a completed review. Streaming is not a claim of faster generation or a substitute for a sufficient time budget. It changes the wire contract and needs offline fixture coverage plus an explicitly scoped live approval before another call. Reassess the next timeout from this observed input/generation split; do not automatically raise it.

The full panel still lacks its completed sequence, objections, open export and Sam's arbitration.
