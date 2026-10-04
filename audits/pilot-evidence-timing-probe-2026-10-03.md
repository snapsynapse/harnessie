# Full-evidence local timing probe

Date: 2026-10-03 (America/Denver)
Scope: one explicitly approved local-only feasibility measurement, not a completed review or panel.

## Authority and fixed input

Sam approved the recommendation to make one local timing probe using the full evidence, a 256-token output cap and the existing 300-second timeout. No retries, Claude calls, cloud fallback, model substitution, downloads, service changes or timeout increase are included.

The [prepared full-evidence request](pilot-evidence-handoff-2026-10-03.md) contains all 17 frozen source bodies. The timing request changes only `max_tokens` from 4,096 to 256; instructions, evidence, response schema and sampling remain identical. This deliberately small response allowance may end during reasoning or yield truncated JSON. Either is recorded as a measurement rather than accepted as a review.

| Input | Value |
|---|---|
| Original request SHA-256 | `a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c` |
| Timing request SHA-256 | `1da982f1c89ded4c983680f7a114dd453208baef31b5a4ce01a9ceaf06ea86fe` |
| Encoded request | 212,223 bytes |
| Complete source bodies | 17 / 193,658 bytes |
| Model | `qwen3.8:latest`, existing local loopback route |
| Limits | One call, 300 seconds, 256 requested output tokens, 256,000 input/evidence bytes, 128,000 response bytes |

## Implementation and verification

The separate experimental driver binds this exact request and implementation, records approval before dispatch, consumes the attempt once, checks identity before and after, and captures raw response bytes privately before parsing. It does not use the old neutral-tool response parser or alter the consumed probe. Known usage survives a truncated or invalid direct review. Missing usage remains unknown. Client-side cleanup is not proof that server generation stopped.

The agentic-harness skill informed these separate boundaries: input completeness, transport result, provider accounting, output structure and substantive review acceptance.

- Worker focused regression: 124 passed, including 36 new probe tests.
- Independent pre-dispatch PASS: 87 probe/capture/identity tests and 37 probe/integration tests passed; exact full-evidence parity, derived request hash, operator scope and guard/capture paths verified.
- Parent stable full pilot regression: 404 passed in 22.07 seconds; trust/inward manifest tests: 16 passed.
- An earlier parent run overlapped final worker edits and reported 396 passed, one failure in `test_live_entry_wires_private_capture_and_keeps_it_out_of_export` (incomplete rather than needs_arbitration). The test passed isolated and in the stable full rerun. The overlap is not proof of cause; no unrelated test fix or claim of resolution is made.

No live result is claimed by this preparation section.

## Outcome

Implementation was committed locally as `7acbd83` before dispatch. The separately sealed proposal `214a64b89decdba2cb5106285ea23b573bc88b163cd9512f46a89d0fc9629d35` was executed once under Sam's explicit approval of the stated scope. The operator bound that approval to the finalized seal; no claim is made that Sam manually inspected the hash.

Private root: `runs/qwen-evidence-timing-candidate-2026-10-03/`. Original handoff, v8 and earlier consumed probe artifacts remain unchanged. The root retains proposal, exact request, approval provenance, fresh identity observations, consume-once guard, response-capture receipt, outcome and bounded content-free server observations.

| Observation | Result |
|---|---|
| Start | 2026-10-03 23:21:22 America/Denver |
| Client outcome | `process_timeout` |
| Overall elapsed | 300.180 seconds |
| Transport elapsed / ceiling | 300.006 / 300 seconds |
| Response bytes | Zero; capture incomplete |
| Client-observed HTTP status | Unknown |
| Final input/output usage | Unknown, not zero |
| Model and implementation | Pre/post identity matched; 67 implementation files bound |
| Local cleanup | HTTP child exited after supervisor cleanup |
| Retry / executed tools / Claude calls | Zero / zero / zero |
| Accepted review / arbitration | False / false |

The additional `malformed_response` diagnostic reflects parsing an empty retained capture, not a malformed answer received from Qwen. The primary outcome is the timeout. No response reasoning or answer was available.

Independent post-run integrity verification passed: exact request and all source bodies, 67 implementation hashes, matching pre/post identity, private permissions, one guard/capture and 599.991 seconds of authority runway at reservation. The result stayed within approval validity. This is an integrity PASS for a timed-out measurement, not inference success.

## Correlated input-processing evidence

The read-only log interval beginning at the byte offset in `operator-start.json` shows a newly loaded local context of 262,144 tokens and task 2 with 49,808 prompt tokens. Initial cached tokens were zero. Progress remained in prompt processing: 8,704 tokens at 108.56 seconds; 12,800 at 165.37 seconds; 19,456 at 275.77 seconds, averaging 70.55 tokens/second at that point.

At 23:26:22 the server logged HTTP 500 on the chat/completions route, cancellation of task 2, release at 19,968 processed tokens and an idle slot. Roughly 40% of the prompt had been processed. Timing, route and task sequence strongly correlate this task with the probe, but there is no shared request identifier binding. These counters are not final usage and do not repair missing accounting. Server task-release/idle logs support cancellation beyond client cleanup; they are not an independent hardware-level cessation measurement. The immutable client diagnostic correctly retains its own `server_cancellation_confirmed:false`.

This result supports input-processing latency as the immediate bottleneck, not a context-size rejection or a failure to request evidence tools. Full input ingestion, output generation, direct-review schema compatibility and substantive judgment remain untested. The 256-token output allowance was not reached in the observed task.

## Next proposed boundary

Do not retry this consumed measurement or call it a completed review. A same-evidence review needs more than five minutes for cold input processing on the observed configuration. A simple projection at the last observed average rate gives approximately 12 minutes for input alone, but the rate was decreasing and this is not a completion-time guarantee. Output generation at this context size is unmeasured.

Recommended next scope, not executed or authorized here: one local substantive review with the same complete frozen evidence, the original 4,096-token output ceiling and an explicitly sealed 30-minute per-call ceiling, zero retries and no Claude call. Keep model and service configuration unchanged. The transport and approval runway must both support that exact bound; do not merely extend an approval timestamp. Retain abstention and privately captured usage/response. The 30-minute proposal is an explicit time-budget change with uncertain sufficiency, not an automatic continuation or permission to run additional timing probes.

The existing panel remains incomplete; a later independent position still does not complete objections, export or human arbitration.

Subsequent decision and result: Sam selected a [20-minute substantive review](pilot-evidence-review-20m-2026-10-03.md), rather than the proposed 30 minutes. That separately sealed one-call attempt is now consumed: input processing completed, generation progressed, but the non-streaming response had not returned at the 20-minute cutoff. Its audit owns the result and next preparation boundary.
