# Controlled-review pilot full-workload sizing

Date: 2026-10-01
Scope: approved offline implementation, measurement and verification only
Status: byte envelope measured; the approved v2 offline token policy is implemented and rehearsed; no live execution authorized

## Starting state and authority

Sam confirmed that no other session owned the Harnessie checkout and authorized the recommended offline workload-sizing tranche with agent fan-out. The checkout fast-forwarded from `aae3daa6e46858f1bc8dd39061d9973a2d73126a` to `4be8438268a4b97dc8a0dbb4ddfd2435e3c9343c`; the ten upstream commits changed only GitHub workflow dependency pins. Existing local pilot work was preserved.

Every consumed panel-v3 file still matches `runs/pilot-panel-v3-analysis-2026-09-19/verification.json`. The earlier failed hash command used `path` as a zsh variable and shadowed the executable search path; its printed `DRIFT` lines were invalid diagnostics. The corrected check found all nine listed artifacts unchanged.

This tranche made no model call, account change, model or service change, live execution, human arbitration, commit, push, release or deployment.

## Implemented admission and measurement contract

The pilot-only transports now prepare immutable request bytes before dispatch. One append-only, hash-chained request journal persists the following non-content metadata before any allowance reservation, identity lookup, authentication or inference:

- exact encoded request byte count and SHA-256;
- stage, participant, transport and encoding identity;
- per-message serialized and UTF-8 content lengths;
- explicit tool-result lengths;
- tool-schema size;
- Qwen inner neutral-prompt size and outer-encoding overhead;
- input and evidence ceilings, headroom and admission result.

The journal stores no prompt text, tool-result text, paths or tool-call identifiers. Exact request bytes measured are the same immutable bytes passed to the transport. Input or evidence overflow and journal failure refuse before inference and latch against retry. The two independent candidate ceilings are 256,000 encoded input bytes and 256,000 cumulative tool-result bytes. These retain the earlier process envelope and add a visible evidence-admission rule; they do not infer tokens from bytes.

The source stays pilot-only under `scripts/pilot_*.py` and `tests/test_pilot_*.py`, excluded from distributions by `MANIFEST.in`.

## Full four-stage rehearsal

The offline rehearsal used the real Claude neutral encoder and Qwen outer OpenAI-compatible encoder with deterministic injected responses and network calls patched to refuse. Each of the four stages made four synthetic transport turns:

1. read the evidence index;
2. read the seven files selected by panel-v3;
3. read the remaining ten declared evidence files as the worst case;
4. return a labeled synthetic position or objection.

This exercises cumulative history, all tool results and objection-stage context. Synthetic responses establish encoding and admission behavior only, not review quality.

| Stage | Requests | Maximum evidence bytes | Maximum encoded request bytes | Minimum input headroom |
|---|---:|---:|---:|---:|
| Claude position | 4 | 196,632 | 209,397 | 46,603 |
| Qwen position | 4 | 196,632 | 218,890 | 37,110 |
| Claude objection | 4 | 196,632 | 209,635 | 46,365 |
| Qwen objection | 4 | 196,632 | 219,150 | 36,850 |

All 16 requests fit both byte ceilings. The request-metrics journal has 16 valid records, all admitted, tail `394e6899a45a7e968593684553155153a241ead2a07eea7a917a36109953ea6d`. The run halted at the required human-arbitration boundary. The compact report is retained at `runs/pilot-workload-sizing-2026-10-01/runs/pilot-offline-workload-sizing-2026-10-01/operator/workload-sizing.json`; its canonical parsed-JSON SHA-256 is `b5081b259e55537f686223c367364745e87b64d9da6d04896a66609e9446b74f`.

## Token and budget conclusion

The byte envelope fits, but the current live token policy does not fit the demonstrated workload. Panel-v3 reported 33,729 Haiku input tokens on a 113,699-byte neutral request, already exceeding the approved 32,768 run-wide Haiku input ceiling before a position, Qwen turn or objection existed. The complete rehearsal reaches 209,635 Claude bytes and 219,150 Qwen bytes. Exact provider token use cannot be extrapolated from those byte counts, so this audit does not invent a larger token ceiling.

The final live allowance remains zero for both participants. Panel-v4 is not authorized.

## Recommended evidence decision

Lower scope before changing the ancillary-model ceiling. The recommended next packet is a provenance-retaining curated evidence contract with:

- an explicit 64,000-byte cumulative tool-result ceiling per stage;
- mandatory coverage of the current capability direction, the arbitrated AIDR-0009 decision, current capability-readiness findings, the routing seam and bid-record falsifiers;
- section- or symbol-level excerpts with source path, whole-source SHA-256, excerpt SHA-256 and excluded-section inventory;
- visible refusal when mandatory material or provenance cannot fit;
- another zero-network four-stage rehearsal before any live proposal;
- unchanged participant, subscription-only, no-credit, no-retry and human-arbitration requirements.

The 64,000-byte ceiling is a proposed scope boundary, not proof of token fit. It is deliberately below the 104,938 evidence bytes present before the failed panel-v3 call. Sam must approve the meaningful evidence reduction before excerpts are created. If the curated packet still cannot support a useful review under the existing Haiku policy, return with evidence rather than raising the ceiling automatically.

## Subsequent operator direction and result

Sam chose not to reduce the evidence to satisfy the conservative Haiku threshold. He subsequently approved the exact offline candidate ceilings recorded in the [Claude Haiku context policy](pilot-haiku-context-policy-2026-10-01.md). The implementation retains the complete evidence and the 256,000-byte pre-dispatch input and evidence ceilings. The offline rehearsal admitted all 16 requests and exercised a clearly labeled synthetic Haiku profile totaling 207,702 input tokens under the 256,000-token run ceiling. No live model was contacted, and synthetic usage is not provider evidence.

The [authentication-contract repair](pilot-claude-auth-contract-2026-10-01.md) distinguishes first-party stored OAuth from separate Max billing evidence. The earlier 64,000-byte curation proposal is not the active next tranche. The approved numerical thresholds remain zero-authority configuration until a separately reviewed and approved live packet binds fresh included-allowance and credits-off evidence.

## Verification and remaining gates

Focused adapter, admission, integration and workload tests cover exact-byte reuse, Unicode and escaping, per-message and tool-result measurement, exact-limit acceptance, one-byte and one-token overflow, cumulative history, content non-retention, identity and transport non-invocation on refusal, and four-stage completion. The pilot suite passed 197 tests before the final call-limit regression, and the final focused policy, transport, ledger, live and workload suite passed 73 tests. The full offline suite passed 908 tests with 9 skips and 28 expected failures; the deterministic eval passed 66 of 66 scenarios; and the isolated package and fresh-install gate passed. Independent read-only review passed after identifying and correcting the legacy call-limit validator. The delivery commit supplies the final source and test object identity.

Separate later decisions remain required for a final zero-authority execution proposal, participant and billing freshness, live execution, human arbitration, push, release and private-run cleanup.
