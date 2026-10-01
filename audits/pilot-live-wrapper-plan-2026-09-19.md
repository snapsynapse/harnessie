# Guarded live-wrapper implementation plan

Status: Sam approved this plan as described on September 19 and authorized bounded delegation. Implementation and offline verification are authorized. Model inference remains excluded. Sam selected included subscription allowance only, with no usage credits.

Scope: Harnessie-local pilot integration. Build and verify the missing wrapper, then produce a concrete execution packet for separate live approval. Preserve the existing question, local Qwen requirement, bounded Haiku policy and human-only arbitration.

## Goal and success test

Deliver a pilot-only wrapper that coordinates the four review stages with shared budgets, durable attempt records, verified transport identities and a preserved human halt. Success means the entire path passes offline injected-transport tests and independent review, and a new execution packet identifies the precise disclosure set, limits, source identities and any unresolved live-readiness blockers.

The current question remains: Should Harnessie proceed with a bounded bid-record contract after its named exposure and budget gates, while leaving dispatch selection unchanged?

## Reconciled starting point

- Checkout remains at `aae3daa`, with the existing uncommitted preparation and planning work preserved.
- All 11 implementation/test hashes in the final policy verification receipt match current bytes. The recorded full-suite result is 780 passed, 9 skipped and 28 expected failures; tests were not rerun merely to draft this plan.
- Preparation packet v3 still matches seal `80951137061d32909da74379aa14fe90338a1714cb0dc85159a663c417450b8e`. Both live allowances are zero.
- The Claude adapter, stream parser, fixed Haiku policy and local Qwen identity collector exist. The current `scripts/pilot_runner.py` remains mock-only. The standalone Qwen smoke is not yet a reusable governed panel adapter.
- The existing mock rehearsal proves eight scripted turns, open-record export and the human halt. It does not prove live-wrapper integration, billing entitlement or current provider state.

## Approved scope

One local implementation and verification tranche is approved, including:

- Pilot-only source and regression-test changes, disposable fixtures and a newly sealed preparation/execution proposal.
- Read-only CLI/auth classification, local Ollama/model metadata and billing-status checks through existing authorized surfaces. No inference is allowed in these checks. If billing or model evidence is inaccessible, record the unresolved fact and continue independent offline work.
- Bounded worker delegation with separate file ownership and an independent verifier.
- Repository-local audit, NEXT and relevant handoff updates reflecting actual completion and unfinished work.

Excluded: Claude or Qwen inference, cloud Qwen, model downloads, service/auth/global-setting changes, public provider registration, core schema redesign, bid selection changes, human arbitration, commits, pushes, publication, releases and unrelated cleanup. The live decision panel requires a second approval of its final execution packet.

## Work units and order

| Unit | Work | Done condition | Owner/dependency |
|---|---|---|---|
| A | Define the execution manifest and stage contract. | One schema binds the question, ordered stages, disclosed paths, packet/source hashes, provider identities, policy and limits; absent or mismatched authority allows zero dispatches. | Lead; first. |
| B | Build shared accounting and durable attempt state. | Calls, token usage and additional-model usage span all stages; exclusive run ownership prevents concurrent dispatch; intent is durably written before a call and its receipt before progression. | Worker 1; after A. |
| C | Integrate the reviewed Claude adapter and a bounded local Qwen adapter. | Fixed approved routes, identity checks, explicit policy selection, complete receipt accounting and shared stop-on-failure behavior pass injected transport tests. | Worker 2; after A, parallel with B. |
| D | Wire the four stages through existing runner interfaces. | Claude position, Qwen position, Claude objection and Qwen objection use B/C through the real runner; existing open export and human halt remain intact. | Lead; after B/C. |
| E | Exercise failures and obtain independent verification. | LIVE-01 through LIVE-06 below have passing evidence; relevant offline suites and artifact checks pass with skips/expected failures visible. | Fresh-context verifier; after D. |
| F | Freeze the final execution proposal and report readiness. | Exact files, hashes, call graph, limits, identities, billing evidence, stop rules and output locations are reviewable; all unresolved facts are explicitly listed. | Lead; after E. |

Use `scripts/pilot_*.py` and `tests/test_pilot_*.py` so the existing distribution exclusion remains effective. Candidate modules are an execution wrapper, manifest/ledger module and local Qwen transport; finalize filenames after the interface review. Keep `pilot_runner.py`'s mock-only command usable. If a public runtime change proves necessary, stop that expansion and present the smallest concrete amendment while completing unaffected work.

## Execution and accounting contract

