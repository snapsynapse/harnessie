# Harnessie INTENT

Tier: public tool under Snap Synapse LLC (launched 2026-07-07: repo public, site live, 0.6.0 on PyPI).
Canonical home: https://harnessie.com/

Entity decision (2026-07-06, Sam): Harnessie releases as a Snap Synapse LLC project, not a PAICE.work PBC portfolio component. Rationale: Snap Synapse is the tools-people-use brand and the repo already lives at snapsynapse/harnessie; a PAICE release would frame it inward as a standards reference implementation, while the strategic value runs the other way. Harnessie is a distribution vector FOR the PAICE specs: it enforces Turnfile and AIDR lessons in code and credits them on its public surfaces, so adoption of the tool pulls discovery of the standards. The corresponding portfolio-level line lives in paice-foundation/INTENT.md.

Positioning (2026-07-06, Sam): the public claim is "the safest and easiest first AI harness for people". Two audiences, ordered: developers are the GitHub audience and get the falsifiable version first (the security model, fail-closed invariants, independent verification, the threat model in SECURITY.md); the non-developer on-ramp is the design story inside that, not an unverifiable headline. Every safety superlative on a public surface must point at a checkable artifact.

This document follows the portfolio Repo Standards INTENT.md section template. Harnessie is not yet a portfolio component; this INTENT is pre-applied so a later promotion is clean.

## 1. What this is

Harnessie is a brain-agnostic multi-agent harness: an orchestrator that decomposes goals, cheap swappable worker models that execute, and independent verifiers that gate every result. It ships as a Python library and CLI with verification gates, consent-based orchestration (task packets are offers), per-agent file ownership lanes, adversarial contested phases with human-only arbitration, cost routing, file-based memory, a resumable run journal, a hash-chained audit log, and a layered prompt-injection defense. The model is a configuration seam, not a code dependency.

## 2. Why it exists

Most AI products fail at the harness layer, not the model: unclear tool boundaries, no approval policy, brittle state, no evaluation loop. Harnessie encodes those as first-class primitives so a cheap or open-source model under a strong harness can approach frontier-model results, and a frontier model under the same harness is kept honest. It was built from an operating charter to match or exceed frontier behavior while remaining brain-swappable.

## 3. Design invariants

1. Brain-agnostic seam: swapping the model is a `config/models.yaml` edit, never a harness code change.
2. Guarantees live in code, at the registry, loop, and OS layer, not in prompts a model can ignore.
3. Fail closed everywhere: an unenforceable control is refused, not skipped (an unverifiable verdict, a missing sandbox, a denied approval all halt).
4. Nothing ships on an agent's say-so: every side-effecting phase passes deterministic checks plus an independent fresh-context verifier.
5. Silence is never success: every loop ends in an enumerated stop condition.
6. Routing is config, not model self-assessment; escalation is earned by gate failures, not predicted.
7. Memory is small, scoped, and provenance-bearing.
8. Task packets are offers: consent precedes side effects, a decline is signal not insubordination, and declines never escalate the route.
9. Agents own their files, never each other's; the ownership ledger lives outside any agent's reach, and the operator is root owner of everything.
10. Disagreement is evidence, never authority: contested decisions are preserved as records and arbitrated only by a human; nothing synthesizes dissent away.
11. Eval-first change discipline: a governance mechanic without a red-then-green scenario pair does not merge.
12. The composite includes the human: operator actions (approvals, arbitrations) are journaled into the same tamper-evident audit stream as agent actions, and memory provenance is stamped by the harness, never claimed by an agent.
13. Operator seat versus arbiter seat: the operator seat (orchestration, approvals) may be occupied by a delegated agent acting on a human's instruction; the arbiter seat may not. A contested decision escalates to a human even when an agent holds the operator seat. The audit stream records operator-of-record (human or delegated-agent) and arbiter-of-record (always human) as distinct fields, so the timeline can prove who held each seat. This is what makes the most-delegated run mode safe to offer: the easiest mode still cannot decide a contested question for the operator.

## 4. Scope boundaries

In scope: the harness runtime (models, tools, loop, verify, routing, memory, state, roles, quarantine, sandbox, runner, CLI), role prompts, workflow definitions, the security layers, and their tests.

