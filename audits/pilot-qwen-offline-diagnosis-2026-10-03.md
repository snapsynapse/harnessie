# Qwen v8 offline diagnosis

Date: 2026-10-03 (America/Denver)
Reviewed implementation: b0b4841, including timing repair 8c7c39d
Scope: saved evidence, existing local logs, code inspection and synthetic tests only
Status: diagnosis complete within retained-evidence limits; no implementation or inference performed

## Findings

The hour-long approval window did not fail. The Qwen client reached its separate 120-second process timeout while strongly correlated Ollama server evidence shows generation still progressing. This is not evidence that a large source packet exhausted input processing: both v8 Qwen requests contained zero returned evidence, and the correlated second server task finished prompt processing before spending most of its interval generating output.

Qwen's first accepted response contained no neutral tool call. The adapter accepts that shape, then the runner adds its standard tool-use reminder and makes the second request. The reason for the first tool-free reply cannot be recovered because its content was not retained. A larger timeout alone would not establish correct tool use or a completed review.

## Existing server evidence

The read-only source is /Users/snap/.ollama/logs/server.log, examined for October 3 21:40:10 through 21:43:47 America/Denver. Selected line observations are retained here; no full log or prompt content is copied.

| Lines | Observation |
|---|---|
| 6919, 6922, 7284 | Model loading began at 21:40:11; runner loaded at 21:40:24. |
| 7357-7359 | Task 0: 1,184 prompt tokens in 16.400 seconds, 350 generated tokens in 64.585 seconds, 80.985 seconds total model processing. |
| 7366 | Local chat-completions HTTP 200 at 21:41:45, duration 1m33s. |
| 7385 | Next slot task 134: 1,452 prompt tokens. |
| 7397 | Task 134 completed processing 776 uncached prompt tokens in 4.64 seconds. |
| 7453 | Task 134 generation progress: 749 tokens, approximately 7.20 tokens/second. |
| 7455, 7457 | HTTP 500 at 21:43:45 after 1m59s, then server message cancel task, id_task = 134. |

The first server task exactly matches the v8 receipt's prompt/output counts. Endpoint, timestamps and sequential slot activity strongly correlate the next task with v8's timed-out second request, but there is no retained per-request identifier binding. Treat this as correlated diagnostic evidence, not exact request attribution. The progress count of 749 is not final usage and does not repair the run's incomplete accounting. A logged cancellation request is not independent verification that all computation ceased.

There is no affirmative queue-delay evidence in the inspected interval. Loading contributed to the first call's interval, but the correlated second call reused context and was already generating. The missing response prevents distinguishing useful answer generation, reasoning or other output in that task.

## Wire contract and diagnostic gap

Qwen receives two native chat messages: a fixed outer system instruction and a user message containing the serialized neutral conversation plus tool schemas. Original role labels remain inside that JSON string. Native tool definitions are not sent. The outer instruction says not to execute tools; the reviewer prompt asks it to emit neutral requests for Harnessie to execute. Claude also uses the neutral protocol successfully. Possible ambiguity between emitting and executing a tool request is a testable hypothesis, not a demonstrated cause here.

The shared neutral parser accepts text-only end_turn responses and preserves valid read_file requests. Native provider tool calls are explicitly refused rather than silently discarded. Only task_complete satisfies the runner's completion contract. After the first text-only response the runner appends a fixed 148-byte tool-use reminder. A second text-only response would stop as no_action; v8 instead timed out waiting for it.

Qwen's transport has two 120-second controls: the supervisor uses min(configured timeout, 120), and the child HTTP operation independently uses 120. Changing an approval expiry or proposal timeout alone cannot extend both. Responses are non-streaming and fully buffered before the child writes stdout. Timeout can therefore leave no returned body or usage even when server generation was progressing. Parent cleanup kills its child process group; this is distinct from server-side cancellation.

Qwen receipts omit raw response content, response capture identity, provider response ID, HTTP status and detailed timing. The completed first reply's 1,036-byte assistant text is absent. The second request cannot be reconstructed byte-exactly without it.

## Offline verification

- Six focused Qwen request/parser/timeout tests passed in 0.23 seconds.
- The complete Qwen adapter and core loop test modules passed 36 tests in 1.10 seconds.
- A synthetic invocation through the actual Qwen adapter accepted an end_turn with no tool calls. An assertion requiring retained raw response evidence failed with DIAGNOSTIC GAP: completed Qwen response is not retained. This reproduces the retention gap, not the live model's decision or latency.
- A separate socket-blocked synthetic invocation returned a valid neutral read_file request; the actual adapter preserved its name and arguments. There is no demonstrated parser loss of a valid neutral tool request.
- A read-only code explorer reconstructed the first v8 Qwen wire request entirely in memory from sealed inputs and actual runner/encoder logic: 6,568 bytes, inner prompt 5,556 bytes, SHA-256 d7d2f89f843d51db3a1beabf83cd8595b8bbf9ea86a0dbfd42b79b645b503be6, matching retained request-0005 exactly.
- The second request remains 7,987 bytes with known hash 1417e8381bbfca23bbe114c849d2b2c321bfbd9cd5d1a8e350452bdb2b3b67fb, but the missing assistant body prevents replay from retained metrics alone.

No live response replay or model-level regression claim is possible from the retained artifacts. The diagnosing-bugs feedback-loop requirement therefore limits the conclusion: transport behavior and evidence loss are reproduced; the specific model behavior remains unproven. Runtime code, timeouts, model settings, consumed artifacts and services are unchanged.

An independent read-only verifier checked the named log lines, request metrics and code paths, reran all 36 adapter/loop tests, and reproduced both synthetic checks with sockets blocked. The reviewer accepted the factual report and its correlation/accounting limitations, not a claim that the live model problem is fixed.

## Recommended next bounded tranche

Add private bounded response capture and timing/timeout diagnostics, verify them offline, then seek or record explicit authority for one local-only diagnostic call. Reuse the reconstructable first v8 request byte-for-byte; preserve the same model identity, request schema, token/byte ceilings and zero retry. A separately scoped 300-second per-call ceiling would provide margin for this diagnostic without repeating Claude's position. Both client timeout controls would need coordinated treatment rather than changing only the approval clock.

The first capture should answer what Qwen says instead of requesting a tool. Only then change one protocol variable, if justified, in a separately reviewed test. Do not bundle a prompt rewrite, native-tool transport change, thinking setting, model substitution and timeout change into one experiment. No full-panel rerun, new inference or implementation is authorized by this diagnosis itself.
