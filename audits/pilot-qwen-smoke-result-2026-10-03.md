# Isolated Qwen smoke result

Date: 2026-10-03 (America/Denver)
Implementation: da050e1
Approved proposal: b6e3684e1a7179c10ff1c404df751caf0b1da6719b1e6d02a5d2fe0ff4089306
Status: completed; one inference attempt; approval consumed

## Authorization and delivery

Sam approved the exact proposal with "Commit locally then proceed" after presentation of its request, model, limits, zero-retry rule and identity-freshness deadline. The session first created local commits 4dd08f6 (coordinated CodeQL update) and da050e1 (pilot output controls, reviewer guidance and guarded Qwen smoke preparation). No push occurred.

The recorded approval and guard bind the canonical proposal digest above. Approval was recorded at 2026-10-03 20:33:06.632 America/Denver; the guard was reserved at 20:33:06.646. The identity observation at 20:19:08.728 was approximately 13 minutes 58 seconds old at reservation, within the 15-minute admission window ending at 20:34:08.728. The driver validated the exact proposal, request and all 63 implementation hashes before consuming the attempt.

## Observed result

- Exactly one local qwen3.8:latest inference request was dispatched through the fixed loopback endpoint. No Claude call, fallback or retry was made.
- The returned neutral response contains exactly PILOT_SMOKE_OK, an empty tool-call list and end_turn. Both adapter receipt and smoke outcome are completed.
- Elapsed time, including before/after identity checks: 26.062396665998676 seconds.
- Reported usage: 89 input tokens, 84 output tokens, 173 total. Raw usage reports zero cached input tokens; the normalized receipt uses the existing cache-in-prompt accounting convention.
- Exact request: 1,074 bytes, SHA-256 44b59509ed87531a9ad7dcf769f606f9b8b27455906991d0fb5ca210ce6b60c7.
- Retained response: 687 bytes, SHA-256 9d031873ba7ff58c1810caa064dc50627b07e22e1139d8c9990d81a079e7c4a1.
- Before and after identity fingerprints match: 091cd436464e62034a967addeb5fb29a8f98a7351c056ca2d8b45843a14b4cb0. They match the approved proposal, including model digest 22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643 and client/server version 0.35.1. Strict local metadata and blob checks passed on both sides of the inference.
- Observed output is within the 1,024-token and 128,000-byte ceilings. The inference timeout remained 120 seconds and no tools or decision evidence were offered.
- Dollar cost remains unknown. Local execution and reported usage do not provide a billing receipt.

## Retained evidence and acceptance

Private evidence is under runs/qwen-smoke-candidate-2026-10-03-output-cap/: proposal.json, request.json, approval.json and attempt/ containing guard.json, identity-before.json, identity-after.json, response.bin and outcome.json. The attempt is consumed; do not delete its guard, reset its allowance or invoke it again.

The driver persisted request/proposal evidence before execution, the consumed guard before metadata or inference, response bytes before parsing, and the final receipt after identity comparison. The session read back the saved files and independently decoded the exact sentinel. A separate read-only verifier checked the proposal/approval/guard bindings, implementation and request hashes, dispatch-time freshness, response and identity evidence, accounting and one-attempt inventory.

This establishes current basic local Qwen transport readiness for the one synthetic request. It does not establish full-evidence review quality or latency, Claude continuation admission, a completed panel, an exported live decision or human arbitration. The v6 panel remains consumed and incomplete.

## Next work

Prepare a new zero-authority full-panel candidate with the revised reviewer guidance and all 17 sources. Refresh Claude CLI/account/allowance/credits-off and Qwen evidence, resolve browser/CLI account correspondence, and obtain separate approval of the exact new panel proposal. Retain the existing limits and four-stage order. The smoke approval authorizes no panel or additional inference.

The local CodeQL and pilot commits remain unpushed. Hosted CodeQL and Scorecard results for the coordinated update remain pending delivery; no package release or downstream publication occurred.