- Stage order is explicit and sequential. Four stages are not necessarily four model calls: evidence reads and neutral tool responses may require multiple calls. Derive proposed per-stage ceilings from the real message flow and packet sizes, then list exact values in the final approval packet. Earlier illustrative limits are not approved defaults.
- One run-level ledger owns budgets. Reconstructing a model or entering a new stage cannot reset them. Reserve an attempt before provider dispatch; failed or uncertain attempts remain consumed.
- Keep uncached input, output, cache creation and cache reads separate, then apply documented aggregate limits. Count all reported Claude identities. Unknown usage blocks progression rather than becoming zero. Report actual subscription dollar cost as unknown unless there is authoritative evidence.
- Persist attempt states such as reserved, dispatched, completed, refused and outcome-unknown with stable IDs and run/source binding. An interrupted or ambiguous dispatch must never be automatically reissued. Recovery is an explicit reconciliation action, not an automatic retry.
- Use exclusive run ownership and durable writes. A stale lock or conflicting process is an unresolved run, not permission to clear state and start again.
- Preserve Claude answer attribution and `claude-max-haiku-overhead/v1`. Haiku stays unclassified and limited to the exact observed ID, first-party metadata, no reported web search, at most 4096 cache-inclusive input and 256 output tokens per invocation. These are post-response acceptance thresholds, not hard pre-inference billing caps.
- Qwen uses only the fixed local endpoint and exact approved digest, with proxy/redirect refusal and no remote fallback. Capture its identity before dispatch and verify it after each request before accepting the result or advancing; retain evidence on drift.
- Harnessie executes only the read/report tools admitted by the frozen workflow. The Claude CLI formatter is treated separately from operational tools. No source edits or arbitration are model actions in this panel.

## Acceptance criteria

| ID | Required proof |
|---|---|
| LIVE-01 | Missing, altered, stale or zero-call execution authority produces zero provider/CLI dispatches. Packet, policy and implementation drift refuse. |
| LIVE-02 | Shared limits survive stage changes, adapter recreation and attempted restart. An overage, missing usage or refused attempt is recorded and cannot trigger another call automatically. |
| LIVE-03 | Claude Fable attribution and the fixed Haiku exception remain enforced. A third model, alternate Haiku identity, remote Qwen route, proxy/redirect attempt or local Qwen identity drift refuses with retained evidence. |
| LIVE-04 | Inject interruption before dispatch, after dispatch and before receipt persistence; a second process and restart cannot duplicate a potentially completed call. Disk-write failure halts progression. |
| LIVE-05 | Injected transports exercise all four stages, agreement and dissent, malformed/truncated responses, timeouts and output limits. Successful fixtures export an open record, preserve source bytes and remain `needs_arbitration` before and after resume. |
| LIVE-06 | A reviewed execution packet states actual proposed limits and disclosures, fresh identity evidence and billing status. Inaccessible billing or identity evidence remains a named blocker or explicit decision for live approval. |

Run focused tests during implementation, the full offline suite after integration and the relevant manifest/docs/distribution checks. Independent review includes an offline replay of the retained real Claude stream. None of these checks makes a new inference request or substitutes for a live participant verdict.

## Deliverables

1. Tested pilot-only wrapper, shared ledger and local Qwen adapter with no live execution during development.
2. Independent verification report mapping evidence to LIVE-01 through LIVE-06.
3. New sealed packet and an execution proposal containing source/CLI/model fingerprints, disclosure inventory, per-stage and aggregate limits, policy selection, billing evidence and exact result/export locations.
4. Updated current-state and handoff records with remaining work clearly distinguished from completed work.

The execution proposal must distinguish a reviewed candidate from actual dispatch authority. Writing or possessing a proposal file must not grant calls.

## Checkpoints and stop conditions

- Approval of this plan authorizes A through F only, under the offline and read-only boundaries above.
- Routine pilot-only implementation choices are delegated to the lead. Additional user questions are limited to missing billing/account evidence or a concrete scope expansion that cannot be resolved within this tranche.
- Stop provider work on identity drift, unexpected route, unusable account evidence or a need for configuration mutation. Continue offline work that does not depend on that state.
- After F, request separate approval for the exact live execution packet. Do not repeat diagnostic smoke calls simply to demonstrate already-retained Fable/Haiku binding.
- Human arbitration and Git/release delivery remain later, separate decisions.

No fixed duration is promised before A's integration review. Scope is one wrapper and its supporting contracts/tests, using at most two implementation workers concurrently and a separate verifier. No satellite-repository changes or public architecture expansion belong to this tranche.
