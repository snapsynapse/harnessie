# Fresh streaming execution wrapper, 2026-10-26

Scope: prepare and independently verify the Qwen streaming execution wrapper without running inference. Sam requested this offline tranche on October 26; the earlier staging, commit and push authorization remains the delivery boundary. No inference authority is created by implementation, testing or this audit.

## Reconciliation

The explicit Qwen pickup is `handoffs/2026-10-04-qwen-review-resume.md`, updated October 11. At pickup, main was clean at `fdfa7d7`, with zero commits ahead or behind its upstream and the default branch after fetch. The sponsor and README handoffs are separate queues and were left untouched.

The October 11 streaming preparation seal, request hash, implementation hashes and byte reversal matched before this work. Its 212,263-byte streaming request reverses to the original 212,224-byte native request, preserving all 17 frozen source bodies. The earlier twenty-minute attempt remains consumed: `process_timeout`, zero returned bytes and unknown final usage. No old request, approval, guard or outcome was modified or executed.

Read-only Ollama metadata now reports client/server 0.40.11, rather than the earlier 0.35.1 observation. The selected `qwen3.8:latest` tag still matches pinned model digest `sha256:22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`. Only version, tag and show metadata routes were used. No generation, pull, service startup, configuration change or fallback occurred.

## Implemented boundary

`scripts/pilot_streaming_review.py` supplies a trusted operator API with separate `prepare` and `execute` functions, proposal schema `harnessie-streaming-review/1`, and approval action `execute_one_local_qwen_streaming_review`. It records an explicit human approval supplied through that API; it does not authenticate the approving human. No dispatch CLI or registered provider was added.

Preparation seals exact streaming request bytes, the model digest, physical identity, implementation hashes, stream policy and timing policy. It performs no metadata or inference I/O and leaves live allowance at zero. Earlier non-streaming action names, proposal roots or hashes cannot authorize this wrapper.

Dispatch requires fresh-at-start identity within 900 seconds, at least 1,320 seconds of authority runway, and an unexpired proposal and approval. An exclusive private attempt directory and persisted guard consume the attempt before further observation or transport. Authority and request bytes are rechecked after identity observation and transport construction. Identity and unexpired authority are checked again after response; the original identity observation does not expire an otherwise authorized twenty-minute call halfway through it. Concurrent calls cannot dispatch twice.

The limits remain one request, 1,200 seconds, 4,096 output tokens, 256,000 input/evidence bytes and 128,000 response bytes plus one overflow sentinel. No retry or timeout extension is introduced. The low-level HTTP transport retains its allowlisted local endpoint and no-redirect/no-proxy behavior.

Raw wire bytes are captured privately before parsing and compared with their retained byte count and SHA-256 receipt. Incomplete, malformed, over-limit, identity-drifted, expired or unpersisted results cannot become accepted reviews. Full raw usage objects stay in private accounting/capture files; public results retain normalized counters and distinct numeric usage receipts without provider-added text. Review text and reasoning do not enter the public result. A structurally valid response is still advisory, with semantic acceptance and human arbitration false.

## Independent findings and repairs

A fresh-context Codex reviewer independently reproduced three defects and reviewed their fixes:

- Timeout plus capture-write failure could hide recoverable accounting. The transport now retains a bounded private in-memory stdout fallback, allowing usage inspection even if stdout, receipt or fsync persistence fails. Failure still refuses acceptance and consumes the attempt.
- Provider-added text in a usage object could enter the public result. Full objects now remain private; the public numeric projection preserves separate duplicate or conflicting accounting receipts without returning arbitrary text.
- An escaped lone Unicode surrogate could abort inspection before later usage was retained. Each textual delta is now checked for UTF-8 encodability inside the frame refusal boundary; malformed frames refuse while later final accounting remains inspectable.

These are narrow experimental-pilot changes. The non-streaming execution contract and all previous consumed artifacts remain intact. Adding the new wrapper and fixes intentionally changes implementation hashes, so the old offline seal is historical and is not reused as current execution authority.

## Independent verification

Reviewer `/root/streaming_verifier` made no source edits and used no metadata, model, service, browser or credential access. Its final offline run, with `HARNESSIE_LIVE=0`, reported 175 passed in 7.21 seconds across the new wrapper, streaming inspector, capture transport and original evidence-review tests. Wrapper tests block sockets and live metadata; supervisor tests replace the child process with fixed synthetic Python fixtures. `git diff --check` passed. No actionable code findings remained.

| Reviewed file | SHA-256 |
|---|---|
| `scripts/pilot_streaming_review.py` | `583ac6e3238002dbf229722a8d8c98c0805eb0f8186facadfa598da584fbd6ff` |
| `scripts/pilot_qwen_capture.py` | `fd80f14cd47fce2bfbf6389671dc5e1c58bd71b01f04f4638de89ff38d660426` |
| `scripts/pilot_qwen_stream.py` | `c62e2051d4070922b3151c41e1adcce8729a2c74c8752206ffcbf7b934932bde` |
| `tests/test_pilot_streaming_review.py` | `a395edeb9ee58c9eb3339df235a610cae8dea56b419c4773051645d262046d44` |

The parent checked these hashes after review. The staged whitespace check found one extra final blank line in the new test; the reviewer independently confirmed the sole newline removal and accepted the final test hash below without requiring functional retesting. The full offline suite reported 1,310 passed, 14 skipped and 28 expected failures in 46.09 seconds; all 70 deterministic evaluation scenarios passed after the queue update. Trust and inward manifests passed for 21 and 16 files; authoring validation passed for nine documents; the nine-page generated-doc check passed. Skips and expected failures do not establish untested capability. This is independent execution/review in a separate agent context, not cross-vendor corroboration or live-model evidence.

## Fresh private candidate

`runs/qwen-streaming-review-candidate-2026-10-26/` contains the new proposal, exact request and offline gate-verification receipt:

- Proposal seal: `0ab6cb46cb79120e853ebaaa0b5977dc43a2b9429392003641b1e07756d26413`.
- Request: 212,263 bytes, SHA-256 `86d9e69ec9d93568b389fdf0f10ab57ebb4f2efdfd06a2dee2bb09d53ce0425e`.
- Metadata observation: 2026-10-26T18:27:37.467219Z, client/server 0.40.11, matching local model pin.
- Implementation binding: 72 runtime/pilot files. Root/files have private 0700/0600 modes.
- Live allowance: zero. There is no approval file and no attempt directory.
- An actual call to the new wrapper without approval refused with `live_authority_required` before observation or dispatch. No generation was attempted.

The preparation identity becomes stale after 900 seconds. If live work is selected later, capture metadata again and prepare a fresh proposal, then bind a separate explicit one-call approval to that exact seal. Do not edit this candidate in place or reuse consumed approvals. A new approval is not implied by today's code or delivery authorization.

## Remaining work

The next boundary is Sam's separately scoped inference decision, after fresh metadata and a new seal when necessary. There is no reason to widen the original time or output limits silently. Streaming preserves emitted output but does not guarantee faster generation or completion. A valid isolated Qwen position would still not finish v8 or supply the panel's objections, open export or human arbitration. Those remain in the existing pilot queue. A fresh wheel and source distribution passed the release-artifact privacy check; both exclude all experimental pilot scripts/tests. The seven changed public paths passed the private-term scrub, and generated docs remained current. This tranche requires no core package or downstream version change.
