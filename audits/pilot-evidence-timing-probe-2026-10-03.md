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

Pending execution and verification. The existing panel remains incomplete; this probe cannot complete positions, objections, export or human arbitration.
