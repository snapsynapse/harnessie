# Offline Qwen streaming preparation, 2026-10-11

Scope: repair the pilot transport fixtures and prepare bounded private streaming capture. Sam authorized proceeding with the proposed actions, staging, commits, pushes and appropriate releases. This tranche makes no model call and grants no new live allowance.

## Transport fixture diagnosis and repair

The inherited-pipe test reproduced both alone and in the 30-test transport suite. Its fake authentication timed out before inference, so the missing child PID was not evidence of a cleanup defect. The fixture used `/usr/bin/env python3`, which selected a different interpreter from pytest through PATH. All fake CLI fixtures now use the test interpreter.

The child-cleanup regression now waits for the fake parent to exit after its child writes the PID, then starts the transport drain deadline. This establishes the intended condition independently of authentication and interpreter startup. The child inherits stdout; after the timeout it cannot write its survival marker. Cleanup still uses the real process-group kill path.

The separately reported terminal-status test passed during reproduction. Its five parser cases now use a five-second test allowance to isolate refusal validation from process-startup variability. Its earlier failure's exact cause is not established. No production timeout, parser or policy was changed. Both named tests passed alone; all 30 transport tests passed together.

## Separate streaming contract

`scripts/pilot_qwen_stream.py` prepares a distinct request from the exact approved 17-source request, changing only `stream` to true and adding `stream_options.include_usage`. It reuses the original UTF-8 JSON encoder. Reversing those two fields reconstructs the original native request byte for byte, including Unicode evidence. Every source body, prompt, schema, output cap and sampling field remains unchanged.

The new transport reuses the existing supervisor, allowlisted local endpoint, no-redirect/no-proxy HTTP child, bounded stdin and private response capture. Raw SSE bytes are saved before inspection. No public provider registration, CLI dispatch command or execution authority is added. The non-streaming reviewer and all consumed approvals remain unchanged.

The inspector requires one consistent response identity, one assistant choice, a normal stop, a final usage receipt and the SSE completion marker. It refuses malformed or incomplete frames, duplicate completion, native tools, inconsistent identity, incomplete JSON, missing or conflicting accounting and output above 4,096 tokens. It retains every reported usage object on refused streams and never deduplicates equal receipts. Reasoning text remains only in private raw capture; the inspector returns its byte count, not the text. Citation membership and schema validity do not establish semantic support or human arbitration.

Ollama's [OpenAI compatibility documentation](https://docs.ollama.com/api/openai-compatibility) lists streaming and `stream_options.include_usage`. That published interface description does not establish acceptance by this installed server; no request reached it during preparation.

## Sealed offline candidate

The corrected private candidate is `runs/qwen-stream-preparation-2026-10-11-v2/`:

- Native request: 212,263 bytes, SHA-256 `86d9e69ec9d93568b389fdf0f10ab57ebb4f2efdfd06a2dee2bb09d53ce0425e`.
- Preparation seal: `32311a141d4ed377254cf44bac43c88a73c79f0c52c21e5a3a309cbff707f4e8`.
- Original native request: 212,224 bytes, SHA-256 `a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c`, unchanged.
- Limits: one call, 1,200-second per-call timeout, 4,096 output tokens, 256,000 input/evidence bytes and 128,000 captured response bytes, with one overflow sentinel.
- Original fresh-at-start identity policy and 1,320-second minimum authority runway are included as proposed constraints. Live allowance is zero.
- The root and proposal/request files have private 0700/0600 permissions. Neither the payload nor raw reasoning is tracked in Git.

The first offline candidate used an ASCII-normalizing encoder; the Unicode round-trip check exposed the mismatch. It was never dispatched. The corrected candidate is separate, and the original consumed attempt is untouched.

## Verification

- 33 synthetic streaming tests cover real child-pipe fragments across UTF-8/SSE boundaries, CRLF, malformed frames, partial EOF, timeout, overflow, duplicate completion, response identity drift, denied native tools, absent/ambiguous/inconsistent usage, exact-limit/one-over accounting, Unicode request parity and storage failure. No endpoint is contacted.
- Full offline suite: 1,263 passed, 14 skipped, 28 expected failures in 47.45 seconds. The skips remain environment-specific missing coverage, not passes.
- Deterministic evals: 70/70. Trust manifest: 21 files. Inward manifest: 16 files. Authoring validation: nine documents, schema v1.
- Ecosystem readback: Verify Action and Homebrew both pin core 1.5.0; wrappers remain independently released at 0.1.0.
- Documentation and release-state checks: 38 passed; generated docs check: nine pages; whitespace clean. A local wheel and sdist passed artifact inspection, and archive inspection confirms all pilot scripts/tests and private run/handoff artifacts are excluded. These disposable builds were not published.

## Next boundary

Prepare a fresh identity-bound consume-once execution wrapper and approval record before another live call. Independently review that exact wrapper and payload before asking for inference approval. The low-level transport is not an approval gateway. This offline seal cannot be used as live authority, and no timeout increase is implied. Streaming does not accelerate input processing or guarantee completion.

The prior twenty-minute review still timed out with zero response bytes and unknown usage. Partial streamed output will remain an incomplete review. A future valid isolated position would not retroactively finish v8; the panel still needs its objection sequence, open export and Sam's arbitration. The active pickup queue remains the Qwen handoff.
