# Synthetic transport smoke

Date: 2026-09-17, local session date
Authority: Sam approved the synthetic smoke described in [preparation](pilot-preparation-2026-09-17.md), explicitly requiring local Qwen rather than a cloud version. Approval covered at most one Qwen request and one Claude inference invocation, no automatic retries, the stated process/input/output limits, and synthetic inputs only. It did not authorize the final decision panel.

## Current checkpoint after separately approved follow-ups

Local Qwen passed on the fixed loopback route. A subsequent Claude stream capture attributes the exact synthetic answer to `claude-fable-5-1`, but also reports `claude-haiku-4-5-20251001` usage whose role remains unverified. This is answer-attribution evidence, not exact-single-model acceptance or final-panel authorization. Sam subsequently approved an offline pilot-adapter correction; [the correction record](pilot-stream-adapter-2026-09-17.md) owns current implementation and policy status.

Each follow-up used separate one-shot authority. Temporary test changes were restored or existed only in disposable subclasses; no Qwen inference was repeated.

| Local receipt directory suffix | Claude inference commands | Outcome |
|---|---:|---|
| `001` | 0 | Original auth precheck failure; local Qwen passed. |
| `002` | 1 | Temporary `USER` correction passed auth; inference command exited 1. Source restored byte-for-byte. |
| `003` | 1 | Sanitized stderr identified invalid empty MCP configuration. |
| `004` | 1 | Temporary valid MCP configuration returned the correct result; aggregate usage included Fable and Haiku, leaving answer attribution unknown. |
| `005` | 1 | Stream output tied the correct result to a top-level Fable message through `StructuredOutput`; Haiku remained in aggregate usage with an unverified role. |

Directories are `runs/pilot-smoke-2026-09-17-<suffix>/`. The `005` capture completed in approximately 3.38 seconds with 6965 stdout bytes, no stderr and one CLI inference command. Fable reported 2 input, 135 output, 585 cache-creation input and 3706 cache-read input tokens. Haiku reported 989 input and 16 output tokens, with zero cache tokens. Full per-model receipts remain preserved. The USD 0.0204655 list-price estimate is not evidence of an actual subscription charge.

Two emitted assistant blocks shared the Fable message/request IDs. The `StructuredOutput` input matched the linked successful tool result and final structured payload within one session. This formatting mechanism must be distinguished from operational native tools. The terminal result reported zero spawned subagents, which does not establish the Haiku request's purpose. The original single-document adapter refused stream JSON as malformed; that refusal was distinct from successful evidence capture.

## Original smoke outcome

The local Qwen smoke passed. Claude stopped at authentication before inference. Overall transport readiness is incomplete. The attempt was preserved and no inference was retried.

| Participant | Actual inference attempts | Result |
|---|---|---|
| Local Ollama `qwen3.8:latest` | 1 | Passed with the exact expected structured `PILOT_SMOKE_OK` result, complete usage, unchanged model identity and matching local memory residency. |
| Claude Code Max, requested `claude-fable-5-1` | 0 | Authentication precheck returned exit 1 in the sanitized child environment. No model request was launched. |

## Local Qwen evidence

- The request destination was fixed to `127.0.0.1:11434` and `/v1/chat/completions`. Proxy handling and redirects were disabled. There was no alternate endpoint, cloud fallback, model pull or service configuration change.
- The exact tag matched installed model digest `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`. Both declared local FROM blob files existed; model metadata contained no populated remote/cloud fields.
- Identity snapshots immediately before and after the request matched. The smoke fingerprint binds the synthetic prompt, not the different future decision-panel prompt.
- The local Ollama residency endpoint reported the same model digest with `size` and `size_vram` both 19,647,346,768 bytes. This corroborates local weight loading; the local endpoint alone was not treated as sufficient evidence.
- Request body: 751 bytes, including the response schema. Response: 756 bytes. Elapsed bounded child execution: approximately 37.37 seconds.
- Reported usage: 33 input tokens, 101 output tokens, 134 total tokens. Dollar cost was not measured and remains null.
- Response model: `qwen3.8:latest`; finish reason: `stop`; structured content: `PILOT_SMOKE_OK`; no requested tools.

## Claude precheck diagnosis

Claude ran its auth check from a new empty private temporary directory outside the repository. The inference transport was not reached, and no repository or decision evidence was sent.

Read-only comparisons isolated the environment dependency:

| Authentication-status environment | Observed result |
|---|---|
| Ordinary environment | Existing first-party Claude.ai Max login, exit 0. |
| Current pilot allowlist | Not logged in, exit 1. |
| Pilot allowlist plus `USER` only | Existing first-party Claude.ai Max login, exit 0. |
| Pilot allowlist plus `LOGNAME` only | Not logged in, exit 1. |
| Pilot allowlist plus macOS session-context variables or `SSH_AUTH_SOCK` | Not logged in, exit 1. |

No credentials were extracted, copied or changed. Environment presence checks printed names and booleans only. `USER` is non-secret process identity context; its removal prevents this installed CLI from finding the existing login in these checks. The diagnosis does not establish serving-model entitlement or successful inference.

## Original next scope, subsequently exercised

1. Preserve `USER` in `scripts/pilot_claude_code.py`'s sanitized child environment and add a regression fixture that requires it for the authentication precheck. Preserve credential exclusions and all other containment controls.
2. Run focused transport/model-adapter tests and an independent review. Recheck authentication metadata only before inference.
3. With separate renewed smoke authority, use one Claude-only synthetic inference invocation under the same 4,096-byte input, 1,024 requested output-token, 128,000-byte output and 120-second-per-process limits. No automatic retry. The already successful Qwen inference need not be repeated.

At this original checkpoint the correction had not been applied. The follow-up table above records the subsequent individual approvals and outcomes. Final-panel authority, live call ceilings for that panel, final input freeze and human arbitration remain separate.

## Local receipts and preservation

All detailed artifacts are under the ignored `runs/pilot-smoke-2026-09-17-001/` directory:

- `attempt-started.json` prevents accidental re-execution.
- `execute.py` and `qwen_request.py` retain the exact bounded smoke driver and fixed-loopback child. Run with the checkout's `.venv/bin/python`; the system Python does not supply the project's dependencies.
- `synthetic-input.json` records the entire Qwen request; no decision packet was included.
- `qwen-before.json`, `qwen-after.json`, `qwen-local-proof.json` and `qwen-residency.json` retain the local identity evidence.
- `qwen-response.json`, `qwen-process.json`, `qwen-usage.json` and `qwen-result.json` retain the response, measured usage, bounds and accepted outcome. The usage receipt records its initial incomplete validation state; the subsequent result records completed validation.
- `claude-attempt.json` and `claude-receipts.json` show `inference_started: false` and `auth_status_failed`.
- `smoke-result.json` is the immutable partial outcome; `auth-diagnostic.json` records the subsequent metadata-only investigation.

The decision packet seal remains `2b1ec30670a679d39e29e260b0c3b9881f29e5c47ebd06dcb9c469938ecd45f5`. No real decision record or Arbitration section was authored or edited. No core transport correction, global model default, credential, persistent service, Git delivery or release operation was performed in this smoke.
