# Offline streaming wire-budget repair, 2026-11-11

Scope: Sam authorized offline repair and independent verification, retaining the 1,200-second and 4,096-token limits, followed by stage, commit and push after checks. No inference, model metadata lookup, service change or live approval occurred.

## Reconciliation and boundary

The [October 26 consumed attempt](pilot-streaming-review-result-2026-10-26.md) reached its 128,000-byte wire cap plus one sentinel before producing an answer or final usage. Its 559 complete JSON frames contained only 2,584 decoded reasoning bytes. SSE framing and metadata spent a budget inherited from non-streaming JSON capture.

The original checkout was clean on `security/seatbelt-unix-socket`, one unpushed commit (`520cc08`) above fetched `origin/main`. That unrelated security commit was preserved. This repair was built in an isolated checkout from `origin/main` at `475633a293b12abd4d39fc6807581a5afcee2adf`; it does not include that commit.

## Repair

- Streaming now has a fixed 4 MiB (4,194,304-byte) raw SSE envelope, retaining at most one extra byte as an overflow sentinel. This is separate from the unchanged 128,000-byte combined UTF-8 content/reasoning acceptance budget.
- The private transport captures bounded wire bytes before interpretation. The decoded-text check runs after capture; on overflow, the parser stops growing its answer buffer, refuses acceptance and continues inspecting later accounting.
- A distinct streaming child marker and fixed-profile validator accept only the new wire envelope and the original 1,200-second deadline. Existing 120/300-second diagnostic and 1,200-second non-streaming paths keep their prior limits.
- Input/evidence caps, 4,096-token output cap, one-call guard, zero retries, exact request bytes, local-only identity checks, authority runway/expiry, private accounting and incomplete-response refusal remain intact.
- Streaming policy, offline preparation, execution proposal/result and approval action are version 2. The new action is `execute_one_local_qwen_streaming_review_v2`. Earlier actions/proposals cannot authorize the expanded envelope; changed implementation hashes also invalidate earlier seals for current execution.

A finite wire bound cannot accommodate arbitrary provider padding or unlimited fragmentation. The new budget gives explicit bounded framing headroom; it does not guarantee completion or higher throughput, and it does not establish actual model token counts.

## Regression and independent verification

A synthetic complete stream with 4,096 choice chunks, small decoded text and provider-style reported output usage of 4,096 first failed at the old wire cap, then passed after the repair. Tests cover exact wire/text boundaries, overflow sentinel retention, combined content/reasoning UTF-8 accounting, post-failure known/unknown usage, missing completion/usage, separate child profiles, old-action refusal and sealed-policy drift.

Fresh-context reviewer `/root/wire_budget_verifier` independently found a null-alias bypass: `reasoning: null` hid nonempty `reasoning_content` from the byte counter. A two-direction regression reproduced one failure before the fix and passed both cases afterward. The reviewer independently checked exact combined 128,000-byte acceptance and overflow refusal with either alias explicitly null, with known usage retained. No actionable findings remained. The reviewer ran 199 focused offline tests in 7.33 seconds and made no source edits, network/metadata/model calls, service changes, credential access or consumed-run writes.

| Reviewed file | SHA-256 |
|---|---|
| `scripts/pilot_qwen_capture.py` | `92e016704cb6f36e4845bfc41f37b48e5e74ffa9042ca7b8b9db3ee26a46ee4c` |
| `scripts/pilot_qwen_stream.py` | `7387f31e0801ce6b30e44227a77c378e60e527bc158a1e1dee618900f53d3ecc` |
| `scripts/pilot_streaming_review.py` | `481427a6201e901e1e139102e1aee70c9bfe7e25fa4977fcd7f01c04e2df07d1` |
| `tests/test_pilot_qwen_stream.py` | `904a42fa16965d1858f5c5ff31cb5a7ccfc213d28044f056473ec9de79bea7cb` |
| `tests/test_pilot_streaming_review.py` | `024e9c12e7f405413d83d7991608ebaa95ec79c6158d727d62d38cec06ba3c82` |
| `tests/test_pilot_wire_budget.py` | `49525dd9e136ed75f8d59f442db51ca3fe62016ec802eaa684f9bd348ca75b64` |

The parent verified the same final hashes. The final full offline suite passed 1,344 tests, with four skips and 28 expected failures, in 45.06 seconds. All 70 deterministic evals, configuration (nine documents), outward/inward manifests (21/16 files), ecosystem validation and generated docs (nine pages) passed. Fresh wheel/sdist builds passed archive checks; all experimental pilot code/tests remain excluded. No core or downstream version change or release is needed. Same-model independent review is not cross-vendor corroboration or live-model evidence.

## Private preparation and remaining authority

`runs/qwen-wire-budget-preparation-2026-11-11/` contains the new offline preparation and verification receipt, seal `643485bdaa3ff203d381b29c095a811018168e012f66b22c2200703e103e3d38`. Its unchanged request is 212,263 bytes, SHA-256 `86d9e69ec9d93568b389fdf0f10ab57ebb4f2efdfd06a2dee2bb09d53ce0425e`, and all 72 implementation hashes are bound. Live allowance is zero; no approval or attempt exists. The actual missing-authority gate refused before metadata or transport, with sockets and metadata explicitly blocked.

Replay of the saved 128,001-byte October 26 capture under the new parser still refuses the incomplete response, preserves unknown usage and recovers no review. Before/after hashes of its proposal, request, approval, guard, outcome, accounting, identities, raw capture and receipt are identical. The consumed capture still has SHA-256 `9862773cda8f1e772bd232539b447feaed9430cb15904e5d1c7c1f65b2a0ef74`; it was not resealed or retried.

Any future inference requires fresh physical metadata, a new version-2 execution proposal, independent verification and a separate explicit one-call approval. This offline preparation grants none of those calls. The prior incomplete review and remaining full-panel work stay incomplete.
