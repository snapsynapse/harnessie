# Controlled-review pilot preparation

Date: 2026-09-17, local session date
Scope: Harnessie-local implementation and deterministic verification, approved by Sam after the session scope review. Live inference and Git delivery were not approved or performed.

Subsequent state: Sam separately approved synthetic smokes and an [offline stream-adapter correction](pilot-stream-adapter-2026-09-17.md). The [execution record](pilot-smoke-2026-09-17.md) reports local Qwen success, Claude answer attribution and unresolved additional Haiku usage. This document retains the historical preparation checkpoint and original proposal; the correction record owns current implementation and policy status.

## Outcome

The confirmed question is executable as a disposable scripted rehearsal through the real runner, journal, open-record exporter and pinned AIDR reference lint. The experimental Claude Code transport and Qwen metadata collector have offline failure coverage and independent review. This is preparation evidence, not a live panel verdict or public provider-support claim.

The authoritative question remains:

> Should Harnessie proceed with a bounded bid-record contract after its named exposure and budget gates, while leaving dispatch selection unchanged?

## Implemented boundary

| Surface | Responsibility |
|---|---|
| `scripts/pilot_contract.py` | Validated finite limits; zero-call default; atomic attempt reservations consumed even on failure. |
| `scripts/pilot_claude_code.py` | Non-registered `ModelInterface` adapter; Max auth-class precheck; sanitized environment; native capabilities disabled; argv and stdin execution; bounded process output/time; group cancellation; structured tool requests for Harnessie to execute; model identity and usage refusal; failure latch. |
| `scripts/pilot_identity.py` | Local-only, proxy-free, redirect-free metadata reads; exact method/path pairs; full tag and FROM digests; configured prompt/parser/sampling identity; canonical fingerprint and drift refusal. |
| `scripts/pilot_prepare.py` | Named-source allowlist; text/credential-shape checks; exclusive new destination; byte inventory; inward manifest; separately retained seal; unexpected-input, symlink and drift refusal; sealed-plan identity capture wrapper. |
| `scripts/pilot_runner.py` | Scripted-only real-runner rehearsal; provider factory/network guards; immutable-input checks; dissent/agreement fixtures; source-preserving open export; pinned lint; preserved human halt on resume. No live execution CLI. |
| `MANIFEST.in` | Excludes experimental pilot scripts and their source-only tests from package distribution. |

The Claude process uses `--safe-mode`, an empty native tool set, strict empty MCP configuration, empty settings sources and no session persistence. It uses an explicit print instruction with the neutral request on stdin. These flags were checked against installed Claude Code 2.1.261 help. They are not evidence of actual model behavior or OS-level isolation. The existing wrapper release is not used as a containment claim.

Auth metadata and inference are distinct subprocesses within one reserved attempt. A failure latches the adapter, so the runtime's ordinary error retry cannot silently launch another provider call. Missing primary token usage refuses acceptance; receipts retain unknowns and reported cache usage. `AssistantTurn` has legacy numeric defaults on errors, so error events are not authoritative evidence of zero cost. Pilot receipts and the invalid outcome must accompany them. Dollar cost is always unknown for the subscription transport.

Limits count CLI invocations, not invisible server-side requests. The installed CLI exposes no documented `--max-turns` flag in its help. The output-token setting is requested through the CLI environment; the independent process byte/time limits provide local bounds. Actual enforcement and structured-response behavior remain smoke-test questions.

## Frozen local artifacts

Current disposable root: `runs/pilot-preparation-2026-09-17-v2/`.

- Input manifest: `pilot-manifest.json`, 26 files and 200,535 bytes.
- Externally retained manifest SHA-256: `2b1ec30670a679d39e29e260b0c3b9881f29e5c47ebd06dcb9c469938ecd45f5`.
- Declared participants, four-stage candidate call graph and synthetic smoke proposal: `pilot-provider-plan.json`.
- Rehearsal evidence: `runs/pilot-rehearsal/preparation-receipt.json` below the disposable root.
- Scripted AIDR: `runs/pilot-rehearsal/export-rehearsal/decisions/AIDR-9999-scripted-pilot-rehearsal.md` below the disposable root. Its Arbitration section is empty; it is never a real decision record.
- Qwen metadata evidence: `runs/qwen-metadata-receipt.json` below the disposable root. Two metadata snapshots matched; neither bracketed live inference.

