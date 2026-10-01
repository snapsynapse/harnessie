# Panel-v2 outcome and opaque thinking-block correction

Scope: Sam approved the [panel-v2 attempt](pilot-response-retention-2026-09-19.md) after the offline capture repair. This record distinguishes that consumed live attempt from the subsequent offline compatibility correction. No automatic retry, human arbitration or Git delivery is authorized by either result.

## Live result

Fresh checks confirmed first-party Claude Max authentication, unchanged local Qwen identity and an unchecked Usage credits switch and checkbox. The shared Usage page showed Max (5x), Fable weekly usage at 0%, session usage at 2%, zero credit balance/spend and auto-reload off. No settings were changed.

Manifest and approval: `runs/pilot-panel-v2-readiness-20260920T044915Z/`, execution digest `6584ca074e055823c63184e5516e2623faebf14996010a6c820c1966416d4843`. Run root: `runs/pilot-dispatch-candidate-2026-09-19-v2/`. The question, disclosure, ceilings and policy matched the reviewed proposal.

The attempt stopped after one Claude invocation in the position stage. Qwen was not called. The adapter refused `stream_malformed`, now with the precise diagnostic `invalid_text_block`, event 7. The workflow is incomplete and has no accepted position, decision export or arbitration. The ordinary loop's subsequent error was a latched refusal, not a second provider dispatch.

- Usage retained: 1,752 input, 595 output, 1,690 cache-creation input and 3,706 cache-read input tokens; aggregate 7,743.
- Operator ledger: six valid records, tail `15dbc1b2d3f310d30d3d2f0994b2f6a3f66c6488e1331042214fb9f8816e253e`.
- Runner audit: nine valid events. Complete usage accounting, no provider retry.
- Private response: 11,533 bytes, completed process with exit 0 and no transport failure. SHA-256 `4207a9861665a17093d8d7c16d3b38065d263fbfa558375a9f820899e325e9f7` matches both the durable capture receipt and read-back bytes. Directory/file modes are 0700/0600.
- Actual subscription dollar cost remains unknown. Raw provider list-price equivalents are not billed-dollar evidence.

`forensic-receipt.json` in the readiness directory binds the run/capture hashes, usage and chains. Consumed files remain unchanged. The response-retention mechanism worked as designed.

## Evidence-based diagnosis

Event 7 is an assistant `thinking` content block. Its fields are exactly `type`, `thinking` and `signature`; the thinking string is empty and the signature is an opaque nonempty string. It shares the model, message, request and session identity used by the later text and StructuredOutput blocks. The old parser admitted only text and StructuredOutput content, so it rejected this otherwise linked stream. No reasoning text or signature content is copied into this record.

The subsequent pilot-only correction admits exactly that block shape as non-answer, non-tool metadata. It requires a string thinking field and a nonempty string signature, rejects extra/malformed fields, and keeps the existing parent/session/model/message/request and terminal-output bindings. The signature is not interpreted or cryptographically authenticated. Unknown content types remain refused. A thinking block alone cannot produce an accepted structured answer.

This contract checks types and fields, not the particular observed text value or signature length. Neither opaque value contributes to the accepted answer. A synthetic regression verifies that nonempty metadata, even text describing an unoffered tool, cannot become an operational request. Pinning one signature length would overfit an uninterpreted value without proving authenticity.

Only `scripts/pilot_stream.py` and its synthetic regression tests changed for this correction. The raw captured response remains private and was not added as a portable fixture. Offline replay through the complete adapter now binds Fable, passes the existing Haiku policy, retains identical usage and yields a `read_file` request. No tool was executed by the replay and no provider was called. This is parser/adapter compatibility evidence, not a completed live position or retroactive acceptance of the failed run.

## Verification and next boundary

The final full offline suite passed 879 tests, with 9 skipped and 28 expected failures. The focused root parser/transport/capture-integration suite passed 57 tests. The live call count for panel-v2 is one Claude and zero Qwen; all subsequent corrective work is offline. Independent review and final source bindings are in `runs/pilot-thinking-block-repair-2026-09-19/verification.json`.

The next proposal is `runs/pilot-thinking-block-repair-2026-09-19/execution-proposal.json`, digest `780b45e0a6db333822c9eccf814e3e566d0db25fa68e522d30ef56f54df2c4bd`, using fresh candidate `runs/pilot-dispatch-candidate-2026-09-19-v3/` and run `pilot-2026-09-19-panel-v3`. The input seal is unchanged: `626322d26c8bca5dd1afaf351612336eaa038aef504b106ad80f445dcfece742`, 26 files, 200,991 bytes. Disclosure, question, call graph, limits, capture contract and Haiku policy match panel-v2. Only the reviewed parser source identity changes. The proposal grants zero live calls and has no approval file; historical readiness fields explicitly require refresh.

Proposed next execution: obtain a new decision for panel-v3, refresh read-only credits-off and both provider identities, bind that evidence and approval, then run the same four stages. Maximum eight Claude and eight local Qwen calls, four per stage, 400,000 aggregate reported tokens and the unchanged process/Haiku limits. Stop on the first refusal or unknown outcome; preserve its evidence without retry. If all stages complete, verify chains and export the open record for Sam's arbitration. Keep credits off and preserve both consumed attempts. Offline replay success does not guarantee the next stage or full panel will complete.

## Subsequent panel-v3 result

Sam approved panel-v3. It passed stream validation and completed two evidence-read exchanges, then stopped at the Haiku bound on call three. See [panel-v3 budget-fit record](pilot-panel-v3-budget-fit-2026-09-19.md) for the current outcome and proposed offline sizing scope.
