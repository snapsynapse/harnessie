# Qwen capture and isolated probe

Date: 2026-10-03 (America/Denver)
Authority: Sam explicitly approved private response capture and one local-only diagnostic call with a five-minute timeout, unchanged token/byte limits, no Claude and no retry.

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
