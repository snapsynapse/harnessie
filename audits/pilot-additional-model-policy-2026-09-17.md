# Pilot additional-model policy and architecture lessons

Scope: Harnessie-local pilot policy. Sam delegated judgment after reviewing the Haiku risks and asked that unexpected behavior strengthen the architecture. The decision is to permit the exact observed Haiku identity under a bounded, explicit policy while retaining Fable answer attribution and all existing containment checks. This grants no new live inference allowance or release authority.

## Decision

Policy `claude-max-haiku-overhead/v1` may permit `claude-haiku-4-5-20251001` as additional, unclassified CLI usage. It does not establish the model's internal purpose, inputs or lack of influence. The requested and verified answer model remains `claude-fable-5-1`. The default adapter policy remains `exact-model-only/v1`; future callers must select the exception explicitly and record it.

The exception requires:

- Successful stream binding and structured-response validation for the Fable answer.
- No additional identity except the exact observed Haiku ID. Aliases and other versions refuse.
- First-party provider metadata for both reported identities, in addition to the existing Max authentication check.
- Complete per-model usage, including cache creation/read counts. Additional-model reported web-search requests must be zero.
- Haiku input consumption, including uncached, cache-creation and cache-read input, at most 4096 tokens per CLI invocation; Haiku output at most 256 tokens per invocation.
- Full usage preservation and a latched refusal on any breach. Subsequent calls cannot silently retry or increase the limit.

These thresholds are conservative operator-selected starting values, above the observed 989 input and 16 output tokens. They are acceptance thresholds measured after usage is reported, not a hard provider spend limit. They may halt a larger real packet. Any adjustment must be recorded rather than inferred from failure. Session-wide call and token ceilings remain part of the separate live-run plan.

Operational native tools remain disabled, with only the CLI's schema-output formatter admitted. All content disclosed to Claude must be suitable for processing by either permitted Anthropic model. Qwen and local-only material remain on the approved local route. The record names the participant as Fable through Claude Code with permitted additional Haiku usage, not a model-exclusive Fable experiment or a third independent reviewer.

## Architectural findings

| Finding | Operator impact | Bounded correction |
|---|---|---|
| An SDK or CLI invocation can use more models than the requested answer model. | A single model field either rejects legitimate behavior or hides additional processing. | Separate requested model, verified answer attribution, observed usage identities and versioned acceptance policy. |
| Usage can arrive even when output is refused or malformed. | Treating failure as zero understates resource consumption. | Capture accounting before acceptance checks; preserve raw records and unknown totals through refusal. |
| A formatting tool appears despite an empty operational tool selection. | An overbroad "no tools" claim misstates the actual boundary. | Distinguish schema formatting from operational tool execution and validate the specific formatter exchange. |
| Unexplained usage triggered repeated diagnostic approvals. | Operators cannot easily tell a policy mismatch from an execution failure. | Report capture completion, answer attribution, policy disposition, resource consumption and final workflow acceptance separately. |
| Mutable transport behavior can outlive a successful fixture. | Old test results can be mistaken for current integration proof. | Bind policy and implementation identities to each execution packet; replay saved evidence offline and require fresh identity checks before live dispatch. |

The reusable contract is evidence first, deterministic policy second. A policy exception must never manufacture missing evidence. This pilot supplies a tested example; extending public provider interfaces, run journals or billing enforcement requires a separate scoped design informed by pilot outcomes.

## Acceptance and regressions

The retained stream must fail under the default policy and pass under the explicit exception with identical answer and usage evidence. Fable substitution, a third model, a different Haiku identity, provider mismatch, missing counts, cache-inclusive threshold breaches, malformed linkage and additional operational tools must still refuse. The policy alone must never authorize a model call. Every receipt must name the evaluated policy and preserve its limits and disposition.

Implemented in `scripts/pilot_policy.py`, integrated into the pilot adapter and serialized by `scripts/pilot_prepare.py`. Policy configuration is frozen and limited to the two named policies; subclasses cannot substitute a permissive evaluator at construction.

- Full offline suite: 780 passed, 9 skipped, 28 expected failures.
- Independent policy/transport/stream/preparation verification: 38 passed, plus exact retained-capture replay.
- Actual retained `005` bytes refuse under the strict default and return `PILOT_SMOKE_OK` under the explicit exception. Both outcomes preserve identical Fable attribution, normalized totals and raw model usage. No model was called during replay.
- Public manifests, generated-document parity and whitespace checks passed. No public provider schema or registry was changed.

