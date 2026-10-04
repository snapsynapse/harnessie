# Acceptance and verification design assessment

Date: 2026-09-17
Scope: Harnessie product and runtime, under this repository's authority.
Status: design recommendations and candidate work packets, not an adopted architecture or implementation approval.
Inspected source: `aae3daa6e46858f1bc8dd39061d9973a2d73126a` on local `main`.

## Purpose and evidence boundary

The operator asked which capabilities described in [Signals & Subtractions episode 10](https://sigsub.show/episodes/ep-010/transcript/) would improve Harnessie, what could be scoped into handoffs, and what should remain on the roadmap. The relevant passage is 20:39 through 21:56: spec and test authoring, competitive task offers, execution, validation by the original spec writer, a third AI logging the run, and different model families.

The transcript was read from the episode source and generated page in the local show checkout after the public transcript reader failed. The indexed public episode summary describes the same sequence. Live transcript bytes and current GitHub branch tips were not verified. Local refs were inspected; `feature/bidding-and-observer` contains preparation, designs and pending tests, with no additional runtime implementation. Current source and the September 9 capability assessment take precedence over that branch's earlier proposal.

No live model evaluation was performed. Claims below distinguish observed source behavior from recommendations and hypotheses. Existing human arbitration and the approved capability sequence remain authoritative.

The later [Ringer/Ringside comparison](ringer-ringside-interoperability-2026-09-17.md) refreshed both projects' remote main refs and inspected current upstream source. It identifies existing upstream onboarding, identity, evaluation and display capabilities that these packets should compose with, plus timeout, retry and receipt gaps. The initial transcript retrieval limitation above remains unchanged.

## Recommended direction

Make the acceptance contract, its ownership, and the evidence for a verdict explicit before adding more model coordination. Keep the current workflow orchestrator and standalone verifier. Reuse ownership lanes, deterministic checks, evidence bundles, model routing, and the event log. Begin with an opt-in worked example and narrow validation rules; justify any new public schema or role separately.

The target flow is: clarify intent and acceptance criteria; review and freeze the contract; offer a bounded implementation task; execute; run protected checks; obtain the declared verification evidence; present unresolved findings to the human. Criteria amendments create a new contract revision and invalidate affected results. They cannot silently redefine an attempted task's success.

## Disposition of the episode capabilities

| Capability | Recommendation | Smallest useful next scope |
|---|---|---|
| A model drafts the spec and tests before implementation | Pursue as an opt-in recipe. The value is a reviewable contract and protected tests, not a universal demand that an AI author them. | Define author, implementer and verifier ownership; freeze criterion IDs and executable checks; prove a known defect fails and a known valid result passes. Accept existing human-authored tests too. |
| The original spec writer validates the implementation | Retain the author's contribution to clarifying intent. Do not make that author the sole mandatory judge. | Record authorship and contract provenance. Evaluate an optional author review separately from a fresh-context verifier, with neither silently rewriting the contract. |
| Different model families perform the roles | Offer a policy choice once identity and fallback semantics are explicit. Do not treat family labels as proof of independence. | Specify required versus preferred diversity, unknown identity, actual resolved routes, context exposure and containment. Measure detection of shared mistakes. |
| Models bid for work | Continue the existing record-first program. An offer, refusal or counter-proposal is already useful without a competition. | Bound candidate exposure, spend and parsing; collect predictions without changing dispatch. |
| A bid winner executes the task | Keep automatic selection gated on evidence. Self-confidence alone is not an admission rule. | Compare with configured routing on held-out tasks, including verification cost, failures and human review. Preserve the separate selection AIDR. |
| A third AI logs everything | Keep the runtime event log authoritative. Optional model commentary may help an operator interpret it. | Complete deterministic observation first. Commentary remains derived, cited, non-authoritative and excluded from agent and verifier context. |
| The winner fans out agents | Use declared parallel phases and explicit ownership first. Dynamic delegation is a later candidate. | Require a real workload where static phases are inadequate, plus inherited permission, ownership, budget, cancellation and verification contracts. |
| Local and frontier models are interchangeable participants | Preserve the existing adapter seam. Capability and verification policies must work for an entirely local deployment. | Record configured and observed identity separately, and refuse rather than silently adding cloud egress to meet a diversity preference. |

## Source findings that shape the packets

1. `workflows/build-and-verify.yaml` asks the orchestrator to produce a plan without writing files. The implementer writes tests when the plan lacks them. A spec author that writes executable tests must use a confined worker role or a separately prepared artifact; adding write tools to the orchestrator would weaken the current role boundary.
2. `OWNERSHIP.yaml`, `harness/ownership.py` and the sandbox overlays can protect another agent's files. The shipped example does not declare a dedicated acceptance-test lane. Write protection does not establish test completeness, and read-together ownership is not test secrecy.
3. `harness/verify_standalone.py` checks exact claim coverage and required/optional classification for an evidence bundle. `harness/verify.py` parses verdicts for ordinary workflow phases but has no equivalent phase-owned expected-claim set. Reuse the existing claim contract before inventing a second verdict vocabulary.
4. `harness/runner.py::_verifier_task` includes the worker's final report as unverified claims. A fresh context excludes the worker conversation, but does not mean an evidence-only blind review. A report-free first pass is an experiment, not an existing guarantee.
5. `harness/verify.py::VerificationGate.run` can pass when checks pass and no verifier is configured, including when the check list is empty. This makes explicit verification requirements and nonempty evidence a concrete design priority. Determine compatibility and admission rules before changing generic phase semantics; do not silently reinterpret existing workflows.
6. `config/models.yaml` routes both implementation and verification to the mid tier by default. `ModelSpec.provider` identifies the adapter, such as `openai-compat`, and cannot establish who trained the model. `harness/adversarial.py` currently earns its independence claim from distinct provider strings. Preserve historical claim semantics while designing a more precise, versioned statement.
7. `harness/live_scorecard.py::BundleIdentity` already binds model, provider, endpoint, role prompts, parser and sampling. Mutable local model tags and declared family labels need additional provenance if they influence admission. Do not build an unrelated identity registry for each new feature.
8. `harness/routing.py::Budget.child` shares remaining parent headroom; it is not a reservation for future verification. The bidding design already needs a real round cap. Include verifier headroom and in-flight call accounting in that design so a successful worker cannot consume the evidence budget.

## Assumptions to test

| Claim | Evidence class | Why it matters | Cheapest disconfirming test |
|---|---|---|---|
| A frozen test suite measures the intended task | Assumption | Immutability can preserve a mistaken specification perfectly. | Have a human label one valid alternative and two intentionally wrong implementations; require the acceptance contract to distinguish them. |
| The spec author is the best final judge | Hypothesis | The author may preserve a misunderstanding that an independent reader would catch. | Compare author and fresh-context verdicts on the same frozen artifacts, including a deliberately flawed criterion. Preserve the disagreement. |
| Different families reduce shared false passes enough to justify their cost | Hypothesis | Diversity can increase latency and exposure without catching additional defects. | Compare same-family and cross-family reviewers against human-labeled defects at fixed task and budget conditions. |
| Bidders predict capability better than the routing table | Hypothesis | A bidding layer can add expense without improving assignments. | Use a fixed corpus, collect bids before execution, then execute eligible alternatives in isolated trials. Unexecuted bids remain unscored. |
| Model commentary reduces operator work | Hypothesis | Additional prose can increase review time or hide unresolved findings. | Compare time to identify the correct next action from the deterministic summary versus optional commentary; also count missed blockers. |
| Smaller review packets reduce review cost without suppressing uncertainty | Hypothesis | Compression can omit the only evidence that matters. | Include a halted run and a missing-proof case; require a reviewer to find both from the packet and open the cited evidence. |

Research gives reasons to run these comparisons, not results for Harnessie. [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/abs/2410.21819) reports familiarity-related evaluation bias in its studied setting; it does not prove that a different family solves this repository's verification problem. [Anthropic's agent evaluation guidance](https://anthropic.com/engineering/demystifying-evals-for-ai-agents) recommends combining deterministic, model and human grading and checking outcome quality. The proposals here apply those ideas to the inspected code; no performance improvement is claimed.

## Four bounded work packets

### AC: acceptance contract and protected tests

First deliverable: an opt-in recipe specification, failure matrix and exact proposed file scope. Reuse existing ownership, checks and evidence bundles. Define a bounded authoring phase, a freeze boundary, contract amendments, implementation rights, per-criterion verdicts and stale-result refusal. Separate contract authoring from execution and from delivery approval.

Acceptance must cover a known-bad implementation, a valid alternative, a worker attempting to weaken a test, a missing required claim, a changed contract on resume, and a test that fails because the environment is broken rather than the feature being absent. A test result must retain its causal category. See the roadmap candidate below; the temporary pickup packet is held locally under `handoffs/`.

### VI: verifier independence and truthful verification requirements

First deliverable: a design comparison and an AIDR-ready question, with no invented reviewer positions or arbitration. Define independence as separate properties: role permissions, context isolation, author exposure, model identity and evaluation evidence. Specify how ordinary verification, evidence-bound verification and a required diversity policy differ.

The strengthened opt-in profile must not accept an empty gate or silently downgrade when a verifier is unavailable. A preference may fall back only within declared policy, with the loss of diversity visible. Family-unknown must remain unknown. Both initial routing and retry/escalation routes must be checked. The spec author may identify ambiguity or raise an objection; authority to amend the task stays with the operator.

### CE: shared calibration and operator-review measurements

First deliverable: a frozen evaluation protocol and small human-labelable corpus plan, reusable by AC, VI and the existing bidding/observer program. Synthetic trials can verify protocol plumbing; only actual, authorized model trials can establish model quality.

Track false passes, false refusals, abstentions, criterion coverage, defect detection, model and check time, all trial cost, retries, and human review minutes. Missing usage is unknown. Use paired comparisons and separate calibration from held-out evaluation. Report inconclusive findings when sample size is inadequate. Bid confidence is scored against that candidate's actual execution result, not a mock model's known response. Observer usefulness is measured against the operator's correct next action.

### FA: first useful review in an existing workflow

First deliverable: a proposed first-use journey and evaluation packet for an operator who already uses agents and has too much work to verify. Start with one existing artifact, its original brief and a small set of reviewed criteria, using the standalone verifier. The authoring front end helps draft the criteria; it cannot accept them for the operator. Advanced role, routing and evidence configuration stays available to integrators.

Prefer an adapter or recipe in an existing terminal, editor or supported task check over a new application. A usable flow still needs explicit data scope, a supported model connection, cost limits and understandable results. Existing chat subscriptions are not automatically usable provider credentials. Agent-assisted setup must not give the outer agent authority to change policy or approve its own work.

A first-use trial succeeds when the operator completes a second review unaided, finds a seeded defect and missing evidence, understands what was checked, and knows the next action. Measure setup and report-reading time as part of total human effort. This is a proposed adoption test, not customer acceptance or a claim about a named person's willingness to adopt.

## Adoption and the original intent

The July intent is a safe first harness with enforced boundaries and legible human control. The September adoption direction makes standalone verification the smallest useful entry point for existing agent workflows. These fit together if the first encounter provides a bounded, useful review and the operator can later opt into governed execution. Adoption of the full orchestration model should not be required to get the first verification result.

The working audience inference is an operator already getting substantial output from agents who needs help deciding what can be used. Paul describes that problem in episode 10 and explicitly resists adding tools to his stack. He is an example to test with, not proof of a general market. Integrators need a stable command, exit codes and machine-readable evidence; the operator needs a short account of what changed, what was checked, what remains uncertain and what decision is theirs. Keep one underlying verdict contract across those surfaces.

The current `docs/quickstart.md` creates a project and introduces workflows and a mock build before applying the verifier to the operator's own work. That teaches the harness but does not yet demonstrate the September entry proposition. Retain mock exploration as an option; add a direct route to an existing artifact. A Markdown draft and its source notes are a plausible first trial for a knowledge-work operator; a PR is the stronger existing integration route for a technical user. File-digest evidence outside Git needs explicit design because the current evidence-bundle contract is Git-bound.

The safety ladder in `docs/ladder.md` currently uses human eyes on code as its main axis. That is insufficient for a person who cannot reliably evaluate the code, and repeated approvals can become ceremonial. A proposed replacement should describe granted effects and exposure, evidence requirements, operator decisions, and recovery. Reading more code may help a qualified reviewer, but is not a universal safety metric. Real model calls can disclose data and consume resources even when artifact writes are disabled.

Design requirements for FA and the other packets:

- Start with a confined copy or snapshot and a scoped evidence set. Model review can still create exposure and cost; display the destination and resource limits before dispatch.
- Treat imported output as untrusted. No automatic execution of commands discovered in a draft or repository. A check recipe declares its executable checks and its confinement requirements.
- Draft criteria from the original task and human intent, not solely from the worker's claims. Where the original brief is missing, disclose limited coverage and obtain intent before claiming task completion.
- Present checked, failed and unresolved criteria with evidence. Separate mechanical checks, source-supported conclusions and subjective editorial judgment. Do not collapse them into a general trust score or imply factual truth from a style rubric.
- Use one brief review result in the existing work surface, with deeper evidence available. Preserve every required failure and unresolved item even when summarizing; never hide missing evidence to reduce noise.
- Provide a bounded correction loop tied to the same contract and artifact revision. A retry can address a failed criterion but cannot quietly remove it. A later edit invalidates affected evidence; design partial reuse only when dependencies can be proven.
- Preserve the distinction between reviewing another agent's output and governing that agent's execution. Post-hoc verification cannot undo an earlier disclosure or confine an external runtime. A verification report does not itself block merge or publication; the consuming workflow must enforce that gate.
- Let operators save and inspect review profiles, pause, remove the integration and retain portable results. Automatic criteria extraction is assistance, not authority to expand scope or lower the quality bar.

These recommendations are consistent with the explicit capability disclosure, correction and user-control emphasis of [Microsoft's human-AI interaction work](https://microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/) and with [progressive disclosure](https://nngroup.com/articles/progressive-disclosure/). Neither source establishes that this proposed Harnessie journey works; FA must test it.

The phrase "safest first harness" remains a positioning ambition. Current source findings, including empty-gate behavior and the external-operator identity boundary, prevent an unqualified claim. Earn specific claims with adversarial mechanism tests, verified setup defaults and observed operator comprehension. A comparative superlative would additionally need a defined comparison set and measured outcomes.

## Recommended sequence and dependencies

1. Retain the existing controlled-review pilot as the approved next active runtime tranche; its provider and live-call requirements remain in its own packet.
2. Define the FA first-use journey alongside AC and VI, and include its measures in CE, without live calls. The adoption design should constrain the amount of configuration these packets expose. They do not require a bidding implementation.
3. Prefer an AC worked example and scoped evidence checks before broad workflow schema changes. Prepare the VI direction decision once its compatibility choices and counterexamples are concrete.
4. Continue automatic deterministic observation and record-mode bidding through the already recorded capability sequence. Reuse CE to decide whether model commentary, reviewer diversity and bidding improve outcomes.
5. Only promote automatic selection, adaptive review depth, or dynamic delegation after their evidence and policy decisions are complete.

The operator can reprioritize implementation. This assessment does not move the live pilot, adopt a new required diversity default, or authorize provider calls. Each temporary handoff is removed after its work is processed and durable outcomes are reconciled into the owning source, audit, roadmap or decision record.

## Roadmap candidates and promotion triggers

| Candidate | Trigger for implementation or expansion |
|---|---|
| Portable acceptance contracts reusable by standalone verification and governed runs | AC demonstrates an actual seam that cannot be expressed safely with the existing contracts; approve the smallest compatible extension. |
| Required or preferred model-family diversity | VI establishes declared versus observed identity, route/fallback behavior and containment; human arbitration adopts the policy. Quality claims additionally require CE results. |
| Original-author review as an additional perspective | CE shows useful incremental defect or ambiguity detection relative to independent verification, within a chosen review budget. |
| Review effort based on declared task risk | Stable evidence shows where added review helps; operator-defined profiles set requirements before dispatch, and uncertainty can never silently lower them. |
| Automatic bid-driven routing | Existing record, calibration and propose-only gates pass; compare against static routing and a history-based baseline before a separate selection decision. |
| Continuous AI commentary | Deterministic observation/follow boundaries are proven and commentary improves correct operator action without receiving execution authority. |
| Dynamic nested delegation | A concrete workload defeats declared phase composition, and a child cannot expand permissions, ownership or budget. |

Do not pursue a mandatory three-model pipeline, a same-author-only final gate, self-confidence as routing authority, or an AI-generated log as the authoritative audit record. Those constraints add cost or concentrate failure without established benefit.