The packet includes the confirmed question, evidence index, AIDR-0009 and design draft, preparation/readiness audits, four attributed readiness reviews, bidding fixtures, and relevant routing, cascade, containment, loop, interface and adversarial sources. It excludes the historical ignored workspace and the bulk runner source, keeping the evidence packet smaller. The complete exact allowlist is code-owned in `SOURCE_FILES`; each copied source is bound by working-tree bytes, not HEAD alone. The recorded base revision is `aae3daa6e46858f1bc8dd39061d9973a2d73126a`.

Whole-packet bytes are not a model token count or proof every source was read. Each Claude request has its own input-byte ceiling. The attended live pilot must inspect actual request sizes, tools/context overhead and exposure evidence; a larger request refuses rather than silently truncating. Hash checks detect drift; they do not claim adversarial concurrent-writer isolation. The known-pattern secret scan is not a substitute for reviewing the final disclosure set.

## Verification

- Independent combined pilot suite: 55 passed, using nonoverlapping test files.
- Final full offline suite with live-provider opt-in disabled: 765 passed, 9 skipped, 28 strict expected failures. The skips and expected failures remain visible; they are not claimed as passes.
- Deterministic evaluations: 66/66 passed.
- Configuration: valid; outward and inward manifests: passed; generated documentation: current; ecosystem pins: matched; diff whitespace: passed.
- Wheel and sdist built locally with no build isolation or dependency installation; both excluded all pilot scripts/tests. Existing release-artifact inspection and `twine check` passed. These disposable 1.4.1 builds are not a release.
- Real mock rehearsal: eight scripted turns, zero live calls, valid 46-event chain, open export and pinned reference lint passed, unchanged inputs, `needs_arbitration` before and after resume, zero model calls on resume. Separate agreement fixture also preserves the halt.
- Read-only provider metadata: Claude Code 2.1.261 with existing Max auth class; Ollama client/server 0.34.1 and local Qwen tag. Qwen receipt fingerprint: `a52cb2ad1318644ab99cf81ba020bae67475b0de8dda78b4e70a7dada49cf560`.

Independent review found and resolved incorrect metadata method/path admission, missing sealed configuration binding, skipped malformed FROM directives, unsupported auth arguments, missing-usage acceptance, malformed-schema exceptions and subprocess descendant cleanup. The real metadata check additionally found Ollama returns bare 64-hex tag digests; the corrected normalizer and realistic fixture passed, followed by successful local metadata capture. No inference was used for diagnosis.

## Next approval: synthetic transport smoke

This proposal is not permission. All stored live allowances remain zero.

| Participant | Proposed maximum | Exposure | Limits |
|---|---|---|---|
| Claude Code Max, exact requested `claude-fable-5-1` | One inference CLI invocation, preceded by auth metadata check | Fixed synthetic smoke instruction and response schema only, sent to Anthropic | 4,096 input bytes; 1,024 requested output tokens; 128,000 output bytes; 120 seconds per subprocess. |
| Local Ollama, exact `qwen3.8:latest` | One chat-completion request, with metadata before and after | Same synthetic instruction, local loopback only | 4,096 input bytes; 1,024 requested output tokens; 128,000 response bytes; 120-second bounded execution. |

Synthetic instruction: return `PILOT_SMOKE_OK` in the requested response format, without requesting or executing tools. The decision packet, repository evidence and real decision question are excluded from this smoke.

Proposed retries: zero automatic retries. Failure preserves the attempt and stops; any additional invocation is a new human decision. This is a fresh proposal for a transport-only smoke, not reinstatement of an earlier rejected pilot limit. Sam may amend any limit before dispatch. Missing usage, unexpected identity/fallback, malformed output, exceeded bounds or unequal completion leave readiness incomplete. Record requested versus reported identity; neither configuration nor model agreement authenticates the serving model.

After smoke evidence review, re-freeze the pilot and present the final disclosure set and per-stage invocation/retry limits for separate approval. The four stages are Claude position, Qwen position, Claude objection and Qwen objection. The illustrative four turns per stage/16 total remains unapproved. The exported live record must remain open until Sam authors Arbitration. No source-run resume is implied by arbitration of an exported record.

## Retained work

The original ignored pilot handoff remains pending for live smoke, final pilot and human arbitration. The September 17 acceptance/adoption/interoperability handoffs remain proposed independent packets. Existing uncommitted planning work was preserved. No Git commit, push, PR, merge, release, provider install, auth change or persistent-service change occurred.
