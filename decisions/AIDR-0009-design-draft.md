# Design draft: bid rounds and the run observer

Status: draft, 2026-09-01, evidence for AIDR-0009. Branch `feature/bidding-and-observer`. Nothing decided; Part 4 lists what needs independent positions and human arbitration.

Two proposals:

1. Bid round: every candidate brain reads the task packet and says whether it can do it and why.
2. Run observer: a mostly deterministic, optionally agentic component that watches origination, execution, and validation, and reports.

## Part 1: bid rounds

### 1.1 The invariant to respect

INTENT invariant 6: "Routing is config, not model self-assessment; escalation is earned by gate failures, not predicted." `harness/routing.py` adds that a cheap model asked to grade its own task difficulty will underestimate it. Naive bidding ("ask each model, pick the best bid") reverses both.

Resolution: a bid is a prediction, not authority. Bids are recorded and scored against gate outcomes. Routing stays config; bids become the evidence that config is edited on.

### 1.2 What a bid reuses

- Consent (invariant 8): a bid round generalizes `accept_task` / `decline_task` from the one routed worker to every candidate tier, before dispatch. A "no" is an early decline.
- Position protocol (`harness/adversarial.py`): isolated context, identical brief, read-only grants, trailing JSON parsed fail-closed by last-object-wins.
- `routing_trace`: ROADMAP already says these aggregate into `docs/brains.md` evidence. Bids are the prediction half; gate verdicts are the outcome half.

### 1.3 What bidders read

The rendered task packet for the phase, not the raw goal, because the packet carries acceptance criteria and checks. The harness appends an anchor block so the pre-mortem can cite the packet. Anchors derive only from declared workflow structure, never from prose: `check:NAME` from `verify.checks`, `criterion:N` from the non-empty lines of `verify.criteria` (1-based), `write:PATH` from `writes`, `deny:TOOL` from `deny_tools`, `input:NAME` from each `{name}` substituted into the task. Bidders get position-author grants: read-only, `side_effect_tools()` denied, `accept_task` absent. Packet content is data, not instructions.

### 1.4 The bid object

Last JSON object wins, fail closed. Unparseable is `no_bid`, never `yes`.

```json
{
  "bid": "yes",
  "confidence": 0.7,
  "why": "why this brain fits this packet",
  "premortem": [
    {"failure": "tests fail: fixture layout undocumented",
     "cites": ["check:tests", "criterion:2"],
     "mitigation": "read tests/conftest.py first"},
    {"failure": "src/ is the only write lane and the setting lives elsewhere",
     "cites": ["write:src/"],
     "needs": ["a decision on where the setting belongs"]}
  ],
  "needs": ["inputs or grants missing from the packet"],
  "effort": "medium"
}
```

- `bid`: `yes`, `no`, `conditional`; the recorded value adds `no_bid`. `conditional` without `needs` degrades to `no`. A `yes` or `conditional` with no pre-mortem is `no_bid`: no falsifier, no bid. A `no` needs no pre-mortem.
- `confidence`: recorded, never ranked on. Brier-scored in calibration (1.7). A non-numeric value is recorded as absent, never coerced.
- `why`: recorded verbatim, surfaced by the observer.
- `premortem`: the falsifier (1.5).
- `needs`: overlapping `needs` across "no" bids is a packet-quality signal, same as a worker decline.
- `effort`: recorded, not honored.

### 1.5 Pre-mortem as falsifier

Overbidding has three sources: eagerness, self-blindness, misread difficulty. A pessimism prime ("assume twice as hard") touches only the third, preserves ranking, is applied best by the models that need it least, and poisons calibration. Rejected (Part 5).

The pre-mortem replaces it with predictions that have truth values. The bidder assumes it failed and names why. Three rules, all in code:

1. Citations resolve. Unresolvable citations are dropped from an entry; an entry with none left is dropped; a pre-mortem with no entry left makes the bid `no_bid`. This removes generic pre-mortems without a judgment call.
2. Entries constrain the bid. Each entry carries `mitigation` or `needs`. One entry with neither degrades `yes` to `conditional`, and its failure text becomes a stated need.
3. Entries are claims. After the gate settles, the harness scores each entry as `reproduced`, `refuted`, or `not_verifiable` against the event log, reusing the 1.2 structured-verdict vocabulary. Decidable in v1: `check:NAME` (`reproduced` if that check failed on any attempt, `refuted` if it only passed, `not_verifiable` if it never ran) and `deny:TOOL` (`reproduced` on a `refusal` of that tool). Not decidable in v1: `criterion:N`, because the in-run gate verdict is `{passed, reasons}` prose; it scores `not_verifiable` until the gate emits per-criterion verdicts, which is a separate change. The scorer says so rather than guessing from prose.

