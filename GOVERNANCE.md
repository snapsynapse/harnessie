# Harnessie governance: consent, ownership, contest, audit

This document specifies the governance layer added in v0.2.0. It imports the tested lessons of two shipped specs — Turnfile (consent-based peer coordination, ownership lanes, maintainer authority) and AIDR (independent positions, preserved dissent, human-only arbitration, structurally earned claims) — and re-expresses them as harness-enforced mechanics rather than protocol conventions. Where those specs rely on agents following rules, Harnessie enforces the same rules in code at the registry, loop, and runner layers, per the standing design invariant: guarantees live in code, not prompts.

Vocabulary is deliberately aligned with the source specs (Turnfile `DEFINITIONS.md`, AIDR `SPEC.md`) so a future integration is a format mapping, not a redesign.

## 1. Authority order

Adapted from Turnfile SPEC §3. Lower entries never override higher ones.

1. OS sandbox and harness code invariants (fail closed; no role prompt can opt out).
2. Operator decisions: arbitration text, approvals, `OWNERSHIP.yaml` lane declarations, config.
3. Workflow declarations: consent requirements, lanes, arbitration mode, deny_tools, budgets.
4. Recorded state: the ownership ledger, granted consents, journaled gate verdicts.
5. Agent output: proposals, positions, objections, reports.

Agent agreement is never approval. Convergence among agents is evidence the operator may rely on; it is not authority (AIDR: "agreement is evidence, never authority").

## 2. Consent-based orchestration

The orchestrator proposes; workers consent. A task packet is an offer, not a command.

Mechanics (enforced in `harness/loop.py` + `harness/tools/registry.py`):

- A consent-gated phase starts with side-effecting tools (effects `write` and `execute`) locked. Read tools stay available: informed consent requires the agent can inspect the workspace before agreeing.
- `accept_task(note?)` unlocks side effects for the remainder of the loop. Emits `consent_granted` with the note.
- `decline_task(reason, counter_proposal?)` ends the loop with the dedicated stop condition `declined`. Emits `consent_declined`. Declining is a first-class, non-punished outcome — the Turnfile apply-or-counter rule: accept, accept-with-amendments, counter, or block with reason. Silent compliance and silent refusal are both excluded.
- A side-effecting tool call before `accept_task` is refused at dispatch with an explanatory error; the refusal is an observation the model sees, and it is logged.
- `task_complete` stays legal without consent: a task that turned out to need no side effects (pure analysis, or "impossible as specified, here is why") does not require accepting the offer.

Gate behavior on `declined` (`harness/verify.py`):

- If the decline carries a `counter_proposal`, the gate reformulates the task once, incorporating the counter text verbatim as operator-visible context, and re-offers. One counter round, mirroring Turnfile's bounded rebuttal default.
- A second decline, or a decline without counter-proposal, returns `needs_human`. The route is never escalated on decline: escalation is for capability failures, not for disagreement. Punishing refusal with a bigger model teaches the system to steamroll objections.

Workflow surface: worker phases default `consent: true`. A phase may declare `consent: false` for the degenerate single-agent case; the default fails closed.

## 3. Ownership lanes: agents own their files, not each other's

Imported from Turnfile `OWNERSHIP.yaml` + PRD-033 (skill-ownership integrity guard), re-enforced at the tool layer instead of a pre-commit hook.

Three lane kinds, declared in `OWNERSHIP.yaml` at the project root (outside the workspace jail, therefore structurally unwritable by any agent):

- `agent` lanes: glob → agent name. Only that agent may write matching paths.
- `collaborative` lanes: glob list. Any worker may write; co-edits are events.
- `operator` lanes: glob list. No agent may write, ever. The ledger, config, and role prompts are implicitly operator-owned because they live outside the workspace; this lane exists for operator-reserved paths inside it.

Unlisted paths follow first-writer-owns: the first agent to create a file becomes its owner, recorded in the ledger (`files:` section of `OWNERSHIP.yaml`, auto-maintained) and emitted as `ownership_claimed`. Operator lane declarations always override auto-claims — the human is the root owner of everything and can reassign any path by editing the file.

Enforcement (in `write_file` dispatch, fail closed):

- write to another agent's file → refused with the owner's name and the remedy: call `request_change`.
- write to an operator lane → refused, no remedy offered to the agent.
- `request_change(path, description)` records a change request (journal + event + run report). It does not grant anything. Resolution is routing work to the owning agent or an operator lane edit — a decision above the requesting agent's authority (§1).

Honest limit (recorded per the AIDR practice of stating what the runner actually guarantees): ownership is enforced at the `write_file` tool. An allowlisted interpreter (worker `python3`) can still write inside the workspace without a per-file check; the OS sandbox confines writes to the workspace as a whole, not per-lane. Interpreter writes are therefore visible in events and caught by verifiers and audit, not blocked per-file. Full per-lane confinement would need per-phase sandbox profiles (roadmap).

## 4. Adversarial collaboration: positions, objections, arbitration

