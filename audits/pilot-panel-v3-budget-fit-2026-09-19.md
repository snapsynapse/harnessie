# Panel-v3 outcome and workload budget fit

Scope: Sam approved panel-v3 under the unchanged ceilings. This record owns the consumed attempt, its offline diagnosis and the proposed next scope. No retry or larger allowance is authorized by the result.

## Authority and readiness

Claude Max authentication and the local Qwen fingerprint were freshly verified, with unchanged reviewed source/test hashes. The Comet connection reported a closed page. Sam explicitly confirmed that usage credits were off and directed proceeding without another browser check. The manifest records that current operator attestation plus the prior directly observed included Fable allowance, not a fabricated new UI snapshot. No account setting changed.

Manifest/approval: `runs/pilot-panel-v3-readiness-20260920T045946Z/`, digest `4b1a91f18e9ec9f3eb731b5a6dfc161630e19f06a22dcd5178ce28a28916be9c`. Run: `runs/pilot-dispatch-candidate-2026-09-19-v3/runs/pilot-2026-09-19-panel-v3/` and its workflow sibling. The fresh approval did not change the disclosure, tools, stage order, limits or policy.

## Observed result

Panel-v3 is incomplete. Claude made three invocations in its position stage; Qwen made zero. The first two responses passed stream and policy validation and caused evidence reads. The third stream parsed and bound correctly but failed `additional_model_usage_bound_exceeded`. Its requested additional reads were not executed. The run halted before an accepted position, decision export or human arbitration. There was no provider retry.

| Attempt | Haiku input including cache | Haiku output | Disposition |
|---|---:|---:|---|
| 1 | 1,750 | 18 | Accepted |
| 2 | 3,372 | 18 | Accepted |
| 3 | 33,729 | 18 | Refused: per-call bound exceeded |

The third call exceeded the 4,096-input per-call bound by 29,633. Run-wide Haiku input reached 38,851, exceeding 32,768 by 6,083, and the ledger halted `haiku_input_budget_exceeded`. These are post-response acceptance/stop thresholds, not provider-side hard spend caps. The refused response still consumed resources and its usage is included.

All-model reported totals: 38,857 input, 2,578 output, 50,840 cache-creation input and 11,118 cache-read input tokens, or 103,393 in aggregate. Actual subscription dollars remain unknown. All three raw stdout captures are retained and hash-verified with private 0700/0600 permissions. The operator ledger has 13 valid records, tail `326b8eb272077c664f1cae1bdb2b7e34873265d01f4308b21f54b2e72bf012eb`; the runner chain has 19 valid events. Independent forensic review confirmed no fourth provider call, no Qwen call and no post-refusal tool dispatch.

The parser correction and capture mechanism worked. The live failure is now a demonstrated mismatch between the evidence-reading workload and the approved additional-model allowance. Haiku's internal purpose remains unknown; the observation does not make it an independent panel participant or prove a particular provider-internal role.

## Offline reconstruction

`runs/pilot-panel-v3-analysis-2026-09-19/request-sizing.json` records a zero-network replay through the same runner, frozen packet and three captured responses. It preserves only reconstructed request hashes, byte lengths and per-message lengths. Original outgoing request bytes were not captured, so these are reconstructed measurements rather than direct wire observations.

| Call | Reconstructed neutral request bytes | Context added before it |
|---|---:|---|
| 1 | 3,498 | System/task and tool schema |
| 2 | 7,136 | 2,974-byte evidence index and framing |
| 3 | 113,699 | Seven full-file results totaling 101,964 bytes, plus framing |

Cumulative reconstructed evidence content before call 3 is 104,938 bytes. This explains the request growth; it is not unexplained prompt inflation. The regular event log keeps only 300-character tool-result previews, which must never be mistaken for full delivered evidence when sizing the workload.

The full frozen evidence corpus is 193,658 bytes. That raw size alone does not prove the 256,000-byte serialized request ceiling or four-call stage budget will fit: JSON framing, role/task prompts, all prior turns, tool responses, objection context and provider-specific encoding must also be counted. Haiku tokenization/internal overhead cannot be derived exactly from byte lengths. The fourth request and later stages were not dispatched and have no live usage evidence.

## Recommended next scope: offline workload sizing

Pause live attempts until the whole review fits an explicit contract. Do not solve this by treating one observed large call as automatic authority to raise the caps.

1. Add pilot-only pre-dispatch request metrics: exact serialized bytes, SHA-256, per-message/tool-result lengths and stage identity. Persist them without copying prompt contents into public logs. A request that exceeds the sealed input/evidence ceiling must refuse before inference. Include both the Claude neutral request and Qwen's outer wire encoding.
2. Rehearse the complete four-stage evidence path offline, including cumulative history and the objection context. Use the actual frozen evidence and recorded tool selections as one scenario; add a declared worst-case read set. Retain synthetic outcomes as sizing evidence only. Determine whether four calls per stage and the 256,000-byte process envelope fit before further inference.
3. Propose an explicit evidence-admission contract and a justified per-call/run token budget. Choose a meaningful evidence subset or excerpts only with provenance and a visible statement of excluded evidence; do not silently truncate relevant material to pass a smoke-sized allowance. If useful review cannot fit the current Haiku bounds, present a separately approved policy revision for context-sized ancillary usage while its role remains unclassified. Keep all-model accounting and subscription-only/no-credit routing.
4. Independently test admission refusal, accumulating history, byte/token headroom, capture/disk failures, unknown usage and stop/no-retry behavior. Produce one coherent next execution packet after those checks. Any new policy, disclosure or ceiling must be visible in that decision; no panel-v4 authority is inferred now.

Done for that proposed offline tranche: a measured four-stage request envelope, tested pre-dispatch admission metrics, a reviewable evidence/budget choice and an exact next-run packet. No live calls, account/service/model changes, public provider/schema changes, human arbitration or Git delivery are part of it. Billing evidence should retain its true provenance; Sam's current explicit confirmation was sufficient for panel-v3, so another identical browser check is not inherently required.

## Offline sizing result, 2026-10-01

The approved offline tranche is implemented and measured in [the full-workload sizing audit](pilot-workload-sizing-2026-10-01.md). All 16 synthetic requests across the four stages fit the 256,000-byte encoded-input and evidence ceilings. The worst encoded request is 219,150 bytes and the complete declared evidence contributes 196,632 tool-result bytes.

This does not resolve the token policy. Panel-v3 already exceeded the 32,768 run-wide Haiku input ceiling on a smaller partial-evidence request, and exact provider token use cannot be inferred from byte counts. Live allowance remains zero. The recommended next decision is a provenance-retaining curated evidence contract with a proposed 64,000-byte evidence ceiling, followed by another offline rehearsal. No evidence reduction, larger cap or panel-v4 is authorized by this result.
