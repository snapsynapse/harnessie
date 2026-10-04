# Pilot output-budget guidance

Date: 2026-10-03 (America/Denver)
Scope: offline repair of the reviewer's missing output-budget context
Status: implemented and locally tested with injected responses

## Change

The fresh pilot_stage_budget notice now includes max_output_tokens_per_call from the actual delegate CallAllowance, alongside the existing call limit and current call number. Its output_budget_scope is aggregate_reported_output_all_models. A scripted participant without a transport allowance receives null rather than an invented ceiling.

The notice and generated reviewer role explain that the ceiling covers the entire response, including any reported reasoning, formatter and helper-model output. They ask for a concise report that preserves required stance or objection fields, evidence-path citations and uncertainty, leaving room for overhead. They discourage repeating source evidence and retain the requirement to read every evidence source before the final synthesis call.

The four-stage order, all 17 sources, call schedule, ceilings, model policy and refusal behavior are unchanged. No numeric report sub-budget, token estimate, truncation or evidence reduction was introduced. Existing consumed packets are unchanged; new packet generation seals the revised role through the existing integrity mechanism.

## Verification

Two budget-context tests failed before the change and passed afterward. One inspects the encoded requests received by both real adapters under injected transports: Claude uses a synthetic lower ceiling of 32, Qwen 48, while the proposal default remains 4,096. Each request contains its own actual configured ceiling, and all four stages complete through the existing human-arbitration halt. These deliberately small test limits and provider counters are synthetic; they do not measure real model output.

The full-evidence workload regression sees the budget and guidance in all 16 requests, verifies that every one of the 17 source files has been returned before each final synthesis call, preserves the four-stage order and reaches the existing open-record export and human-arbitration halt. The workload report continues to say that token fit is not inferred from byte counts.

The workload, injected integration, live-seam offline tests and packet preparation tests passed: 37 tests in 6.40 seconds. No provider, account or auth subprocess was called.

Literal
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pilot_workload.py tests/test_pilot_integration.py tests/test_pilot_live.py tests/test_pilot_prepare.py
```

## Limits

Guidance makes the configured constraint visible to the reviewer. It does not prove that a model will comply, that a complete substantive report fits, or that internal reasoning and formatting overhead are predictable. The Claude adapter's aggregate post-response refusal remains the enforcing control. Live usefulness and token fit require a separately approved new attempt; v6 remains consumed and incomplete.