The v0.1 verifier gate is retained as the workhorse adversarial check (independent fresh-context verification of every side-effecting phase). v0.2 adds a second, heavier instrument for decisions rather than artifacts: the contested phase, modeled on AIDR's record lifecycle and Turnfile's conflict ladder.

Workflow surface:

```yaml
- name: choose-storage
  mode: adversarial
  task: |
    Should the cache layer use SQLite or flat JSONL? ...
  positions:
    - agent: analyst          # role prompts; each runs read-only
      task_class: plan        # may route to different tiers = different brains
    - agent: skeptic
      task_class: verify
  rebuttal_rounds: 1          # Turnfile PRD-021 bound
  arbitration: convergence    # or "human": always halt for the operator
```

Protocol, executed by the runner:

1. Position round. Each position agent receives the identical brief in an isolated context with read-only grants (side effects denied at schema and dispatch — a stance needs no hands). Its `task_complete` report must end with a JSON stance object `{"stance": "recommend|oppose|alternative|abstain", "summary": "..."}`, parsed with the same last-object-wins, fail-closed discipline as verifier verdicts. An unparseable stance is recorded as dissent, not dropped: fail closed means uncertainty forces arbitration rather than silently converging.
2. Objection round(s). Each agent sees the other positions and returns objections or an explicit no-new-objection marker (Turnfile convergence rule). Bounded by `rebuttal_rounds` (default 1). Objections are never deleted; every round is appended to the record.
3. Assembly. The harness (never an agent) assembles a decision record at `runs/<run_id>/decisions/DR-<n>-<slug>.md`, AIDR-shaped: frontmatter (id, title, status, date, arbiter = operator), Context, Question, Positions with per-position metadata (agent, model_id, tier, stance, summary), Objections, empty Arbitration section.
4. Structural lint + earned claims, computed by the harness and stamped into the record:
   - `independent-positions`: two or more positions with distinct providers recorded before arbitration (a monoculture can only echo with variance; same-provider model variants do not earn the claim).
   - `dissent-preserved`: an oppose/alternative stance or objection exists and the Arbitration section is complete.
   - `human-arbitrated`: status `arbitrated`, arbitration metadata complete.
   Claims are structural only; whether the arbitration prose genuinely answers each objection is the human's responsibility, exactly as in AIDR — lint checks form, never judgment.
5. Outcome:
   - Converged (`arbitration: convergence`, all stances `recommend`, zero open objections): the phase passes; the record ships with status `open` and the convergence noted. Audit trail exists even for uncontested decisions.
   - Contested, or `arbitration: human`: the phase halts with the new status `needs_arbitration` (a `needs_human` variant carrying the record path). No later phase runs on an unarbitrated contested decision.

Arbitration is human-only, mechanically: no harness code path writes the Arbitration section, and no agent can reach the record (it lives under `runs/`, outside the workspace). The operator edits the record in their own words, flips `status: arbitrated`, and re-runs. On resume the runner re-lints the record instead of re-running the phase: `human-arbitrated` earned → the phase passes and the arbitration decision text flows to later phases as the phase report. Anything else stays halted.

Independence statement (recorded in every decision record, after the AIDR recipe practice of stating what the runner actually guaranteed): positions run in isolated model contexts within one harness process; isolation is code-enforced for context and tools, behavioral for everything a shared filesystem could leak; the hash-chained events log is the evidence it held.

## 5. Audit: tamper-evident log, replayable governance

Every governance action already flows through `events.jsonl`. v0.2 makes that log tamper-evident and gives the operator a single verb to interrogate it.

- Hash chain: each event carries `seq` and `prev` — the SHA-256 of the previous event's exact serialized line (`genesis` for the first). Any post-hoc edit, deletion, or reorder breaks every subsequent link.
- `harnessie audit <run_id>`: verifies the chain end to end, then renders the governance timeline — consents granted/declined, ownership claims and denials, change requests, injection flags, gate verdicts, approval grants and denials, operator actions (arbitration detected on resume), memory facts saved and expired, and decision records with their earned claims and arbitration status. One composite timeline of agent and human actions. Exit 0 clean, exit 1 broken chain, exit 2 run not found.
- Honest limit: a hash chain is tamper-evident, not tamper-proof — an attacker who can rewrite the whole file can rewrite the whole chain. The defended asset is auditability against silent partial edits, which is the realistic failure (an agent or tool quietly appending or an operator "tidying" history). Anchoring the chain head externally (git commit, transparency log) is the operator's escrow decision, not the harness's.

## 6. Evals as the change discipline

Imported from Turnfile PRD-006's eight-step loop (proposer authors red evals; implementation happens against them; review follows) and applied to Harnessie's own development as a standing rule:

