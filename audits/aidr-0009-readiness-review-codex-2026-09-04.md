# AIDR-0009 readiness review: Codex

ENGINE: Codex
LANE: Red-first test mapping and smallest observer-first implementation sequence
REPOSITORY ACCESS: full

RECOMMENDATION: conditional
ONE-SENTENCE RATIONALE: AIDR-0009 is sufficiently specified for human arbitration, but implementation should proceed only after Sam fixes the authority boundaries, incremental-test strategy, event semantics, and calibration gates identified below.

AIDR READINESS:
- Ready for arbitration: yes
- Missing evidence or decisions: No calibration evidence yet supports bid-based selection; the observer's deterministic observation definitions lack complete threshold and ordering rules; commentary has no settled citation grammar or privacy/redaction contract; `record` mode cost and failure behavior need explicit operator policy; the strict-xfail file-level markers prevent incremental implementation because one newly passing test becomes an XPASS failure until the entire file passes.
- Questions Sam must arbitrate: Whether `record` and `propose` comply with invariant 6; whether bidding is permitted to add cost and latency before configured dispatch; whether bid failures always fall back without affecting phase status; whether observer output may append an `observation` event or must remain wholly derived; whether deterministic observation thresholds and ordering are public stable contracts; whether commentary warrants a fourth role kind and what data it may see; whether `select` is categorically excluded from this decision and requires a new AIDR with numeric admission thresholds.

FINDINGS:
1. The observer-first direction has the cleanest dependency boundary. Its deterministic core can be implemented as a pure reducer in `harness/observer.py`, using existing `EventLog` records and `audit.verify_chain`, without touching routing, budgets, model selection, grants, approvals, or agent context.
2. The observer tests span three separable surfaces but are guarded by one file-level strict xfail: pure reduction and rendering, filesystem/chain handling, and runner/model commentary integration. This creates an all-at-once delivery hazard. The test organization must be arbitrated or changed before claiming a genuinely incremental first slice.
3. The first observer production path crosses `harness/observer.py`, `harness/audit.py`, `harness/events.py`, `harness/cli.py`, and eventually `harness/runner.py`. Optional commentary additionally crosses `harness/roles.py`, model adapters, routing configuration, quarantine, budgets, and reporting. Commentary should not ride with the deterministic slice.
4. Bidding has substantially greater coupling. It requires a new `harness/bidding.py`, an additive `bid` definition in `harness/schemas/v1/workflow.schema.json`, candidate cross-checks in `harness/schema.py`, dispatch interception and outcome emission in `harness/runner.py`, budget children, containment filters from `harness/cascade.py`, read-only tools from the registry, routing/config lookups, eval-runner support, trace metrics, live scorecards, audit/report surfaces, and documentation.
5. Several contracts need sharper semantics before code: whether an observer narrative is reproducible byte-for-byte despite generated timestamps; how duplicate/retried events are reduced; whether a broken chain permits writing a derived report; what constitutes a tier escalation when routes move sideways or change effort; how bid-call errors, partial candidate completion, and exhausted bid budgets map to events; and the minimum sample size and numeric thresholds required before any future `select` proposal.

FALSIFIERS:
- Most important existing falsifier: `test_record_mode_bids_every_candidate_and_dispatches_the_table_route` directly proves that `record` mode cannot alter configured routing, while `tests/test_aidr_0009_guards.py` protects byte-identical behavior for workflows without opt-in.
- Missing falsifier: A deterministic replay test should observe the same immutable event stream twice in separate processes and require byte-identical JSON and Markdown, stable observation ordering, no appended source event, and zero dependence on wall-clock time, filesystem enumeration order, or model configuration.
- Condition that would reverse your recommendation: Oppose if arbitration permits observer output into agent, verifier, approval, halt, routing, or arbitration context, or permits bid predictions to affect dispatch before a separately approved, quantitatively gated `select` decision.

IMPLEMENTATION MAP:
- First safe slice: Implement only deterministic offline observation for an existing run: verify `events.jsonl`, reduce it into stable cited JSON and Markdown, refuse narration on chain failure, and expose `harnessie observe RUN_ID`; exclude `--follow`, automatic `run --observe`, commentary, bidding, new role kinds, and source-log mutation.
- Required production modules: First slice requires new `harness/observer.py`, command registration and path resolution in `harness/cli.py`, and reuse of `harness/audit.py` plus `harness/events.py`; later automatic observation requires `harness/runner.py`; bidding later requires new `harness/bidding.py`, `harness/runner.py`, `harness/schemas/v1/workflow.schema.json`, `harness/schema.py`, `harness/cascade.py`, `harness/routing.py`, `harness/tools/registry.py`, `harness/budget.py`, `harness/trace_eval.py`, `harness/evals.py`, `harness/live_scorecard.py`, audit/report code, and generated documentation sources.
- Tests that should turn from strict xfail to passing: For the first slice, the deterministic and filesystem tests in `tests/test_observer.py`: stable narrative shape, crashed-run status, earned and unearned escalation, scope drift, unparseable output, provider monoculture, bid-origin reduction, pre-mortem observations, broken-chain refusal, and idempotent output location. Because the current marker covers the whole file, either implement all observer tests atomically or first separate deterministic, runner, and commentary contracts under independently removable strict-xfail markers.
- Work explicitly deferred: Runner-level `--observe`, `--follow`, observer event journaling, optional model commentary, the `observer` role kind, plugin observers, all bid modes, bid scorecards, calibration-backed proposals, and every form of `select`.
- Main regression risk: An ostensibly read-only observer could accidentally become participant state through appended events, agent-context injection, governance timeline inclusion, nondeterministic reports, or automatic runner failure propagation; bidding later risks silently changing dispatch through candidate filtering, budget handling, or fallback logic even in `record` mode.

CROSS-ENGINE HANDOFF:
- One claim another engine should challenge: The deterministic observer can be treated as an ordinary non-governance feature even though its summaries may become de facto operator evidence and therefore require stronger schema stability, redaction, and provenance guarantees.
- One question another engine should answer: Should AIDR-0009 arbitrate only deterministic observation plus bid instrumentation, leaving commentary, `propose`, and `select` to separate decisions, or is the combined decision still narrow enough to preserve meaningful human control?
- Evidence Sam should compare across all four reports: Agreement on the non-participant observer boundary, the exact invariant-6 interpretation for `record` and `propose`, the minimum calibration evidence and thresholds required before `select`, unresolved event/schema semantics, hidden implementation coupling, and whether every engine independently selects deterministic observation as the first safe build slice.

STOP CONDITION:
I made no production-code or decision-record changes, invoked no external models, and ran no live-provider tests while producing this review.