Out of scope: being an open standard or spec; a hosted surface or web UI; model training or fine-tuning; secrets management beyond env-var hygiene and the mechanical guards; Windows-native sandboxing (bare Windows fails closed; WSL2 presents as Linux and uses the Linux backends shipped in 0.4).

## 5. Conformance philosophy

N/A because harnessie is a tool, not an open standard. It makes no external conformance claims and has no verifier-anywhere model. Internal correctness is asserted by the test suite and the threat model in `SECURITY.md`.

## 6. Admission criteria for changes

N/A as a formal open-spec gate. The working change discipline is: the full test suite stays green; no documented security invariant (`SECURITY.md`) is weakened without a recorded rationale; the affected docs and `CHANGELOG.md` are updated in the same change; shipped configs and workflows still parse (`tests/test_repo_configs.py`).

## 7. Relationships to other PAICE standards

Harnessie is not a PAICE portfolio component and will not become one: it releases under Snap Synapse LLC (see the entity decision above), relating to PAICE standards by adoption, not ownership. It is built on the Aggregated Intelligence tenets, ratified as canon 2026-07-06 (eight tenets; the tenet-to-mechanism mapping is `GOVERNANCE.md` §7). Its multi-agent structure is modeled on the Safe Agentic Workflow (SAW) patterns. As of v0.2 it deliberately imports, as harness-enforced mechanics, the shipped lessons of two portfolio standards: Turnfile (consent-based coordination, ownership lanes, authority order, bounded rebuttal, eval-first change loop) and AIDR (record lifecycle, preserved dissent, human-only arbitration, structurally earned claims; the repo dogfoods AIDR in `decisions/`). These are lesson imports and format alignments, not conformance claims — Harnessie asserts no Turnfile or AIDR conformance. Graceful Boundaries is now adopted for the agent refusal surface, transport-adapted: every denial carries the GB Level 1 `{error, detail, why}` grammar (plus a `boundary` tag), the action-refusal codes match GB's Action Boundaries vocabulary (spec Appendix C.4), and SC-16 (guidance-is-untrusted-data) holds both directions; achieved status, the transport N/A for the HTTP-shaped Levels 2 through 4, and the named gaps are cited in `GOVERNANCE.md` §8 and proven by `tests/test_graceful_boundaries.py`. GuideCheck is adopted as of v0.6.0 at confirmed Level 4: the shipped `assistant-guide.txt` is a conforming profile served byte-identically at `docs/.well-known/assistant-guide.txt` with a sidecar provenance manifest and an independent DNS TXT anchor (`_assistant-guide.harnessie.com`, registrar control plane); the hosted fetching verifier (guidecheck-hosted 0.7.0) reports achieved level 4 with zero blocking findings, and guide-artifact sync is enforced by `tests/test_guide_artifacts.py`.

## 8. Exceptions to Repo Standards