- Every governance mechanic in this document lands with eval scenarios in `evals/` written before or with the implementation, in the standing golden / risky / recovery taxonomy:
  - golden: consent granted → work proceeds; in-lane write succeeds; unanimous positions converge and the record carries `independent-positions`.
  - risky: side effect before consent → refused; cross-owner write → refused; operator-lane write → refused; unparseable stance → forces arbitration; edited events log → audit exits 1.
  - recovery: decline with counter → one re-offer → accept → proceed; decline twice → needs_human with no route escalation; contested record → needs_arbitration → human arbitrates → resume passes phase.
- A governance feature without a red-then-green scenario pair does not merge. The eval suite is the conformance surface: like Turnfile's no-oracle principle, anyone can verify the claims by running the validators against plain files — `python3 -m harness.cli eval`, no hosted service, no trust in the author.

## 7. Aggregated-intelligence tenets (v0.3)

Harnessie's operator runs on a standing frame: the unit of value is Aggregated Intelligence — humans, agents, and organizations as one composite, never human-versus-AI. The canonical statement is a privately maintained Aggregated Intelligence Tenets document (drafted 2026-07-04, ratified by the operator 2026-07-06 after independent multi-provider peer review; two of its claims remain explicitly provisional). Its eight tenets, against what this harness enforces:

1. Intelligence lives in the arrangement, not the node → the founding v0.1 thesis: the harness structure carries the quality floor, the model only raises the ceiling.
2. Disagreement is the engine, not the exhaust → contested phases; objections are appended, never deleted; a decline is signal.
3. Independence before influence → the position round runs in isolated contexts BEFORE the objection round; the `independent-positions` claim requires distinct providers, because a monoculture can only echo with variance.
4. Consensus is evidence, never authority → design invariant 10; convergence is recorded, arbitration is not inferred from agreement.
5. Authority is human because accountability is human → arbitration is human-only, mechanically; `needs_arbitration` halts the run.
6. The record is the relationship → decision records plus the hash-chained events log: who proposed, who objected, who decided, by what right.
7. The standard is a commons or it is a leash → the brain is a config seam; no code names a required provider; records are plain markdown readable without this harness.
8. Rules are earned, not decreed → the eval-first discipline plus an AIDR record per direction change; a mechanic without a red-then-green scenario pair does not merge.

The tenets document also names a dual failure mode (a provisional claim, deliberately not ratified as canon): hallucinated completion — the agent confidently reporting done — and premature convergence — the group agreeing before dissent surfaced. Harnessie is deliberately the composition that covers both: mechanical verification below (gates), structured dissent above (contested phases), one accountable human on top (arbitration).

The operational mapping:

| Tenet | Mechanic |
|---|---|
| The composite includes the human — the operator is a participant, not an external reviewer | Operator actions enter the SAME hash-chained audit stream as agent actions: `approval_granted`/`approval_denied` events (with their source), and `operator_action` when a resume detects human arbitration. An audit renders one composite timeline, not an agent log with invisible human edits. |
| Substrate compounds — durable, provenance-bearing artifacts are the highest-leverage asset | Project memory becomes first-class substrate: facts carry `verified` and `verify_by` dates plus source-run provenance, and agents maintain them through `save_fact`/`expire_fact` tools instead of ad-hoc writes. |
| Drift is the primary failure mode | Staleness is detected, not assumed away: facts past `verify_by` are surfaced by the memory-triage workflow every cadence, and the fix is re-verification or archival — never silently trusting old context. |
| Nothing is deleted, authority is explicit | `expire_fact` archives (moves to `memory/archive/`, index updated); deletion does not exist as an agent capability. Expiry requires approval — headless runs propose, the operator disposes, and a workflow's `approve_tools:` key is the operator's recorded, journaled pre-approval. |
| Traction is verified change, not activity | The eval scorecards are the measure: a mechanic exists when its red-then-green scenarios exist, and a brain earns a tier by passing the same scorecard (0.4). |
| The Constraint Rule: a composite is bounded by its weakest vector — minimum, never average | A run's assurance is the minimum of its control surfaces, and reporting must name the constraining control. This already holds mechanically (one `needs_human`/`needs_arbitration` halts the workflow; a missing sandbox fails shell closed regardless of every other control being green; a broken audit chain fails the audit regardless of clean gate verdicts); 0.4's live scorecard should surface it explicitly — per-run assurance = min(consent, ownership, verification, audit), constraining control named. |

The memory-triage workflow (`workflows/memory-triage.yaml`) is the working expression: a scheduled maintenance agent — the same job as the operator's vault triage agent — running under these controls, so "should not delete without approval" becomes "cannot."

## 8. What this is not

- Not a peer-to-peer protocol: Harnessie remains one orchestrator, one process. Turnfile's multi-runtime mailbox/worklog machinery is out of scope; if Harnessie sessions ever need to interoperate with other runtimes, that is a Turnfile adoption decision, not a reimplementation.
- Not synthesis: contested decisions are never merged into a compromise by a model. The record preserves the disagreement; the human resolves it (AIDR WHY.md).
- Not workflow-author protection: an operator who writes a malicious workflow owns the outcome. The governance layer protects the operator's authority over agents and agents' lanes from each other, not the system from its owner.
