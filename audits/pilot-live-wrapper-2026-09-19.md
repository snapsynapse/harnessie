# Guarded pilot wrapper implementation

Scope: execution of the [approved offline plan](pilot-live-wrapper-plan-2026-09-19.md). No live model inference, provider reconfiguration, Git delivery or release is authorized by this record.

## Implemented seams

| File | Responsibility |
|---|---|
| `scripts/pilot_execution.py` | Sealed proposal, disclosure and source binding, process/run ceilings, expiration, separate operator approval and explicit manifest confirmation. A proposal has zero live allowance. |
| `scripts/pilot_ledger.py` | Exclusive one-shot run ownership, fsync-backed hash-chain, intent before dispatch, receipt before progression, global/stage/participant accounting, uncertainty and refusal latches. |
| `scripts/pilot_qwen.py` | Fixed local route with no proxy/redirect/fallback; bounded child process; strict structured responses; before/after identity checks and complete usage. |
| `scripts/pilot_preflight.py` | Metadata-only Claude auth/version/binary check and local Qwen model/blob checks. No model invocation or setting changes. |
| `scripts/pilot_live.py` | Four-stage integration through the existing runner, injected rehearsal, separate guarded live entry point, open-record export and preserved human halt. |
| `scripts/pilot_prepare.py` | A separate zero-authority execution-candidate packet, while retaining the original mock-only preparation path. |

Public runtime modules, provider registration and schemas remain unchanged. The pilot imports the existing runner and supplies its reviewed models through the existing cache seam. The mock-only `pilot_runner.py` remains usable.

The ledger counts reservations, including failed attempts. It cannot assert the number of internal provider requests inside a Claude CLI invocation. All-model usage and cache-inclusive input remain in the authoritative operator receipts. The existing runtime's fixture USD accounting is not proof of zero cost; actual subscription dollars remain unknown.

## Read-only readiness findings

The current account preference is included allowance only. In the user-shared Claude Usage page, the account showed Max (5x), a Fable weekly allowance at 0% used, and usage credits enabled with a USD 50 monthly limit. This establishes an available allowance category but does not enforce the requested no-credit boundary. No switch, spending limit or account setting was changed. Live authority validation requires credits disabled, evidence of included Fable allowance and a fresh explicit billing check. The existing account state therefore remains a blocker.

Claude CLI metadata reported `2.1.261 (Claude Code)`, first-party Max authentication and the recorded binary hash. This is authentication/version evidence, not a new serving-model or billing verdict.

The fixed local Ollama metadata endpoint did not respond. A second bounded read-only connection check confirmed that `127.0.0.1:11434` was not listening. No service was started and no remote endpoint was substituted. Fresh Qwen identity evidence is unavailable; the earlier identity remains historical.

These findings do not block offline implementation. They do block live execution. The manifest and approval must be refreshed after readiness is resolved; saved UI/CLI observations are not indefinitely fresh authorization.

## Enforcement and limits

- The proposal is a review artifact, not permission. The live command additionally requires a matching operator approval record and explicit confirmation of its digest. Operator-owned local Python and approval files remain trusted; this is not cryptographic authentication of a remote caller or a sandbox against malicious host code.
- Both selected provider identities must pass metadata checks before the first panel call. Local Qwen is checked again before and after every request.
- Every request rechecks packet/source binding and, for live execution, current approval/evidence validity. Model construction or stage changes do not recreate the shared budget.
- Crash, uncertainty, refusal, unknown accounting, overage and receipt-write failure stop progression. The run directory is single-use; reopening it never resumes inference. Reconciliation is read-only, and any deliberate subsequent execution requires a separately reviewed run identity.
- Candidate ceilings are eight reservations per participant, four per stage, 400,000 aggregate reported tokens, and run-wide Haiku ceilings of 32,768 cache-inclusive input and 2,048 output tokens. Per-process bounds are 120 seconds, 256,000 input bytes, 128,000 output bytes and 4,096 requested output tokens. These are proposed ceilings, not approved calls or hard provider-side billing caps.
- Per-invocation Haiku limits remain 4,096 cache-inclusive input and 256 output tokens under `claude-max-haiku-overhead/v1`. Its purpose remains unclassified and it is not an independent reviewer.
- The call proposal allows up to three evidence-reading exchanges and one completion per stage. This is headroom, not proof that a live reviewer will finish or read every source. A stage that cannot complete within its limit stops; no auto-expansion occurs.

