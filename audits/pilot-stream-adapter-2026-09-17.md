# Pilot stream adapter correction

Scope: Harnessie-local pilot implementation, approved by Sam after reviewing the single stream capture. This tranche permits offline code changes and regression verification. It does not authorize another inference call, Qwen cloud routing, public provider registration, Git delivery or the final decision panel.

## Required behavior

The child environment preserves the non-secret `USER` identity needed by the installed Max authentication check while excluding provider credentials and endpoint overrides. The ephemeral MCP configuration contains an empty `mcpServers` object. Inference requests complete stream events through `stream-json` with verbose output.

Answer attribution is separate from acceptance. A top-level serving message must bind the final `StructuredOutput` input, successful linked tool result and terminal structured payload within the same session. Content blocks sharing a message ID must not duplicate usage. Conflicting identities, broken linkage, unsupported operational native tools, incomplete output and unsuccessful terminal status must refuse.

Receipts preserve all reported models and calculate totals from per-model terminal usage only. Top-level and assistant-message counters are not added again. Unknown counters and actual subscription dollar cost remain unknown. Even a refused response must retain its available usage and attribution evidence.

## Additional-model policy

At this implementation checkpoint the policy remained exact-model only. Fable answer attribution did not establish Haiku's purpose, so a response containing additional usage stayed refused. There was no configurable helper allowlist in this tranche's baseline.

Subsequently Sam delegated the decision after reviewing the risks. The [bounded additional-model policy](pilot-additional-model-policy-2026-09-17.md) permits the exact observed Haiku identity as unclassified usage when explicitly selected. The default adapter remains exact-model only. Neither the policy decision nor this historical correction increases final-panel call authority.

## Evidence and verification

The [smoke record](pilot-smoke-2026-09-17.md) preserves the progression from authentication and MCP failures through successful stream attribution. Exact local evidence is under ignored `runs/pilot-smoke-2026-09-17-005/`. Regression fixtures must be synthetic and portable, without account metadata or dependencies on ignored local receipts.

Implemented in `scripts/pilot_claude_code.py` and the new offline `scripts/pilot_stream.py`, with synthetic regression cases in `tests/test_pilot_transport.py` and `tests/test_pilot_stream.py`. The parser handles only the observed single formatter exchange. Unsupported multi-message exchanges refuse; this is not a general Claude Code session parser.

- Full offline suite with live opt-in disabled: 772 passed, 9 skipped, 28 expected failures.
- Focused stream, transport and public adapter tests: 59 passed.
- Independent verification: 40 current-code and offline attribution tests passed, plus retained-capture replay and adversarial checks.
- Root type-mutation check: 462 mutations of retained event fields, zero uncaught exceptions.
- Public outward/inward manifests, generated documentation parity and diff whitespace checks passed.
- A fresh local wheel and source build excluded pilot modules/tests. No package or release was published.

Offline replay of the actual retained `005` capture returns `additional_model_usage_unapproved`, with bound answer model `claude-fable-5-1`, both reported models and totals of 991 input, 151 output, 585 cache-creation input and 3706 cache-read input tokens. Raw per-model cost/provider/canonical-model metadata remains in `reported_model_usages`; actual dollar cost remains null. Replay replaced process execution with retained bytes and made no provider call. Its receipt is `runs/pilot-stream-adapter-2026-09-17/retained-capture-replay.json`.

Review found and corrected incomplete session/message/request/tool linkage, missing parent and ordering checks, wrong-type exceptions, duplicate-key/non-finite JSON admission and lost accounting on malformed output. Valid terminal usage survives invalid trailing bytes or blank lines. Malformed usage entries remain in raw records; incomplete or multiple-terminal aggregate totals stay unknown.

The historical `005` capture driver and its old-base regression test remain unchanged. That disposable subclass appends stream flags already supplied by the corrected base, so it is not a reusable driver or part of the current-code test gate. Its consumed attempt guard and original receipts remain intact. Current transport tests assert a single verbose flag directly.

This approved code tranche intentionally changes the pilot source after the temporary-smoke restoration checks. It does not claim the old protected-source hashes still apply. No live model calls, Qwen requests, global configuration edits, commits or pushes occurred in this tranche.

## Next boundary

Current next work is recorded in the [additional-model policy and integration plan](pilot-additional-model-policy-2026-09-17.md). Re-freeze the evidence packet before proposing live execution. The old frozen packet is historical and must not be presented as containing the new adapter. Any final panel needs a concrete disclosure set, call graph, limits and separate authority. Qwen stays on its locally verified route; human arbitration remains required after the panel.
