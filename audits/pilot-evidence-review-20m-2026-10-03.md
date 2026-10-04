# Full-evidence local review with a 20-minute limit

Scope: one explicitly approved local substantive review, no retries or Claude calls. Decision date: 2026-10-03, America/Denver.

## Authority and input

Following the [consumed five-minute timing probe](pilot-evidence-timing-probe-2026-10-03.md), Sam approved a substantive review but selected a 20-minute per-call timeout instead of the proposed 30 minutes. The approved output ceiling is the original 4,096 tokens. All 17 frozen source bodies remain unchanged, and abstention remains available. No model substitution, cloud fallback, download, service configuration, package release or push is included.

The exact native request is the original [full-evidence handoff](pilot-evidence-handoff-2026-10-03.md): 212,224 bytes, SHA-256 `a06f3262e5633af2c4d0e5f4d7e52c9b12a43d5e694fa4f002c76f40c7bbc30c`. It contains 193,658 source bytes and no current Claude panel response, model-emitted retrieval commands or fabricated tool results.

## Timing and acceptance contract

The opt-in review transport must enforce 1,200 seconds in both its supervisor and HTTP child. The old capture transport and consumed probes retain their 300-second maximum. Input/evidence and response ceilings remain 256,000 and 128,000 bytes respectively.

This new review seals a fresh-at-start identity policy: the preparation identity observation must be at most 15 minutes old initially and immediately before dispatch; a fresh matching physical identity is observed before and after the call. The original preparation observation does not expire the result halfway through an approved 20-minute request. Approval/proposal must provide at least 1,320 seconds of runway before dispatch and remain valid on return. The operator records a 30-minute approval envelope to cover the 20-minute call plus checks; this is not a 30-minute call allowance.

One exclusive attempt guard consumes authority before dispatch. Raw bounded response bytes are retained privately before parsing. Known usage survives later structural, identity, authority or storage failures. A completed response must finish normally and validate against the direct review schema and citation-path rules. Truncation is incomplete, never a completed review. Structural validity is not evidence that citations support findings; semantic assessment and Sam's arbitration remain separate. Even a valid independent position does not complete the panel's objections or export.

The agentic-harness skill informed the explicit timing, provenance, single-use and acceptance boundaries. No new live result is claimed by this preparation record.

## Verification and outcome

- Transport worker: 54 capture tests and 121 combined transport/legacy regression tests passed.
- Review worker: 197 focused tests passed, including 41 new review tests.
- Independent pre-dispatch PASS: 197 review/probe/handoff/capture tests and a separate 121-test legacy transport regression passed; exact full-source parity and private operator scope verified.
- Parent frozen-tree full pilot plus trust/inward manifest suites: 493 passed in 23.28 seconds.
- No live calls occurred during implementation or verification. The single approved call is pending.