## Verification

Implementation and independent review passed offline. The full suite reported 837 passed, 9 skipped and 28 expected failures. The independent verifier passed 124 focused tests covering LIVE-01 through LIVE-06 and found no remaining source defect. Both distribution manifests, generated-doc parity, Python compilation and whitespace checks passed. A fresh wheel and source distribution excluded the pilot scripts/tests and browser artifacts.

The final scripted rehearsal made four Claude-labeled and four Qwen-labeled calls, with no provider inference. Its operator ledger verified all 33 records and the runner chain verified all 46 events. The actual exporter and pinned reference lint passed. The exported Arbitration section stayed blank; resume returned `needs_arbitration` with zero additional calls. The rehearsal root is `runs/pilot-preparation-2026-09-19-live/`; despite that directory name, this run was offline only.

The separate clean dispatch candidate is `runs/pilot-dispatch-candidate-2026-09-19/`: 26 files, 200,991 bytes, packet seal `626322d26c8bca5dd1afaf351612336eaa038aef504b106ad80f445dcfece742`. Its proposal is `runs/pilot-live-wrapper-2026-09-19/execution-proposal.json`, digest `6b41d10639aeafdd613f39c882740129a053b60d021a99433028268328b317fb`. It grants zero live calls and records both readiness blockers. The candidate uses a fresh runtime root so the rehearsal's run-specific boundary sidecar cannot contaminate dispatch preparation.

`runs/pilot-live-wrapper-2026-09-19/verification.json` binds the final implementation and test hashes to these results. `preparation-receipt.json` records the distinct rehearsal and dispatch roots. These are local, uncommitted artifacts; no live panel, human arbitration, Git delivery or release occurred.

The acceptance matrix covers zero-call refusal, cross-stage accounting, route/identity drift, interruption and disk failure, agreement and dissent, strict parsing, open export and the human halt. Rehearsals use scripted actors or injected transport bytes and are labeled accordingly; they are never treated as actual participant positions.

## Next live boundary

The final execution proposal will remain unapproved while usage credits are enabled and the local Qwen identity cannot be refreshed. Once those conditions are resolved, refresh the identities, billing observation, implementation hashes and manifest expiration; then obtain approval for that exact packet. No more diagnostic inference is required to establish the previously observed Fable/Haiku binding.

## Subsequent live authorization and readiness check

Sam subsequently authorized the recommended live panel on both participants, using subscription allowance only and explicitly prohibiting enabling usage credits. That live-panel instruction is recorded; account-wide configuration changes are not implied.

The refreshed local Ollama check passed: server 0.34.2 and Qwen digest `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`, with local blob evidence. The CLI reports client 0.33.0 alongside the server version; both are retained in the identity receipt. A metadata parser defect surfaced before inference: shell parsing applied to multiline template text. The narrow correction parses only FROM directives and refuses malformed FROM quoting. Fifty root focused tests and 52 independently run relevant tests passed. The earlier full-suite receipt remains evidence for its original source snapshot; the new source hashes are in `runs/pilot-live-readiness-20260920T042025Z/readiness-receipt.json`.

The freshly shared Claude page still reported the Usage credits switch and checkbox checked, a USD 50 monthly cap, USD 0 balance and auto-reload off. Those are separate settings. No switch was changed. Live dispatch is waiting for Sam's answer about disabling the switch; zero inference calls have occurred. A refreshed proposal in that readiness directory retains the blocker rather than marking billing verified. Once resolved, refresh time-sensitive evidence and bind the existing live approval to the resulting exact manifest without repeating the same approval question unless scope changes.

## First live attempt

The billing blocker was subsequently resolved and the authorized panel ran to its first-call refusal. See [first live panel attempt](pilot-live-panel-2026-09-19.md) for the consumed-run identity, complete accounting, diagnostic retention finding and next boundary. Earlier zero-call statements describe their offline checkpoints.
