# Isolated Qwen smoke preparation

Date: 2026-10-03 (America/Denver)
Scope: offline invocation driver, exact request proposal and injected regressions
Preparation status: driver verified; metadata-only candidate prepared with zero inference calls. The subsequent separately approved [smoke result](pilot-qwen-smoke-result-2026-10-03.md) records one completed attempt and consumed approval.

## Prepared behavior

`scripts/pilot_qwen_smoke.py` prepares one independent local `qwen3.8:latest` smoke. Its CLI only creates a new private candidate directory containing exact `request.json` bytes and `proposal.json`. Preparation reads source files to seal implementation hashes and accesses no model, service or account. It leaves `live_allowance` at zero and current identity absent. No approval record is generated.

The request contains only the synthetic instruction to return `PILOT_SMOKE_OK` through the existing neutral structured response contract. It offers no tools and includes no decision evidence. Endpoint selection is fixed to the existing local Ollama route at `127.0.0.1:11434/v1`, using its HTTP loopback transport. There is no cloud fallback.

| Bound | Value |
|---|---|
| Proposed inference attempts | 1 |
| Automatic retries | 0 |
| Inference timeout | 120 seconds |
| Request and evidence ceilings | 4,096 bytes each |
| Requested output | 1,024 tokens |
| Reported output acceptance ceiling | 1,024 tokens |
| Response ceiling | 128,000 bytes |

The output token ceiling is checked after generation. It cannot prevent already incurred model work. Dollar cost remains unknown. The 120-second timeout bounds inference transport; before/after metadata probes add elapsed time outside that inference deadline.

## Authority and evidence

The execution API defaults to refusal and is not exposed through the CLI. Like the existing panel operator API, it requires a separately supplied exact proposal seal and a time-bounded approval record attributed to Sam Rogers. Local operator code and records are trusted; matching strings do not authenticate a human. Editing a proposal or setting a preparation flag does not grant execution authority. The operator must establish the actual human authorization before invoking this API.

The proposal binds its absolute evidence directory, exact request hash and length, model, endpoint, limits, declared client configuration, supplied identity with timestamp, and the existing `implementation_hashes()` inventory. Any implementation drift requires a new proposal and approval. Identity must be checked within 15 minutes before dispatch, and the adapter captures and compares identity immediately before and after inference. The default capture uses `local_qwen_identity`, matching the panel's strict preflight: it rejects cloud/remote metadata and requires local, regular, nonempty FROM blob files without symlink paths. Loopback routing alone does not prove local inference.

Before either identity capture or dispatch, the driver creates and syncs an exclusive attempt directory and consumed guard. Existing attempts refuse reuse, including attempts whose guard, response or final receipt could not be fully persisted. Files are created exclusively with mode `0600` under private `0700` directories, and symlink paths refuse. A failed attempt is preserved for inspection.

Private evidence includes the request and proposal, attempt guard with approval binding, before/after identities, bounded raw response when available, normalized and raw usage, elapsed time and final outcome. Response-capture failure still allows the adapter to extract usage before the driver refuses acceptance. Final-receipt persistence failure leaves the attempt consumed and the available response evidence intact.

Acceptance requires exactly `PILOT_SMOKE_OK`, no tool calls, normal completion, complete usage, unchanged identity and reported output no greater than 1,024 tokens. A successful smoke establishes basic current transport readiness only. It does not test full-evidence review quality or latency.

## Verification

The new tests first failed to collect because the new driver did not exist. After implementation and parent review, the repository interpreter ran 26 new smoke tests plus 24 existing adapter tests: 50 passed. All new cases use injected synthetic identities and transport responses. No test accessed live metadata or inference.

Coverage includes exact request parity with `QwenPilot`, zero-authority preparation, no-confirmation refusal, request/proposal/implementation drift, stale identity and approval, missing usage, malformed response, identity drift, timeout, wrong sentinel, exact-limit and one-over output tokens, oversized response, symlinks, private modes, durable guard ordering, no reuse, and persistence failures before and after dispatch. Default-capture tests verify both strict local-residency checks and refusal before dispatch when remote metadata or local blob validation fails. `git diff --check` passed.

## Metadata-only candidate preparation

After implementation and independent review, the parent session read the local client version and used the strict local metadata/blob preflight. At 2026-10-03 20:19:08 America/Denver (2026-10-04 02:19:08 UTC), client and server reported 0.35.1; qwen3.8:latest matched digest 22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643. Local FROM blob checks passed. These were metadata and filesystem checks with no generation request.

The resulting private proposal is runs/qwen-smoke-candidate-2026-10-03-output-cap/proposal.json. Its canonical SHA-256 is b6e3684e1a7179c10ff1c404df751caf0b1da6719b1e6d02a5d2fe0ff4089306. Exact request length is 1,074 bytes and its SHA-256 is 44b59509ed87531a9ad7dcf769f606f9b8b27455906991d0fb5ca210ce6b60c7. The proposal binds the reviewed implementation and observed identity, with live_allowance zero. At preparation no approval or attempt existed. The 15-minute identity admission window ended at 20:34:08 America/Denver; the separately approved attempt was reserved within that window at 20:33:06.

## Subsequent approval and consumption

Sam approved this exact candidate with "Commit locally then proceed". Local commits preceded the single dispatch, and the [result audit](pilot-qwen-smoke-result-2026-10-03.md) retains its outcome. This candidate and approval are consumed. Any additional inference needs a new proposal and authority; the smoke approval does not authorize a full panel. Do not reuse the consumed September driver or any panel approval. The preparation metadata alone was not inference evidence.
