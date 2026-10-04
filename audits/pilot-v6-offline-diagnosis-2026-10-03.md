# V6 stream diagnosis and Qwen readiness

Date: 2026-10-03 (America/Denver)
Scope: offline diagnosis and read-only Qwen evidence review
Status: reproduction complete; runtime repair and new live calls not performed

## Reproduced barriers

The retained v6 fourth capture reproduces conflicting_model_evidence. A synthetic six-event stream with fictional identifiers and content reproduces the same refusal without private thinking, signatures or report text. The tests are diagnostic characterizations of current behavior, not approval of a broader acceptance contract.

Ranked hypotheses and controlled results:

| Hypothesis | Observed probe result |
|---|---|
| Changed assistant message/request identities trigger the first refusal | Changing either ID alone in an otherwise accepted synthetic control produces conflicting_model_evidence. All model labels remain Fable. |
| The intermediary synthetic user event independently violates the existing contract | Normalizing both IDs in memory reveals tool_result_binding_invalid. Removing only that intermediary after identity normalization allows parser acceptance. Removing the intermediary alone leaves the identity refusal. |
| Thinking or other system metadata is necessary to trigger the failure | The minimal text-only stream still refuses. Thinking is not necessary to reproduce it. |
| The requested output-token setting is independently enforced after response | An injected response through the real Claude adapter reports 6,740 output tokens against a requested 4,096 and is admitted when all other bindings pass. Its receipt preserves 6,740. |

In-memory normalization and removal are diagnostic probes only. The original v6 capture and refused outcome remain unchanged. No report has been admitted retroactively. Same model labels and an isSynthetic marker do not prove that the later formatted report preserves the earlier answer or establish trusted continuation semantics.

## Verification

The initial diagnostic acceptance probe failed with conflicting_model_evidence before hypothesis testing. It was replaced after independent review with an explicit current-refusal assertion so the retained tests do not encode an unapproved desired acceptance contract. Final diagnosis and existing stream tests: 33 passed. Runtime sources remain unchanged. Independent review confirmed synthetic-only fixtures and the one-variable findings.

Literal
```bash
.venv/bin/python -m pytest -q tests/test_pilot_v6_diagnosis.py tests/test_pilot_stream.py
```

## Smallest recommended repair packet

First specify the admitted continuation shape and its provenance. Any broadened parser must retain one session, the exact permitted model, no operational native tools, one unambiguous StructuredOutput, its successful result link, exact terminal payload equality and complete all-model accounting. Include adversarial cases for changed models, unknown or injected intermediary messages, ambiguous formatting groups, mismatched payloads, duplicated results and missing usage. A blanket relaxation of assistant IDs or acceptance based only on isSynthetic is not sufficient.

Separately define the requested 4,096 output-token setting as a post-response refusal threshold if that is the intended invariant. A future implementation should retain usage before refusing over-limit responses and cover exact-limit and one-over cases. This cannot prevent already-generated provider usage. No increase to existing limits is recommended.

Only after a reviewed correction and regression checks should a new sealed panel be proposed. V6 approval is consumed; no retry follows from this diagnosis.

## Qwen is required and was not attempted

The panel order is Claude position, Qwen position, Claude objection, Qwen objection. The first Claude position never passed admission, so the runner stopped before constructing a Qwen inference request. Zero calls means unattempted, not unnecessary and not a failed Qwen inference.

Underlying September 17 receipts independently confirm one successful local Qwen smoke: exact PILOT_SMOKE_OK, unchanged identity, observed local residency, 33 input plus 101 output tokens, 37.373921 seconds, 756 response bytes and no process failure. That is dated basic transport evidence. October 3 metadata checks matched its model digest and verified local blob paths; they did not test current inference or a full-evidence position.

The existing QwenPilot API supports a fresh isolated smoke without a transport change. A small new invocation driver should record an attempt guard before dispatch and retain exact request/hash, before/after identity, normalized and raw usage, result and elapsed time. Do not rerun the consumed September driver, which also invokes Claude.

Proposed smoke: one local qwen3.8:latest request, synthetic PILOT_SMOKE_OK prompt only, no tools, no decision evidence, fixed loopback route, no cloud fallback or retries. Limits: 120 seconds, 4,096 input/evidence bytes, 1,024 requested output tokens and 128,000 output bytes. Accept only the exact sentinel, completed receipt, complete usage and unchanged identity. This is a proposed separately approved live call, not authority to execute it.

A successful smoke would establish current basic transport readiness. Full-evidence review latency and quality within the panel limits would remain untested. Fixing Claude admission allows Qwen into the original panel without changing its order; an isolated Qwen smoke can test its transport independently while that repair is pending.
