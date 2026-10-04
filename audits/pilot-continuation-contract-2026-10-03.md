# Pilot continuation and reported output contract

Date: 2026-10-03 (America/Denver)
Scope: approved offline Claude pilot admission repair
Status: aggregate output refusal implemented; existing continuation refusal retained

## Reviewed admission boundary

The parser still admits one assistant model/message/request identity, one session, one StructuredOutput exchange, its successful result link and an exactly matching terminal payload. The adapter requires the exact requested answer model and complete all-model usage, then applies the existing accounting policy. Operational native tools remain prohibited. No multi-identity continuation is admitted by this repair.

This narrower outcome follows inspection of v6 capture metadata. The intermediary marked isSynthetic reports an output-token limit and asks the model to resume. It is not merely a formatting instruction. The first assistant identity has thinking/text blocks, while the second supplies StructuredOutput. Both assistant stop_reason and stop_details are null. The terminal reports 6,740 output tokens and an iteration with 2,644 output tokens. Their difference is exactly the requested 4,096. Those observations support an inference of CLI continuation after output exhaustion; they do not establish authoritative provider continuation semantics or prove that the second identity preserves the first answer.

The private fourth capture remains at runs/pilot-candidate-v6-2026-10-03/packet/runs/pilot-panel-v6-2026-10-03/operator/responses/attempt-0004/stdout.bin, SHA-256 caf00b381c29967f044d4695dab6dd607bf624cb90a4e294f83b9738a7a0b6f0. Raw thinking, signatures and report text are not reproduced here. Original captures, receipts, proposal and consumed approval are unchanged.

One captured process establishes a transport boundary. It does not make every synthetic user message authoritative. An isSynthetic flag, identical model names, null parents or matching session IDs cannot independently authenticate a continuation's purpose or semantic preservation. The stream does not supply a verified binding between the preliminary answer and the later formatter input. Pinning the observed instruction text would recognize that text, not establish such a binding. There is consequently no basis in this evidence to widen admission. The existing conflicting_model_evidence refusal remains primary for the v6 shape, and the reported aggregate is over the newly enforced threshold independently.

## Output refusal semantics

PilotLimits.max_output_tokens is both the requested CLI setting and the maximum aggregate reported output admitted per completed adapter request. The normal value remains 4,096. All models in terminal modelUsage count, including permitted unclassified Haiku usage. Counts must be complete; missing or malformed counters retain the existing accounting refusals. Exactly the configured maximum is allowed; one token over refuses with output_token_limit_exceeded.

Capture persistence, process errors, stream binding, exact model checks, usage-policy validation and neutral response validation precede the new check. Their established failure codes remain primary. The new refusal therefore applies to an otherwise admissible response, without rewriting a structural refusal as a budget refusal. Raw modelUsage metadata, normalized model counters, aggregate counters, capture linkage and the observed policy disposition survive the refusal. The adapter latches after refusal and does not start another auth check or inference when called again.

This is post-response admission enforcement. It cannot prevent, cancel or refund usage already generated inside the CLI. In particular, one adapter invocation can contain multiple CLI-internal messages; the adapter latch prevents another invocation and does not prove the CLI made only one internal request. Dollar charge remains unknown. The stdout byte limit and existing request/run ceilings are unchanged.

## Verification

The new synthetic admission tests were run before implementation: four expected failures and thirteen passes. Failing cases were 4,097 against 4,096, the diagnostic 6,740 against 4,096, a custom limit plus one, and allowed additional-model output taking the aggregate above 4,096.

After implementation, the continuation, existing stream and v6 diagnosis tests passed: 50 tests. Coverage includes exact-limit and zero-output success, configured-limit enforcement, capture bytes and raw/normalized usage retained on refusal, a latched second call, aggregate additional-model accounting, and unchanged refusals for changed models, unknown or synthetic intermediary messages, ambiguous formatter groups, duplicate terminal results, mismatched payloads, missing usage and operational native tools. All new adapter tests inject auth and response bytes; they launch no provider or authentication subprocess.

The former v6 diagnostic over-limit acceptance assertion now expects the repaired refusal and explicitly distinguishes current behavior from the historical run. The original identity diagnosis remains unchanged. scripts/pilot_stream.py is unchanged.

Literal
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pilot_continuation.py tests/test_pilot_stream.py tests/test_pilot_v6_diagnosis.py
```

## Output-budget guidance follow-up

At the initial admission review, the reviewer role in scripts/pilot_prepare.py described the four-call reading/reporting schedule but did not state the output budget. The pilot_stage_budget notice in scripts/pilot_live.py exposed call counts, not the output ceiling. scripts/pilot_claude_code.py supplied the ceiling to the CLI environment, while its neutral request instruction asked only for the structured response. Environment configuration alone did not tell the reviewer how much output it could spend.

The [output-budget guidance](pilot-output-budget-guidance-2026-10-03.md) follow-up now communicates each delegate's actual configured aggregate ceiling and asks for concise reports preserving evidence-path citations, explicit unknowns and the required position/objection fields. Its synthetic regressions preserve all 17 evidence sources, four-stage order and existing limits. Guidance leaves room for reported reasoning and formatting overhead within the same ceiling. Byte/character counts or mock token numbers cannot prove live token fit or report quality.

The admission patch itself does not change prompts; the linked follow-up owns those changes. A fresh full-panel candidate still needs fresh identity/account evidence and separate approval of its exact proposal before live execution. V6 remains consumed and incomplete. These repairs do not establish successful full-evidence review, Qwen readiness, provider-enforced token limits or a reusable continuation contract.