The new zero-allowance preparation packet is `runs/pilot-preparation-2026-09-17-v3/`, containing 26 files and 200,988 bytes. Its seal is `80951137061d32909da74379aa14fe90338a1714cb0dc85159a663c417450b8e`. The selected policy is bound in both the manifest and provider plan. Eight scripted calls exercised the real runner and exporter; the 46-event audit chain and pinned reference lint passed. The human halt remained `needs_arbitration` before and after resume, with zero resume calls.

`runs/pilot-policy-2026-09-17/retained-replay.json` records the two offline policy outcomes. `runs/pilot-policy-2026-09-17/verification.json` binds the final implementation and test hashes to the packet seal. The earlier `v3-receipt.json` source snapshot predates the constructor fix and remains historical; the policy verification receipt supplies the final source binding. Neither is a complete CLI/environment fingerprint or permission to dispatch.

No new Claude or Qwen calls, provider settings changes, commits, pushes or releases occurred. At this policy checkpoint, the live-wrapper work below remained unimplemented. It was subsequently completed and independently verified offline; see [September 19 wrapper evidence](pilot-live-wrapper-2026-09-19.md).

## Next executable tranche

1. Completed: freeze the explicit policy in a new zero-live-allowance preparation packet and replay the workflow with scripted models. Retain policy, source hashes and packet seal as operator evidence.
2. Build and verify the bounded live-run wrapper offline. The current `pilot_runner.py` is deliberately mock-only; it is not a live launcher. The wrapper must share call/token accounting across the four stages, persist receipts before progressing, stop on failure, bind before/after local Qwen identity, and preserve the human-arbitration halt.
3. Present one reviewed live execution packet: exact disclosure set, per-stage call graph, token/process ceilings, CLI and model identities, billing-route evidence, stop/resume rules and export path. Verify whether the existing account's Fable requests consume included allowance or usage credits; Max authentication alone does not settle that question.
4. Run only after that live packet is approved. No more diagnostic inference is needed merely to re-establish the observed Fable/Haiku binding.

The offline live-wrapper integration is now complete; the [September 19 record](pilot-live-wrapper-2026-09-19.md) owns current readiness blockers and verification. Policy acceptance and offline verification do not authorize the final panel.

The next task packet has these acceptance criteria:

| ID | Required behavior and proof |
|---|---|
| LIVE-01 | No dispatch without an explicit execution manifest whose seal, participant identities, policy ID, disclosure paths and nonzero allowances match. Default and malformed authority make zero child/provider calls in tests. |
| LIVE-02 | One shared ledger spans position and objection stages, including refused attempts and reported additional-model usage. Stage-local model recreation cannot reset the budget. Unknown usage stops progression. |
| LIVE-03 | Claude uses the reviewed pilot adapter; Qwen has only the fixed local route with proxy/redirect refusal and before/after identity checks. Both providers have a stop-on-failure latch outside the ordinary agent retry loop. |
| LIVE-04 | Persist attempt intent before dispatch and the available receipt before advancing. Restart after an uncertain outcome requires reconciliation; it never automatically repeats the call. Retain hash-bound operator receipts alongside the runner journal. |
| LIVE-05 | Offline injected transports exercise all four stages, dissent, unexpected model, usage overage, Qwen drift, truncated output and interruption. Valid fixtures export an open record, preserve source bytes and remain halted before and after resume. |
| LIVE-06 | Before live approval, show the exact packet and all ceilings, including cumulative additional-model consumption and the unresolved subscription/usage-credit billing route. Source hashes and CLI/model fingerprints must be refreshed after implementation. |

Implementation order: review the runner's existing model injection and adversarial stage interfaces, add the smallest pilot-only wrapper and persistent ledger, test with injected transports, perform independent review, then freeze the final live manifest. Do not change public model schemas, arbitration semantics or bid dispatch selection. None of these offline tests supplies a live participant opinion.

## Subsequent v2 full-evidence policy

On 2026-10-01 Sam approved a separately versioned offline candidate after the full-evidence workload exceeded the conservative v1 run ceiling. The [Claude Haiku context policy](pilot-haiku-context-policy-2026-10-01.md) records `claude-max-haiku-context/v2`, its exact per-invocation and run-wide thresholds, its synthetic full-workload rehearsal and its remaining authority gates. This does not revise the historical v1 values or turn either policy into live authority.
