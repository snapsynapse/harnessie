# ATIF export acceptance, 2026-10-05

First end-to-end check of `harnessie atif`: a standalone verification run through OpenEnv's capture proxy, exported from Harnessie's own event log as an ATIF-v1.7 trajectory, validated with Harbor's validator, and reconciled against what the proxy saw on the wire.

## Setup

- Harness source: the phase 3 working tree that became the `harnessie atif` commit (loop events carry `input_tokens`, `output_tokens`, `tool_call_ids`, `model`, `provider`, `effort`; tool results carry `call_id`).
- Model: `qwen3.8:latest` on local Ollama 0.35.1, reached through `python -m openenv.core.harness.capture.server` (openenv 0.7.0) on 127.0.0.1:8100. The `local` tier's `base_url` pointed at the proxy and `api_key_env` carried the proxy's per-rollout session id. No cloud provider involved.
- Task: `harnessie verify` over a two-function workspace with one sandboxed check and two claims. Result VERIFIED, exit 0.
- Validator: `harbor.utils.trajectory_validator` from Harbor 0.24.0.

## Results

Harbor's validator: `Trajectory is valid`. The same validator also accepted a trajectory exported from an older report whose log predates the new event fields, exercising the legacy path (one token total reported under `metrics.extra.total_tokens` with `split_recorded: false`, tool results paired to calls by order with synthesized ids).

Reconciliation against the proxy's rollout (`GET /sessions/{id}/rollout`):

| Measure | Harnessie ATIF | Proxy capture | Agreement |
|---|---|---|---|
| Model calls | 3 agent steps | 3 turns, 1 root, 0 forks, 0 discarded | yes |
| Tool calls per step | 2, 2, 1 | `n_tools` 4, 4, 4 | not comparable: `n_tools` is the tool set offered per request (the verifier's four tools), not calls made |
| Prompt tokens per step | 1060, 1183, 1315 | `n_prompt` 0 | not measurable: Ollama returns no token ids |
| Completion tokens per step | 60, 131, 696 | `n_sampled` 0 | not measurable: capture level `logprobs`, rollout type `eval` |

Call-count agreement is the check OpenEnv itself applies to eval rollouts (`_reconcile_eval` in `openenv/harbor/atif.py` compares counts only when the endpoint returns no token counts). Per-call completion-token agreement, the full `atif=match` bar for a validated harness, needs the proxy in front of vLLM or SGLang with token ids enabled. That is a GPU-host decision and remains open.

## What the trajectory does and does not contain

- Contains: one agent step per model call with `model_name`, `reasoning_effort`, prompt and completion tokens, tool calls by id and name, observations paired to calls by id, refusal codes on refused results, the loop's stop condition, the harness identity (version, inward manifest digest, tool set digest) under `agent.extra`, and `final_metrics` totals.
- Does not contain, and says so: model messages and system prompts (`message` is empty, `extra.message_recorded: false`), tool arguments (`{}` with `arguments_recorded: false`), full tool output (300-character excerpts, `content_excerpt_chars: 300`). These are absent from the audit stream by design; the exporter reports the gap rather than reconstructing it.

## Files

- `atif-export-acceptance-2026-10-05/trajectory.json`: the exported trajectory as validated.
- `atif-export-acceptance-2026-10-05/reconciliation.json`: the per-step comparison above, with the proxy's stats and capture level.

Dated observation under one model, one endpoint and one capture level. It establishes that the exporter produces a schema-valid trajectory whose call structure matches an independent capture; it does not establish token-level agreement.
