# Ringer, Ringside and Harnessie interoperability assessment

Date: 2026-09-17
Scope: Harnessie's adoption and integration design. Recommendations are not an implementation approval, upstream contribution or new product decision.

## Verified snapshot

- Ringer upstream `main`: `0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591`, committed September 15, 2026. Public Git refs, GitHub repository metadata, releases, recent commits and all 63 open PR summaries were retrieved on September 17. Selected relevant PR descriptions and changed-file lists were inspected; open-PR behavior was not independently tested.
- Upstream source was read in a fresh temporary clone. Existing local Ringer checkouts were left untouched; their tips were from July 16 and July 10 and were not used as current evidence.
- The tests workflow on the exact upstream main commit reports success. This is upstream CI evidence, not a local full-suite run or live-provider acceptance.
- The current GitHub release is Ringside `v0.1.1`, published July 3. The current README calls the Tauri build a prototype and recommends the more advanced web dashboard. Do not use the desktop release tag as the version of today's main source.
- Harnessie local and remote `main` both resolve to `aae3daa6e46858f1bc8dd39061d9973a2d73126a`. Core 1.4.1 release evidence remains in the repository. The September 17 acceptance/adoption documents are local uncommitted proposals, not shipped behavior.
- One local synthetic subprocess probe exercised Ringer's actual `Verifier` with commands returning 0, 1 and 2. Results were PASS, FAIL and FAIL. The timeout constant is 60 seconds. There were no model calls, workers, self-update or dashboard launches. This proves the exit mapping only, not an end-to-end Harnessie integration. The [machine-readable receipt](ringer-ringside-exit-contract-2026-09-17.json) records the result.

Source links below are pinned to the inspected upstream commit unless explicitly identified as open PRs.

## Recommendation

Preserve the complementary direction: Ringer dispatches engine workers and records attempts; Ringside presents activity and deliverables; Harnessie can supply an independently executable acceptance check with claim-bound evidence and, when chosen as the execution runtime, stronger in-run policy enforcement. Start with process and artifact interoperability rather than shared internals or another orchestration/UI layer.

Complementarity requires explicit ownership of lifecycle and authority. A Ringer worker reviewed by Harnessie is still a Ringer worker: Harnessie's verification subprocess does not retroactively confine it. Neither an independent model verdict nor Ringside's pass label is a human approval to merge, publish or arbitrate.

## Current overlaps and boundaries

| Dimension | Ringer and Ringside on current main | Harnessie current or proposed scope | Recommendation |
|---|---|---|---|
| Dispatch and parallel execution | Pluggable CLI engines, per-task directories/worktrees, timeouts and retries. | Governed sequential/parallel phases, ownership lanes, role restrictions and verified retry/escalation. | Different emphasis with substantial overlap. Let the chosen outer runtime own dispatch; do not require a nested Harnessie worker loop for a verification check. |
| Executable acceptance | A shell check and expected files determine the outcome. Baseline mode runs checks before worker spend; lint identifies several weak-check patterns. | Deterministic checks plus optional model verification; standalone evidence bundles enforce expected claim coverage. Proposed AC strengthens pre-execution contracts. | Reuse the check seam. Define criterion identity and artifact binding beyond exit status. |
| Review panels | Review and adversarial-review kits collect structured findings for orchestrator confirmation. | Fresh-context verifier, contested phases, preserved dissent and operator-side arbitration records. | Distinguish a report-shape check, substantive claim verification, and human decision. Do not infer model independence from different engine labels. |
| User interface | Ringside renders live runs, delivered files, declared check meaning, check output, dead runs, historical artifacts and model scores. | CLI reports, offline observer, proposed first-use review receipt; no product web UI in scope. | Acknowledge Ringside's lead. Make Harnessie evidence consumable there; avoid a duplicate mission-control dashboard. |
| Model identity | Separates trained model, lab, harness, access plan and reasoning effort, with declared/reported identity handling. | Existing bundle identity captures model, adapter, endpoint, prompts, parser and sampling; VI proposes clearer identity and diversity semantics. | Align fields through an explicit mapping. Ringer identity is useful provenance, not authenticated model-family proof. |
| Evaluation | Attempt log, task-type scores, catalog exploration, known-good/bad bakeoff fixtures and human repair-time fields. | Deterministic evals, opt-in provider scorecards and proposed calibrated bid/reviewer comparisons. | Extend existing evidence with claim-level correctness, contract hashes, exposure and uncertainty. Do not build a duplicate catalog or scoreboard. |
| Enforcement | Worker confinement belongs to attached engines/operator policy; selected engine configurations include sandboxes. | Registry, ownership, sandbox and consent controls within Harnessie-managed execution. | This is the clearest complementary boundary. State its scope precisely; a verifier call cannot confer all harness controls on external workers. |
| Resource controls | Main has worker timers, concurrency and observed token fields; broader cost ceilings are proposed in open PR #129. | Token/dollar accounting and run ceilings; verifier reservation and total integration accounting remain design work. | Budget production and verification separately. Neither process can claim the other's usage without a receipt. |
| Decision records | No AIDR runtime/import/arbitration implementation was found on main. The decision-template proposal is open. | Contested run records and offline open-record AIDR export are shipped. | Retain Harnessie's distinct decision lifecycle. Any external-position importer is a separate provenance-preserving proposal. |

