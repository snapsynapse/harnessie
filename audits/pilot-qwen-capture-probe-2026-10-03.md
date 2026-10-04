# Qwen capture and isolated probe

Date: 2026-10-03 (America/Denver)
Authority: Sam explicitly approved private response capture and one local-only diagnostic call with a five-minute timeout, unchanged token/byte limits, no Claude and no retry.
Implementation commit: 84e8a21
Status: single probe completed and consumed; panel remains incomplete

## Scoped implementation

The new opt-in CapturedQwenTransport records exact bounded response bytes privately before parsing, including malformed responses, incomplete prefixes and empty failures. Capture files are exclusive, fsynced and mode 0600 beneath mode 0700 directories. Captures preserve private reasoning without printing it. Diagnostics retain elapsed time, first body byte, byte count, HTTP status when available, process exit, timeout source and local cleanup outcome. Client cleanup is not a claim of server cancellation or completed cessation.

Both the diagnostic supervisor and child HTTP operation receive the approved 300-second ceiling. The legacy panel transport remains limited to 120 seconds. Endpoint, request bytes, output schema, model, sampling, token ceilings, tools and retry behavior remain unchanged. No native tools or model-requested tools are executed by this diagnostic.

QwenPilot now refuses capture failures after parsing available complete usage. The isolated driver also applies capture and evidence-persistence failures to the final outcome, preserving any known usage. A malformed/incomplete response remains refused and unknown usage remains unknown.

The driver prepares zero-authority immutable files and requires a separate seal-bound approval action execute_one_local_qwen_probe. It reserves a single durable attempt before dispatch and cannot repeat it. Identity is freshly checked before/after the request. Admission requires at least 330 seconds before the earliest approval, proposal or identity-freshness expiry, both initially and immediately before dispatch. Post-return checks do not demand another call's runway. A dispatch marker distinguishes refusal before the actual transport from an attempted inference.

Independent review caught an initial approval-only runway check; it was corrected before sealing or dispatch. Frozen-clock tests cover the identity-age boundary at 570 seconds versus 571 seconds and a metadata delay crossing that boundary. No consumed v8 evidence was modified.

## Exact candidate

Private preparation: runs/qwen-probe-preparation-2026-10-03/.
Private candidate: runs/qwen-diagnostic-candidate-2026-10-03/.
Proposal canonical SHA-256: 28fc7a9580aaf224d4810400b0834c1ec99a7d237804281eaccf5d54645f3e0f.
Request SHA-256: d7d2f89f843d51db3a1beabf83cd8595b8bbf9ea86a0dbfd42b79b645b503be6.

The request is byte-identical to v8 request-0005: 6,568 bytes, inner prompt 5,556 bytes. It was reconstructed offline from the sealed packet and actual runner/encoder expressions with sockets blocked. The second v8 request is not replayed because its preceding assistant text was lost. This probe changes transport timing and retention, not the model-facing request.

Fresh local metadata at 2026-10-04 04:28:22.681185 UTC matches v8's physical model, server and client. The probe's declared harness identity deliberately binds the exact wire-request hash instead of the packet reviewer-file hash; this does not alter the bytes sent to the model. Model digest remains 22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643. The proposal binds 65 implementation files.

Limits: one call, 300 seconds, 256,000 input/evidence bytes, 128,000 response bytes plus one capture-only overflow sentinel, and 4,096 requested output tokens with post-response enforcement. No actual tool execution, fallback, model/service changes or retry. Completion here means a retained diagnostic response, not a panel position or arbitration.

## Offline verification

The worker capture/adapter suite passed 46 tests; the final combined probe/capture/adapter suite passed 81. Independent review passed 89 focused driver/capture/adapter/storage tests after the runway correction. The final full pilot suite passed 337 tests in 21.21 seconds. Tests cover exact bytes, private capture, malformed/partial/empty/error responses, unknown usage, capture failure with known usage, timeout propagation, strict config/authority/seal checks, identity drift, expiry and consume-once refusal. Trust and inward manifests passed with 21 and 16 files respectively. The verifier checked the exact candidate seal, all 65 implementation hashes, private permissions and zero-authority preparation. No rehearsal proves live tool behavior.

## Actual result

The single approved local request completed in 90.7447 seconds including operator overhead, with HTTP 200. Transport time was 90.5904 seconds and first body bytes arrived at 90.5632 seconds. No timeout, cleanup or retry occurred. Raw response capture is complete: 2,196 bytes, SHA-256 e2fa4c44f49b17a8aec7bd62d546dd768b8c5eea8127d8936a27ba4f4a5534e5. Response bytes, parsed turn, identities, approval, guard and outcome remain private under the candidate's attempt directory. The known usage is 1,184 input plus 350 output tokens, 1,534 total; actual dollar cost remains unknown.

The diagnostic succeeded, but Qwen did not perform the review workflow. It returned a 1,036-byte plain-text report with end_turn and no tool calls. The report explicitly says no evidence files were read, treats the index and all 17 sources as unknown, and concludes abstain because it cannot verify the named gates. It did not request read_file or task_complete. No model-requested tool was executed, no Claude call occurred and no panel position, objection round, export or human arbitration was completed by this probe.

The response does not establish why the model chose that behavior. In particular, a causal claim that the outer no-execution instruction prevents neutral tool requests remains a hypothesis. The captured text demonstrates premature reporting without evidence acquisition, not a valid grounded abstention or a completed task.

Independent read-only post-run verification passed for the single diagnostic: one consumed attempt, exact private capture hash and permissions, response parsing, complete reported usage, unchanged before/after identities and all 65 implementation hashes. Effective runway at reservation was 740.469 seconds, with approximately 649.724 seconds remaining at completion. The verifier confirmed zero retries and zero executed tools, and independently reproduced the historical request reconstruction below. It made no model or service calls.

## Binding the newly retained text to v8

Offline reconstruction combined the new 1,036-byte assistant content with the unchanged initial conversation, the core loop's 148-byte tool-use reminder and the call-two budget notice. It reproduced the historical v8 request-0006 byte-for-byte: 7,987 bytes, SHA-256 1417e8381bbfca23bbe114c849d2b2c321bfbd9cd5d1a8e350452bdb2b3b67fb. This matches the immutable v8 request-metrics record and binds the newly captured text to the content incorporated into v8's second request. Matching response length and token counts alone would not establish that link.

The reconstruction and proof are retained under the separate preparation root as recover_second_request.py, recovered-v8-request-0006.json and content-binding.json. The consumed v8 root was not modified. This recovers the assistant content used in the next request, not v8's original raw response, reasoning, provider identifiers or missing second-call usage. The reconstruction made zero model calls and executed no tools.

## Next boundary

Do not repeat this consumed probe or resume the incomplete panel. Recommended next scope is an offline, one-variable protocol correction that explicitly distinguishes emitting neutral tool requests from executing tools and reinforces the first evidence-read step. Preserve unknown evidence and abstention, but require the expected tool protocol for a completed stage. Verify the correction with fixtures before proposing one separately approved local-only comparison. No prompt change, additional inference, full-panel retry, model substitution or service change is authorized by this result.
