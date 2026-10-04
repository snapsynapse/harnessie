# Deterministic evidence handoff

Date: 2026-10-03 (America/Denver)
Scope: experimental, repository-local preparation only. No public provider support or release change.

## Decision and outcome

Sam approved providing Qwen the frozen evidence directly, preserving its ability to abstain. This replaces the proposed tool-protocol repair as the next evidence-review lane. Tool-use reliability remains a separate experiment. The agentic-harness skill informed the separation between mechanically complete inputs, model judgment and human acceptance.

Implemented `scripts/pilot_evidence_handoff.py` and preparation-only tests. The builder verifies the consumed v8 packet without changing it, selects exactly the 17 approved `SOURCE_FILES`, and includes every UTF-8 source body with its path, SHA-256 and byte count. No summarization, truncation or source omission is allowed. Approved historical review artifacts remain evidence; current Claude panel positions, objections, approvals and raw runtime captures are excluded.

The actual first request uses native system and user messages. Instructions are separate from a JSON bundle explicitly labelled untrusted evidence. There are no tools, fabricated tool messages or synthetic retrieval claims. This is an instruction/data boundary, not a guarantee against model-level prompt injection. The requested model remains `qwen3.8:latest`, temperature zero, non-streaming, with a 4,096-token output request.

The direct review schema supports recommend, oppose, alternative and abstain. Non-abstaining reviews need a valid source-path citation. An uncited abstention is permitted with an explanatory summary and nonempty uncertainties. Validation proves structure and citation-path membership only; it does not prove that a citation supports a finding or that a summary adequately explains abstention. Semantic review and human arbitration remain separate.

## Private preparation receipt

New ignored root: `runs/qwen-evidence-handoff-2026-10-03/`. Directory mode 0700; each artifact mode 0600. Writes are exclusive, with completion metadata written last. No dispatch API, approval, consumed-attempt marker or provider response exists in this preparation.

| Check | Result |
|---|---|
| Frozen packet | `4b47b12d9cd11a01ac36b225c39a59bca61358caa9b0f4eccd845c903270d3f4` |
| Complete source bodies | 17 |
| Source bytes | 193,658 |
| Encoded request bytes | 212,224 of 256,000 |
| Request SHA-256 | `a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c` |
| Evidence manifest file SHA-256 | `bf2f2b4cbc69592e9cda90d41540f9e8624de2096f148fd69a6d733fe68dda27` |
| Preparation file SHA-256 | `0ff04afddde7e8ceddc390edb0da9cbb48ad2923a5952c26df35b48012311d24` |
| Bound implementation files | 66 |
| Delivery / model calls | False / zero |
| Input tokens / processing time | Unknown / unknown |

The saved request is a complete prospective wire payload, not proof of delivery, complete provider ingestion or model understanding. Byte fit does not establish token fit. The new direct response format has not been exercised against the live backend.

## Resource preflight

Read-only inspection found no supported installed exact-token-count path. The project environment lacks tokenizer libraries; the Ollama CLI exposes no tokenizer command. Bundled llama tooling has no documented vocabulary-only/count mode in its help. Its tokenizer symbol alone is insufficient without matching headers and a safe vocabulary loader; no ABI was guessed and no model/server was launched. Saved model metadata contains no usable vocabulary/merge data for independent exact counting.

Historical server logs show a 262,144-token context, not fresh capacity proof. Earlier observed generation rates of approximately 5.4 to 7.2 tokens/second imply that generating all 4,096 allowed output tokens alone would take about 569 to 759 seconds, before this much larger input is processed. This conditional calculation is not a full-evidence latency measurement. The consumed probe's 300-second timeout is therefore not established as sufficient. No timeout, byte cap, output allowance, model configuration or service was changed.

## Verification

- Tests-first missing-module failure preceded implementation.
- Worker focused regression: 75 passed, including 31 handoff tests.
- Parent full pilot suite: 368 passed in 21.31 seconds.
- Independent verifier PASS: exact v8 source/body parity and request hash reproduced with socket and subprocess access disabled; focused regression 48 passed and full pilot suite 368 passed in 21.35 seconds. Acceptance covers offline preparation only, not live compatibility, delivery or understanding.
- Private artifact permissions and hashes read back after preparation.

Fixtures cover missing, tampered, unexpected, symlinked, non-UTF-8 and oversized evidence; encoded size overflow; deterministic payloads; hostile source instructions; absence of current runtime conclusions; abstention and invalid citations. These are offline tests, not live model evaluations.

## Next boundary

Keep all consumed v8/probe artifacts unchanged. Do not reuse the old probe driver, whose request hash is intentionally fixed to the old 6,568-byte tool-oriented input. The new 212,224-byte direct request needs a separately bounded, consume-once local execution path with exact identity and request binding, private response capture before parsing, preserved usage and a direct-schema parser. No neutral tool wrapper or task_complete fabrication should be introduced to make it pass the old workflow.

Before dispatch, resolve token/context feasibility and choose an explicit timing bound. If safe offline counting remains unavailable, a separately authorized, full-evidence measurement with a reduced output allowance can establish prompt usage and prefill behavior, but it is itself inference and may time out; it must not be called a completed review. No inference or timeout expansion is authorized by this preparation receipt. A later evidence-backed position still does not complete objections, export or Sam's arbitration.

Subsequent authorized measurement: the [one-call timing probe](pilot-evidence-timing-probe-2026-10-03.md) used the same full input with a 256-token output cap and timed out after 300 seconds. Correlated server logs show input processing, not a context-capacity rejection; no final response or usage was obtained. The probe is consumed. Its audit owns the result and proposed longer substantive-review boundary.
