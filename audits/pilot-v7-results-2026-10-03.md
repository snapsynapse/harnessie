# Pilot v7 live result

Date: 2026-10-03 (America/Denver)
Execution checkout: 616c44e; sealed source snapshot: bd52a30
Approved proposal: f7de489f9e570ee0e3fddffbbef060f70b8605f08fa653d8f0f97107fb487d48
Status: consumed, incomplete; no retry or further live authority

## Outcome

Sam approved the exact ready proposal. One live invocation made four Claude calls and one local Qwen call. Claude's first position was accepted with stance recommend. Qwen returned a structurally valid response with unchanged before/after identity, but the enclosing guard refused acceptance after the approval and preflight window expired. No Qwen position, objection exchange, open AIDR export or human arbitration was completed.

This differs from v6: all four Claude responses passed the unchanged identity admission and aggregate output cap. Their reported output counts were 389, 1,069, 803 and 3,212, each below 4,096. The reviewer read the index, nine sources, then eight sources before task_complete. This is evidence of one successful first-stage execution, not a completed panel or general reliability claim.

## Timing and refusal

The retained event timestamps establish this UTC sequence:

- 03:08:44.084: Claude stage started.
- 03:10:01.931: Claude position recorded and Qwen stage started.
- 03:10:34.996: the approval expiry and earliest preflight freshness deadline.
- 03:11:26.917: Qwen response returned to the runner as a guard error, approximately 84.99 seconds after its stage started.

The Qwen transport receipt reports completed, failure null, 1,184 input tokens and 350 output tokens. Its identity fingerprints match. The enclosing ledger records accepted false and receipt_refused; the overall outcome is stage_failed. The guard revalidates authority after receiving a response. Its validator checks approval expiry before billing freshness, so live_authority_expired is the first applicable authority failure at this return time. This cause is reconstructed from the sealed approval, timestamps and unchanged validator: the guard does not persist the specific post-response authority exception. Expiry is sufficient to reject this response, but the raw Qwen envelope and stop reason are not retained, so it is not proven to be the only failed acceptance condition. It must not be presented as a provider failure or a recorded timeout.

The runner emitted a second error turn, but no second Qwen dispatch or receipt exists. The approval and candidate are consumed. No retry, replacement route, model change or service mutation occurred.

The operator started with only about 111 seconds left before expiry. Valid-at-start was insufficient runway for this panel. A future proposal should be freshly observed immediately before the approval/execution handoff, and its remaining runway should be reviewed against the staged workload before dispatch. Any change to freshness semantics or treatment of in-flight responses requires a separate offline design and test review; this run does not authorize weakening the guard or extending limits.

## Accounting and retained evidence

- Reported input: 1,192 tokens.
- Reported output: 5,823 tokens.
- Cache-creation input: 148,856 tokens.
- Cache-read input: 7,272 tokens.
- Total including cache: 163,143 tokens, of which Claude accounts for 161,609 and Qwen for 1,534.
- No Haiku usage was reported. Accounting is complete; actual subscription dollar charge remains unknown.
- Outcome integrity reports: 22 valid ledger records, five admitted request-metrics records, and a valid 36-event runner chain.

Private evidence remains under runs/pilot-candidate-v7-2026-10-03/: the exact ready proposal, approval, observations, packet/runs/pilot-panel-v7-2026-10-03/outcome.json, operator ledger and four private Claude captures. The initial unapproved proposal remains distinct. Preserve all consumed evidence unchanged; raw thinking and signatures are not publication material.

An independent read-only verifier reproduced all four Claude admissions from retained captures, checked capture hashes and per-call output counts, and matched each of the 17 source reads against unique prefixes and full byte lengths. Ledger, request-metrics and runner validators passed. The verifier confirmed five dispatches and five receipts, the timing/expiry inference, complete accounting and the absence of objections, export and arbitration. Verification passed for these retained facts, not for completion of the panel.

## Next boundary

Do not rerun v7 or infer human agreement from the single recorded recommend stance. First review the freshness/runway admission and retained diagnostic gap offline. A later live panel requires a fresh candidate, current preflight evidence and separate explicit approval. Completion still requires both positions, both objection stages, an open-record export and Sam's arbitration. Dispatch selection and product implementation remain unchanged.