Sources: [Ringer runner and verifier](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/ringer.py), [template catalog](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/templates/README.md), [identity taxonomy](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/docs/TAXONOMY.md), [bakeoff kit](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/templates/bakeoff-kit/README.md), [upstream contribution boundary](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/CONTRIBUTING.md).

## Concrete interoperability gaps

### Exit codes and retry ownership

Harnessie distinguishes verified, failed and cannot-verify through 0/1/2. Ringer's `Verifier.verify` retains the raw check return code but treats every nonzero exit as a failed check. `verdict_for` maps that to FAIL unless there is a worker error or timeout. `_run_task` retries FAIL and TIMEOUT when attempts remain.

The integration therefore fails closed on exit 2, but can rerun the producer for missing credentials, unavailable evidence, an unsuitable verifier or another verification infrastructure problem. It can also count that outcome against the worker model. Preserve the distinct verification reason in the durable report, and specify that producer retries respond to demonstrated work defects. Verification retries need a separate owner and bounded allowance.

The smallest interim recipe can set the outer task to one attempt and use an explicit later rerun. Do not disguise cannot-verify as exit 0. A richer status mapping requires an agreed upstream seam or an outer adapter; it is not present in current main.

### Check duration

Ringer's check subprocess has a fixed 60-second timeout independent of the worker's `timeout_s`. A model-backed verification may legitimately exceed it. Changing the worker timeout does not change the check timeout. [PR #133](https://github.com/NateBJones-Projects/ringer/pull/133) proposes separate check budgets; #74 and #91 are related open proposals.

Before recommending the inline check as the general live-model route, establish a supported check-timeout setting and prove cancellation reaches the verification process tree. A separately invoked post-run verifier is a possible trial path, but then Ringer's producer PASS must remain distinct from Harnessie's acceptance verdict. A synthetic sub-second check does not close this gap.

### Receipt survival and presentation

Passing worktrees can be deleted, and failed checks expose only abbreviated output. Write verification reports and proofs to unique per-run, per-task, per-attempt paths outside disposable worktrees. Preserve failure and cannot-verify reports too, not only passed deliverables. A full receipt must survive retry, timeout and cleanup.

Ringside's `verified` text is supplied by the manifest author; it is not derived proof of all acceptance claims. Its current task card can display a check description and output, but a native three-state Harnessie review card is not implemented. Start with truthful summary text and a persistent report artifact, then evaluate a UI extension with the upstream maintainer if useful. Every displayed receipt must identify the exact artifact and criteria it covers.

### Shared identity and calibration

Map Ringer model/lab/harness/access-plan/effort and actual versus expected model onto Harnessie's bundle identity, with provenance and unknown values preserved. Include effective worker spec and steering-profile version where those affect a trial. Distinct adapters are not necessarily different families; the same family can be reached through multiple providers.

Ringer currently uses three tasks and a first-try success threshold of two thirds for its `proven` exploration label. That is a useful local routing heuristic, not evidence for Harnessie's stronger calibration or independence claims. Preserve raw attempts, check definitions, contract changes, incomplete outcomes and review costs when importing metrics. Do not convert a format-check PASS into substantive claim correctness.

### Exposure and enforcement

Ringer deliberately delegates worker containment to the chosen engine and operator. Its check launcher executes a shell command; Harnessie's sandbox applies to checks Harnessie itself launches, not to every outer command or worker. The separately released Harnessie engine wrappers currently prove only their documented macOS credential-file-read boundary, not comprehensive host confinement.

Ringer's `redact_spec` does not redact all returned output in main. [PR #130](https://github.com/NateBJones-Projects/ringer/pull/130) proposes captured-output redaction after a reported incident. Do not forward raw credential-bearing logs as integration evidence or describe the combined workflow as sanitized merely because one component filters its own output.

### Revision and distribution contracts

Ringer can update itself before command dispatch, and its persistent HUD can restart after updates. Compatibility probes must pin both revisions and disable automatic updates and catalog refresh during the frozen trial. Record the actual running revision separately from a checkout that might change later. Future adapters should declare supported receipt versions and refuse unsupported shapes.

Upstream `LICENSE.md` is PolyForm Shield 1.0.0 with a noncompete condition; Harnessie is Apache-2.0. Keep independent distribution and original integration code as the proposed architecture. Do not copy upstream implementation or assume that a combined distribution is licensed merely because the projects are intended to complement each other. Resolve any actual packaging or reuse proposal against the license and maintainer permission. This assessment makes no legal compatibility determination. [Inspected license](https://github.com/NateBJones-Projects/ringer/blob/0be58d3bef0a1d3eb133fddbfa51fc7ab55c8591/LICENSE.md)

## Delivered versus proposed upstream work

Recent main changes include preserved retry patch archives ([merged #56](https://github.com/NateBJones-Projects/ringer/pull/56), September 15), early engine-command diagnostics (#59, September 10), and check-writing guidance (#57, September 7). Existing current-main capabilities above should not all be described as newly added in September.

Relevant open proposals, verified as open on September 17:

| PR | Proposed scope | Implication |
|---|---|---|
| [#133](https://github.com/NateBJones-Projects/ringer/pull/133) | Separate check timeout | Direct prerequisite for long inline model verification; not delivered. |
| [#129](https://github.com/NateBJones-Projects/ringer/pull/129) | Reported-cost aggregation, run ceilings and repeated-failure stopping | Coordinate accounting; do not assume its proposed controls exist on main. Its reported field measurements were not reproduced here. |
| [#130](https://github.com/NateBJones-Projects/ringer/pull/130) | Captured-output redaction | Relevant to shared reports and logs; not delivered. |
| [#104](https://github.com/NateBJones-Projects/ringer/pull/104) | Known-bad check exercise | Strong overlap with AC; baseline mode is already present, this additional mode is not. |
| [#100](https://github.com/NateBJones-Projects/ringer/pull/100) | Staged task dependencies | Would support producer-then-reviewer composition; current main tasks run as a flat concurrent set. |
| [#52](https://github.com/NateBJones-Projects/ringer/pull/52) | Provider-isolated decision template and optional record assembly | Composition proposal, not an existing AIDR runtime or human-arbitration enforcement. |
| [#103](https://github.com/NateBJones-Projects/ringer/pull/103) | Align `ask` prompt with required `answer.md` output | Do not select `ask` as a proven onboarding path without reconciling this open mismatch and doing a live acceptance test. |

## Consequences for the four design packets

- AC: Ringer already pairs task specs and checks and offers baseline/bakeoff fixtures. Focus Harnessie's addition on frozen human-accepted criteria, protected tests and artifact-bound verdicts. Propose a mapping from an accepted brief to both a Ringer check and a Harnessie contract rather than two separately edited specifications.
- VI: reuse identity vocabulary, explicitly preserve cannot-verify and its cause, and distinguish engine diversity from proven independence. Do not claim confinement of external workers or authentication of the outer operator.
- CE: reuse upstream attempt IDs, task types and human-repair measurements. Add claim correctness, exposure, held-out calibration and complete nested verification cost. Avoid duplicating its model catalog, exploration UI or field heuristics.
- FA: Ringside already provides the results surface. Its interview prompt is also prior art for producing a brief in an existing chatbot. Test a short Harnessie evidence report in that workflow before proposing another UI or intake system. Import and validate a human-confirmed brief rather than forcing the operator through two interviews.

## Proposed next implementation packet

Prepare one compatibility recipe owned by Harnessie, requiring no copied upstream code or new universal protocol. First prove with model-free fixtures that the current process seam preserves all three Harnessie outcomes, durable evidence and original criteria across retries and worktree cleanup. Name the check-timeout and outer-retry limitations in the recipe; do not paper them over with success exits. Then run one separately authorized live task through pinned builds with a shared resource ledger.

Acceptance should include: a valid artifact, a refuted claim, missing proof, an unavailable verifier, a changed artifact, a timed-out check, cancellation, a retry and worktree cleanup. The operator must be able to distinguish execution success from acceptance and see who has the next action. The first live trial is one task with one reviewer, not a swarm or model comparison campaign.

## Documentation corrections to prepare

`docs/ringer.md` currently overstates built-in AIDR interoperability and genuine independence of different engines. Narrow those statements to external composition and identity/exposure evidence. It also presents the inline verifier command without the current 60-second check limit, cannot-verify retry consequence or report-survival contract. Prepare those updates from this assessment and regenerate HTML through the normal pipeline when authorized; no public documentation or generated HTML was changed in this review.

## If Ringer succeeds

Ringer's wider adoption can increase the number of tasks that benefit from Harnessie's acceptance checks. That strengthens Harnessie's position if its contracts remain useful from any runner and its evidence is easy to display. Duplicating dispatch, catalogs and mission-control screens would instead spend effort on the part upstream already owns well. Keep Harnessie independently usable so neither project needs to become a dependency of the other to function.

## Integration contract to settle

Migrated from the processed 2026-09-17 RI handoff. Proposal only; nothing here is implemented.

- One accepted contract: bind the original task, criterion IDs, requiredness and check definitions to the artifact revision. An adapter maps the contract; it does not rewrite the human's intent.
- Three acceptance outcomes: retain verified, failed and cannot-verify in the durable receipt and operator summary, and preserve Ringer's actual outer status. If current Ringer shows FAIL for exit 2, disclose that mapping rather than claiming native three-state UI support.
- Separate retries: a verification infrastructure problem cannot silently trigger a producer rewrite. The minimal recipe may use one outer attempt and an explicit rerun. Any automatic producer or verifier retry has one named owner, its own ceiling and causal classification.
- Real cancellation: the enclosing deadline and cancellation reach the verification process and children; no detached model job continues after Ringer records completion or timeout. A missing or interrupted receipt is incomplete, never an old success reused.
- Durable evidence: unique run/task/attempt identities; preserve all outcomes beyond cleanup and retries; bind reports to artifact and contract hashes; refuse stale results. Logs or excerpts are not receipts.
- Truthful display: Ringside's declared `verified` sentence describes the check; acceptance comes from the current receipt. Start with an existing report/artifact surface. Failure evidence stays reachable even where upstream only harvests passing deliverables.
- Complete accounting: distinguish worker, verifier and check resources, configured vs observed identity, known vs unknown usage, outer vs inner failures. Do not penalize the worker for missing verifier credentials or infrastructure.
- Explicit boundary: Harnessie confines its own verification execution per the active contract; it does not confine the Ringer worker or authenticate the operator as human. A report is not permission to merge, publish or arbitrate.
- Post-run path: label Ringer producer completion and Harnessie acceptance separately; the consuming workflow holds downstream use until acceptance. Inline path: keep a nonzero exit whenever required verification is incomplete; never return 0 merely to prevent a retry.

## Deterministic acceptance matrix

| Scenario | Required observation |
|---|---|
| Valid artifact and complete required evidence | Verified receipt and matching artifact/contract identity; outer behavior agrees with the documented path. |
| A required claim is refuted | Failed receipt with evidence; bounded correction may target that defect. |
| Missing proof or unavailable verifier | Cannot-verify retained; no silent producer rewrite or successful acceptance. |
| Artifact or criteria change | Prior verdict cannot apply to new bytes; refresh or refuse explicitly. |
| Check timeout or operator cancellation | Child processes terminate and outcome remains incomplete; no stale pass is displayed. |
| Explicit producer or verifier retry | New attempt identity and costs; earlier reports survive. |
| Successful worktree deletion | Verified artifact identity and complete report remain available outside the deleted tree. |
| Failed task not harvested by Ringside | Its receipt still has a stable, usable path and the operator can find the failure. |
| Malformed/unsupported receipt or missing resource counter | Refusal or documented unknown; no silent promotion or invented zero. |
| Synthetic credential-like content in evidence | The proposed output boundary behaves as documented; no claim that unmodified upstream logs are automatically sanitized. |