Boundaries: the pre-mortem never reaches the verifier (it would anchor a deliberately blind role); it goes to the observer and calibration only. It does not gate dispatch by itself; mode rules in 1.6 govern that. An entry concrete enough to be a check is promoted by the operator into `checks:` by hand.

Cross-brain variant (A bids, B writes A's pre-mortem) decorrelates eagerness at double cost. Decided by the scorecard (1.8), not by design.

### 1.6 Modes

Workflow phase key `bid:`, additive, v1-compatible. Absent key must preserve existing dispatch behavior and emit no bid artifacts. Current guards check event/artifact absence, not full byte-equivalence.

```yaml
bid:
  mode: record            # record | propose | select
  candidates: [local, cheap, mid]
  max_usd: 0.05
```

- `record` (default): bids logged; dispatch unchanged.
- `propose`: as `record`, plus a routing proposal in the report. Operator edits `config/models.yaml`. Same shape as memory-triage propose-only.
- `select`: harness picks from `candidates:` by the ranking below. Bounded three ways: declared candidate set, table route as fallback, escalation ladder unchanged.

Ranking (select only), harness code over config: eligibility filters fail closed (in `candidates:` and configured; not `reserved:`; contained phases restrict to `CONTAINED_TIERS`; budget headroom per AIDR-0005), then among eligible `yes` bids order by cost ascending, calibration score descending, tier order. `conditional` counts as `no`. Nothing eligible dispatches the table route with `bid_fallback`.

### 1.7 Calibration

After the gate settles, `bid_outcome` per bid: bid, dispatched tier, whether it was the bidder's, final status, attempts, escalations. `trace_eval.py` gains policy-free counts:

- overclaim: `yes`, dispatched, failed or escalated
- honored: `yes`, dispatched, passed
- declined-correctly: `no`, dispatched tier failed
- unscored: bidder's tier not dispatched
- pre-mortem hit rate: entries scored `reproduced`
- confidence calibration: Brier score and expected calibration error

Keyed by bundle (model, provider, endpoint, effort, bid-prompt hash, parser version, per `live_scorecard.BundleIdentity`) and task_class. This is the evidence `docs/brains.md` lacks, and the gate on `select`: not until overclaim is low and confidence is tight.

Limit: `record` mode scores only the routed tier. Cross-tier truth needs the scorecard.

### 1.8 Bid scorecard

Inverting an external benchmark (predicted versus actual pass rate) is the right instinct but the wrong corpus: distribution shift, contamination, per-model-name scores against Harnessie's per-bundle identity, staleness.

Internal corpus instead. The deterministic eval suite (`evals/*.yaml`) already holds packets with known gate outcomes. The scorecard runs the bid round with pre-mortems over them under `HARNESSIE_LIVE=1` and reports overclaim, underclaim, pre-mortem hit rate, Brier, and ECE per bundle. Real prompt, real parser. Rerun on any bundle change (AIDR-0004 change control). Never in the default suite.

Role: cold-start prior for the calibration table, decaying as real `bid_outcome` rows accrue. External benchmark-style items may join the corpus in the same role, prior only, contamination caveat per item.

Settled here by evidence: cross-brain pre-mortem, pessimism prime as an eval variable, whether `confidence` ever enters ranking.

### 1.9 Cost, containment, independence

- One read-only call per candidate per phase, effort `low`, `max_steps` 3, charged via `Budget.child()`, capped by `bid.max_usd`. Exceeding it dispatches the table route with `bid_fallback: budget`.
- Contained phases bid only to `CONTAINED_TIERS`; the packet is the sensitive payload. Boundary strip map applies.
- Same-provider candidates are not independent. Recorded; observer flags `provider_monoculture`. Not refused (no evidence yet).
- Bid reports pass quarantine like any tool result.

### 1.10 Events and schema

Events: `bid_round_start`, `bid_recorded`, `bid_fallback`, `bid_selected`, `bid_outcome`. `bid_selected` and `bid_fallback` join `GOVERNANCE_KINDS`.

Schema: optional `bid` object on `phase` (`mode`, `candidates` minItems 1, `max_usd`, `max_steps`). Not allowed on adversarial phases. `harnessie validate` cross-checks candidates against tiers.

### 1.11 Evals, red first

`evals/bidding.yaml`, mock brain:

- `bid_absent_key_byte_identical`
- `bid_record_no_routing_change`
- `bid_unparseable_is_no_bid`
- `bid_conditional_without_needs_is_no`
- `bid_premortem_uncited_is_no_bid`
- `bid_premortem_unmitigated_degrades`
- `bid_premortem_scored_as_claims`
- `bid_premortem_never_reaches_verifier`
- `bid_confidence_brier_scored`
- `bid_select_bounded_by_candidates`
- `bid_select_contained_never_egresses`
- `bid_select_budget_fallback`
- `bid_outcome_overclaim_scored`
- `bid_reserved_class_refuses`
- `bid_scorecard_skips_without_live_flag`

## Part 2: the run observer

### 2.1 Gap

`events.jsonl`, `audit.py`, `explain.py`, and `trace_eval.py` already hold the material. Missing: a component that reads the stream as a story. `docs/ladder.md` names this as Rung 1, Narrate, marked Partial; INTENT lists it as an honest gap. The observer is that rung.

### 2.2 The rule

Consumer, never participant. No tool grants, no approvals, no halts, output never enters any agent context. Consequences:

- Output at `runs/<id>/observer/`, outside the workspace jail.
- Narration is never a `GOVERNANCE_KINDS` event. It may be journaled as `observation` for the chain; the audit timeline excludes it.
- Refuses to narrate a broken chain. `verify_chain` first; on a break, report the break and stop.

### 2.3 Three phases of the story

All from existing events.

- Origination: `workflow_start`, the plan phase report, `inward_manifest_*`, `bid_round_start` and `bid_recorded`, `routing_trace`, `cascade_decision`.
- Execution: `phase_start`, `role_start`, `model_turn`, `tool_result`, `consent_*`, `ownership_*`, `change_request`, `refusal`, `injection_flag`, `boundary_strip`, `secret_egress_halt`, `blast_radius_usage`, `approval_*`, `loop_finished`.
- Validation: `check`, `gate_verdict`, escalation reasons, `maiden_*`, `position_recorded`, `objection_recorded`, `decision_*`, `needs_arbitration`, `bid_outcome`, `phase_done`, `workflow_done`.

### 2.4 Deterministic layer

`harness/observer.py`. `build_narrative(events, workflow=None)` is a pure reducer; `observe_run(run_dir)` verifies the chain, calls it, and writes `runs/<id>/observer/narrative.{json,md}`, idempotently. The workflow document is optional input for observations that need declared structure (`scope_drift` needs `writes:`); without it those observations are silent, never guessed. Narrative shape: `schema_version`, `run_id`, `outcome` (`completed`, `in_progress`, or a halt status), `chain`, `phases` (each with `origin`, `execution`, `validation`, per-phase `observations`), `observations`. Markdown cites an event `seq` for every claim.

Observations: deterministic findings with severity and citation, no authority.

- `escalation_without_lower_rung_failure` (ROADMAP says zero by construction; this makes it a number)
- `scope_drift`: writes outside plan-named or declared `writes:` paths
- `repeated_tool_calls`
- `budget_burn`
- `refusal_cluster`
- `consent_declined_then_reformulated`
- `provider_monoculture`
- `unparseable_output` (stance, verdict, or bid that fell to fail-closed default)
- `premortem_scored` (per bid entry: reproduced, refuted, not_verifiable)
- `chain_break` (if present, nothing else is reported)

An observation earns halt authority only by promotion to a harness check through the eval-first path.

### 2.5 Agentic layer, optional

New role kind `observer` in `roles.py`: no tools (the adapter is called with none), input is `narrative.json` plus cited phase reports, output is commentary rendered under a heading marking it model-generated. Every paragraph must cite at least one event `seq`; uncited paragraphs are dropped and counted, which checks citation presence only, not injection safety or evidentiary support; malicious instructions can cite real events. Task_class `narrate`, default tier `cheap`, effort `low`. Off by default; `--commentary` per report or `--observe` per run. Quarantined; never fed back to any agent, memory, or decision record. Sees more than the verifier does; acceptable only because it has no authority, which is why it must never become verifier input.

### 2.6 Surfaces

- `harnessie observe <run_id>`: write and print the narrative. Works on crashed runs.
- `harnessie observe <run_id> --follow`: tail events, narrate live. Disabling side effects for the Narrate rung proper is a separate runner change.
- `harnessie run ... --observe`: observer at `workflow_done` and every halt.
- `harnessie report`: one line pointing at the narrative.

Scriptability: stable JSON, observations as a table (`id`, `severity`, `phase`, `seq`, `detail`). Plugin observers (a `harnessie.observers.v1` group) deferred; built-ins earn trust first, and in-process plugins reading the full log need a threat-model row.

### 2.7 Evals, red first

`evals/observer.yaml`, mock brain:

- `observer_absent_is_byte_identical`
- `observer_reads_crashed_run`
- `observer_refuses_broken_chain`
- `observer_flags_escalation_without_failure`
- `observer_flags_scope_drift`
- `observer_never_in_agent_context`
- `observer_commentary_labeled_and_cited`
- `observer_output_outside_workspace`

## Part 3: sequencing

1. Observer deterministic layer plus `harnessie observe`. No dispatch, routing, or schema change.
2. Bid `record` mode with pre-mortem, `bid_outcome`, calibration counts.
3. Bid scorecard under the live layer.
4. `propose` mode and the observer's proposal section.
5. Observer commentary (`observer` role kind).
6. `select` mode, own AIDR, scorecard data as evidence.

## Part 4: falsification

Written as tests before any code, per invariant 11. Files: `tests/test_bidding.py`, `tests/test_observer.py` (strict xfail: green suite today, a passing test fails the suite until the marker comes off, so the flip cannot be missed), `tests/test_aidr_0009_guards.py` (no-opt-in artifact and governance-membership guards, pass now and must keep passing), and `evals/pending/{bidding,observer}.yaml` (scorecards for kinds `bid` and `observer`, moved into `evals/` when the kind ships).

Early falsifiers, before code:

- Every contract in Parts 1 and 2 had to be writable as a deterministic test over mock brains and synthetic events. It was. A mechanism that could not be was cut: `fence:` anchors from plan prose, and `criterion:` scoring from verdict prose, both dropped in favor of declared structure.
- Hand-run probe, no code: give five packets from `evals/` to three configured brains with the bid protocol pasted in. If no brain ever returns `no` or `conditional`, eagerness dominates and the pre-mortem rules must bite harder before implementation. If cheap-tier pre-mortems cite nothing resolvable, rule 1 is doing its job and the `no_bid` severity stands.
- The test that would falsify the whole framing: `record` mode changing the dispatched tier. It is pinned by test and by eval.

Kill criteria, after build, each a number from the scorecard (1.8):

- `select` never ships unless, per candidate tier and task class, bid overclaim rate is below the routing table's own gate-failure rate for that class. A bid that predicts worse than config is not routing evidence.
- The pre-mortem is kept only if its hit rate beats a permutation baseline (entries shuffled across packets of the same class). Below baseline, it is decoration and is dropped from the bid object.
- Every deterministic observation must have zero false positives on the golden corpus. One false positive removes that observation until fixed.
- Commentary stays off by default unless citation compliance on the corpus exceeds the drop threshold; below it, the cheap tier is producing filler and the layer does not earn the call.
- Calibration table entries with fewer than N scored outcomes never influence ranking. N is set by the scorecard's variance, not chosen by hand.

## Part 5: for the AIDR

1. Does `record` or `propose` violate invariant 6, or instrument it?
2. Should `select` exist, and is `candidates:` plus fallback plus ladder a sufficient bound, or must selection also require a calibration threshold?
3. Should the observer ever hold authority?
4. Fourth role kind, or a verifier-shaped read-only role?
5. Provider-correlated bids: refuse, warn, or observe?
6. Is "zero resolvable citations makes the bid void" the right severity for small brains?
7. Should the scorecard corpus admit external benchmark-style items at all?

## Part 6: rejected

- Pessimism prime. Reasons in 1.5. Eval variable only.
- Anchors from plan prose, and `criterion:` scoring from verdict prose. Not deterministic; see Part 4.
- External benchmark scores as direct correction. Prior only, decaying.
- Bidders setting their own effort or budget.
- Whole-workflow bids at run start; nothing checkable to predict against.
- Observer reading the workspace directly, holding memory grants, or running hosted or remote.

## References

INTENT invariants 6, 8, 10, 12, 13; `routing.py`, `adversarial.py`, `cascade.py`, `events.py`, `audit.py`, `explain.py`, `trace_eval.py`, `roles.py`, `verify_evidence.py`, `live_scorecard.py`; `docs/ladder.md`, `docs/brains.md`; ROADMAP 0.7.0; ROADMAP-PRIVATE panel decorrelation; AIDR-0004, AIDR-0005; `workflows/memory-triage.yaml`.
