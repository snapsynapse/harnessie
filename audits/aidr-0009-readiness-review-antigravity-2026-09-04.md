# AIDR-0009 readiness review: Google Antigravity

Date: 2026-09-04
Reviewed base: `feature/bidding-and-observer` at committed HEAD `b3efeca`
Scope: One of four independent engine reviews (Codex, Claude Code, Google Antigravity, Qwen 3.8) assessing whether AIDR-0009 (bid rounds and a run observer) is ready for human arbitration. Read-only analysis produced prior to writing this record at operator request.
Lane: Architecture and integration seams. Map observer and bidding changes across CLI, runner, events, roles, schemas, audit, reporting, routing, budgets, and documentation. Identify coupling or sequencing hazards.

ENGINE: Google Antigravity
LANE: Architecture and Integration Seams
REPOSITORY ACCESS: full

RECOMMENDATION: conditional
ONE-SENTENCE RATIONALE:
The two-surface design is architecturally sound and cleanly decoupled, provided the deterministic observer ships first with zero schema or role changes while candidate bid generation strictly enforces containment filters and budget ceilings before dispatching candidate calls.

AIDR READINESS:
- Ready for arbitration: yes
- Missing evidence or decisions:
  - Decision on whether a contained phase declaring exposed candidate tiers in `bid.candidates:` must fail closed at preflight or silently prune exposed candidates.
  - Decision on whether `Budget.child()` must take an explicit `max_usd` argument to prevent a wide candidate list from exhausting phase headroom before worker dispatch.
  - Empirical baseline confirming that the deterministic observer reducer incurs zero noticeable CLI latency when processing multi-megabyte `events.jsonl` files.
- Questions Sam must arbitrate:
  - Confirm that `select` mode is excluded from implementation and authoring schemas until calibration evidence is produced under a separate AIDR.
  - Confirm that candidate bid generation for contained phases must prune exposed tiers before prompt dispatch, not merely at selection time.
  - Confirm that the `observer` role kind and LLM commentary are deferred to a later slice, keeping the initial observer entirely deterministic.

FINDINGS:
1. Complete decoupling of the deterministic observer: `harness/observer.py` functions as a pure reducer over `events.jsonl`. It requires no model adapters, no prompt files, no changes to `ROLE_KINDS`, no changes to `workflow.schema.json`, and no alterations to runner phase dispatch logic.
2. Schema and trust-bundle synchronization blast radius: Adding `bid:` to workflow phases requires editing `harness/schemas/v1/workflow.schema.json`, mirroring byte-identically into `docs/schemas/v1/workflow.schema.json`, recomputing SHA-256 hashes in `docs/MANIFEST.yaml`, and updating generated documentation. Slicing the observer first completely avoids touching public schemas and trust manifests.
3. Contained phase prompt egress hazard during bid rounds: `test_select_contained_filters_exposed_tiers_before_ranking` tests ranking, but the candidate dispatch loop itself must filter candidate tiers against `CONTAINED_TIERS` (`local`, `sovereign`) before sending the rendered task packet to any brain. Dispatching a sensitive task packet to an exposed candidate in `record` mode would breach data containment before routing even occurs.
4. Budget leakage across candidate bid rounds: Each candidate in `candidates:` incurs token and dollar spend. A phase declaring multiple candidates could consume substantial headroom before execution begins unless `Budget.child()` enforces `bid.max_usd` as a hard cap. If candidate calls exceed `max_usd`, the runner must drop to `bid_fallback: budget` and dispatch the configured route without failing the phase.
5. Governance timeline separation: `harness/audit.py` defines `GOVERNANCE_KINDS`. The guard in `test_aidr_0009_guards.py` strictly verifies that `observation` and `narration` never enter the governance timeline. Conversely, `bid_selected` and `bid_fallback` must join `GOVERNANCE_KINDS` because they record dispatch authority.

FALSIFIERS:
- Most important existing falsifier: `test_workflow_without_opt_in_emits_no_bid_or_observer_artifacts` and `test_record_mode_bids_every_candidate_and_dispatches_the_table_route`, proving that unconfigured workflows emit no extra events and `record` mode never alters dispatch routing.
- Missing falsifier: A strict test asserting that for a contained phase, candidate bid prompt generation never invokes any model spec outside `CONTAINED_TIERS`, even if exposed tiers were explicitly listed in `bid.candidates:`.
- Condition that would reverse your recommendation: Evidence that observer execution requires write access inside `workspace/`, leaks observation text into agent prompts, or that candidate bidding in `record` mode alters the dispatched worker tier.

IMPLEMENTATION MAP:
- First safe slice: Deterministic run observer in `harness/observer.py` and CLI command `harnessie observe <run_id>`. Zero schema changes, zero prompt modifications, zero model calls.
- Required production modules:
  - New module: `harness/observer.py` (`build_narrative`, `render_narrative`, `observe_run`).
  - `harness/cli.py`: add subparser for `observe`.
  - `harness/explain.py`: add pointer to observer narrative when present.
- Tests that should turn from strict xfail to passing:
  - `tests/test_observer.py`: tests covering `test_narrative_has_stable_shape_and_cites_seq`, `test_crashed_run_marks_last_phase_in_progress`, `test_escalation_without_lower_rung_failure_is_observed`, `test_earned_escalation_is_not_observed`, `test_scope_drift_needs_declared_writes_and_cites_the_claim`, `test_unparseable_output_and_provider_monoculture_are_observed`, `test_bids_appear_in_origin_and_premortem_scores_are_observed`, `test_observe_run_refuses_a_broken_chain`, and `test_observe_run_writes_outside_the_workspace_and_is_idempotent`.
- Work explicitly deferred:
  - Phase key `bid:` and candidate evaluation (`harness/bidding.py`).
  - Workflow schema changes in `harness/schemas/v1/workflow.schema.json`.
  - Model commentary and fourth role kind `observer` in `harness/roles.py`.
  - Live bid scorecard and `select` mode routing.
- Main regression risk:
  - Potential crashes in `build_narrative` when handling partially written or unexpected event shapes from aborted or older runs.
  - Accidental output collision if `runs/<run_id>/observer/` pathing resolves within a workspace boundary.

CROSS-ENGINE HANDOFF:
- One claim another engine should challenge: The claim in `AIDR-0009-design-draft.md` that `criterion:N` pre-mortem claims can be scored after gate settlement without migrating the verifier gate to emit per-criterion structured verdicts first.
- One question another engine should answer: For Claude Code (Decision Reviewer): Should a workflow declaring `bid.candidates` with exposed tiers on a contained phase fail closed at schema validation or silently filter out exposed candidates at runtime?
- Evidence Sam should compare across all four reports: Agreement across engines that the deterministic observer has zero architectural coupling to bidding and should ship as a completely independent first slice before any schema or dispatch changes are made.

STOP CONDITION:
I made no production code changes, ran no live provider calls, and invoked no external models while producing this review.