- Tier is personal-utility (private, not in `portfolio.yaml`), so hosted, open-spec, agent-facing, and commercial matrix rows are N/A. Trajectory is public/portfolio; promotion will trigger those rows via `repo-standards-audit` plus `repo-polish`.
- `.claude/` is gitignored as a full directory per the all-tier rule. Consequence recorded for maintainers: the repo is dogfooded under Claude Code via a local, untracked `.claude/` (worker and verifier subagent wrappers, a `/run-workflow` command, and a PostToolUse pytest hook). The canonical, tracked source for those role prompts is `agents/`; the CLI (`python3 -m harness.cli`) is the primary interface and needs no `.claude/`.
- `INTENT.md` is present although the personal-utility tier does not require it, pre-applied for the public/portfolio trajectory.
- Recorded exception (2026-07-06, operator default): the tracked `assistant-guide.txt` would classify this repo agent-facing under portfolio Repo Standards v0.7; the repo remains personal-utility tier until public promotion, at which point annotated tags, `RELEASE_CHECKLIST.md`, and CI-gate-before-tag are adopted via the standard promotion path. Until then, versions are commits-not-releases by deliberate choice.
- Recorded exception (2026-07-06, operator default): the Turnfile adoption row ("repo runs multi-agent collaboration sessions") is not adopted. Harnessie is one-process orchestration under a single operator, not cross-runtime peer sessions; Turnfile interop is declared out of scope in `GOVERNANCE.md` and would be a deliberate 0.5-era decision, not a conformance default.
- `docs/` is the live public served tree (https://harnessie.com/, GitHub Pages from `main` `/docs` per the portfolio Repo Standards docs/-publish rule): the landing page, the generated HTML doc pages (`scripts/build_docs_html.py`), and the `.well-known/` GuideCheck trust pair. Internal engineering and planning docs (ARCHITECTURE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN, PROMPTS, session-url-log, source-verification.json) live at the repo root and are not served, though the repo itself is public.

## 9. Changelog

- 2026-07-10 - Operating-modes ladder and operator/arbiter distinction recorded (Sam). Product-and-education decision: Harnessie is an educational on-ramp as much as a harness, so the ease-versus-safety trade-off is made explicit as a named ladder of run modes (Watch, Narrate, Approve-every-step, Approve-on-exception, Agent-mediated), each stating in plain language what is real, what is not, and which risk the operator is accepting before it runs. The safety axis is human eyes-on-code: the rungs are a psychologically safe staircase toward the code newcomers fear, and the approval gate is the mechanism, not a slogan. Design invariant 13 added (operator-of-record may be a delegated agent; arbiter-of-record is always human), which is the property that makes the most-delegated rung safe to offer. The full rung table is a public surface at `docs/ladder.md` (served as `/ladder.html`); most machinery already exists (mock run, `--approve-interactive`, `--approval-policy`), the honest gaps are the Narrate rung, the two audit fields, and the per-rung trade-off banner. Dogfood provenance: the ladder was decided while running `workflows/contested-decision-3panel.yaml` on this session's launch-post choice under an all-Ollama brain swap; the panel split, halted at `needs_arbitration`, and Sam arbitrated (record `runs/20260710-083859-KP0C8J/decisions/DR-decide.md`, earned claims dissent-preserved and human-arbitrated). Note surfaced by that run: the `independent-positions` claim keys on distinct provider strings, so routing three different models all through `openai-compat` did not earn it though the brains were genuinely distinct.
- 2026-07-07 - License decision recorded (Sam): relicensed MIT to Apache-2.0 pre-public, copyright Snap Synapse LLC; NOTICE added with trademark and PAICE.work PBC carveouts (specs are adopted and credited, never owned; PBC-originated code requires an explicit written grant recorded in NOTICE before vendoring). Rationale: patent grant and trademark clause fit the trust-infrastructure positioning; the switch is free while the author list is one.
- 2026-07-06 - Entity and positioning decision recorded (Sam): public release under Snap Synapse LLC; PAICE relationship is adoption-and-credit, not ownership; safety claims must be falsifiable and developer-checkable. §7 updated for the tenets ratification. README gains audience framing and a standards-credit section; ROADMAP gains the 0.6.0 first-harness readiness milestone (launch gate).
- 2026-07-06 - v0.3.2 refusal and identifier hardening patch: structured refusal grammar now covers tool denial surfaces with audited `refusal` events; run IDs, change requests, and generated decision records carry human-readable checked refs; 0.4 portability remains the next milestone.
- 2026-07-06 - v0.3.0 aggregated-intelligence release (operator direction): operator actions enter the hash-chained audit stream (approval events, arbitration as operator_action, `approve_tools:` recorded pre-approval); memory becomes substrate (verified/verify_by provenance, save_fact/expire_fact tools, archival-only disposal); `workflows/memory-triage.yaml` ships the maintenance-agent pattern under enforcement. Invariant 12 added. Direction record `decisions/AIDR-0002` (open). Portability displaced a second time to 0.4.0; roadmap flags a third displacement for operator arbitration.
- 2026-07-06 - v0.2.0 governance layer: adversarial collaboration and evals promoted to foundational principles (operator direction). Consent-based orchestration, ownership lanes, contested phases with human-only arbitration, hash-chained audit; design in `GOVERNANCE.md`, direction record `decisions/AIDR-0001` (open, awaiting arbitration by Sam). Design invariants 8-11 added; §7 updated to record the Turnfile/AIDR lesson imports. Portability milestone displaced to 0.3.0.
- 2026-07-06 - Initial INTENT. Repo-standards conformance pass before the first commit: baseline `.gitignore`, `.claude/` untracked per the all-tier rule, `INTENT.md` added. Harness at v0.1.0 (see `CHANGELOG.md`).
