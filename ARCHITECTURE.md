# Harnessie architecture

A brain-agnostic multi-agent harness: one orchestrator, cheap swappable workers, independent verifiers, verification gates between every phase, file-based memory with provenance, and cost routing as declared config. Built so that the harness structure, not the frontier model, carries the quality floor; upgrading the brain raises the ceiling.

Every external source cited in this document was fetched and verified real on 2026-07-06 by a 24-agent verification workflow before being relied on (raw verdicts: [source-verification.json](source-verification.json)). Two sources could not be verified either way (a Facebook group post and one YouTube video whose verification agents died mid-run); nothing in this design depends on them.

## 1. Harness shape and the multi-agent justification

Shape: workflow orchestrator with a code-agent execution layer (hybrid). Work enters as a goal, runs through declared phases, and every side-effecting phase exits through a verification gate.

Multi-agent is a deliberate, argued choice, not a default. The three roles exist because each needs constraints incompatible with the others:

| Role | May do | Must never do | Why separate |
|---|---|---|---|
| Orchestrator | read, decompose, route, integrate | write files, run commands | planning quality must not be spent on execution; no side effects means its mistakes are cheap |
| Worker | read, write, allowlisted shell inside workspace | leave the workspace, run non-allowlisted commands, self-certify done | does the work; the role most likely to be a weak model, so most fenced |
| Verifier | read, test execution | modify anything, see worker reasoning | self-verification is structurally biased; fresh-context independent verification outperforms self-critique (confirmed by Anthropic's official Fable 5 guidance) |

Where one model can hold the whole job coherently, run the single-agent degenerate case: one workflow phase, no verifier. The harness does not punish small jobs.

## 2. Subsystem map

One module per boundary:

| Subsystem | Module | Responsibility |
|---|---|---|
| Entrypoint | `harness/cli.py` | run, resume, report |
| Orchestration | `harness/runner.py` | executes `workflows/*.yaml` phase by phase through gates |
| Model interface | `harness/models/` | one `complete()` seam; Anthropic, OpenAI-compatible, mock adapters |
| Capability registry | `harness/tools/` | tool schemas, effects classes, role grants, approval policy; enforced at dispatch |
| Agent loop | `harness/loop.py` | context, model call, permission-gated tool execution, enumerated stop conditions |
| Verification | `harness/verify.py` | deterministic checks, verifier agent, retry/reformulate/escalate ladder |
| Routing and budget | `harness/routing.py` | task_class to (tier, effort); escalation; hard cost ceilings |
| Roles | `harness/roles.py` | prompt files plus machine-owned boundary blocks assembled per role |
| Quarantine | `harness/quarantine.py` | injection ingress filter, invisible-char stripping, secret detection/redaction |
| Sandbox | `harness/sandbox.py` | OS confinement of child commands (workspace-only writes, network deny), fail closed |
| State | `harness/state.py` | append-only journal of phase results; resume skips verified successes only |
| Memory and proofs | `harness/memory.py` | provenance-carrying fact files plus per-run proof artifacts |
| Observability | `harness/events.py` | every subsystem emits to `runs/<id>/events.jsonl`; humans can replay any run |

## 3. The loops

Inner loop (`AgentLoop.run`), per role invocation:

```text
assemble context (role prompt + boundary block + memory index + task)
-> model.complete(messages, tools-for-this-role, effort)
-> if tool calls: permission check -> execute -> append observation -> repeat
-> stop only on an enumerated condition:
   complete | max_steps | budget | stuck | model_error | no_action | refusal
```

Silence is never success: `task_complete(report)` is the only success path, and every other exit is a named diagnosis the gate can act on. Tool errors return to the model as observations so it can self-correct; identical repeated failures trip the stuck detector; provider refusals surface as `refusal` and go to the gate's ladder or the operator, never a silent same-prompt retry (aligned with the documented two-stage safety pipeline and fallback behavior of the Claude 5 family).

Gate loop (`VerificationGate.run`), wrapping every worker phase:

```text
attempt N: worker runs
-> deterministic checks (tests, lint, schema); red checks block the model verifier
-> verifier agent judges artifacts vs acceptance criteria (fresh context, fail closed)
-> pass: phase done, proofs on disk
-> fail: task REFORMULATED with the concrete failure evidence
         attempt 3+: route escalated (effort up, then tier up)
         ladder exhausted: needs_human, workflow halts
```

Outer loop (`WorkflowRunner.run_workflow`): declared phases, journaled results, resume-on-crash, halt on `needs_human` so later phases never build on unverified work.

## 4. Memory and data layer

Four stores, all files, all inspectable:

- Facts (`memory/facts/*.md`): one fact per file with frontmatter provenance (type, source, date). `memory/MEMORY.md` is a one-line-per-fact index, injected into orchestrator phases only; agents read fact bodies on demand with their read tools. This is the official file-based memory pattern (one lesson per file, one-line summary, update rather than duplicate) and it is deliberately small: memory without provenance and expiry is how stale context starts dominating runs.
- Journal (`runs/<id>/journal.jsonl`): append-only ledger of phase results; the resume mechanism. Resume skips only phases journaled as passed; a needs_human phase re-runs rather than silently counting as done.
- Events (`runs/<id>/events.jsonl`): the full audit trail: every role start with its route, model turn metadata, tool result, check outcome, gate verdict, and cost. `harnessie report <run_id>` renders journal plus events.
- Proofs (`runs/<id>/proofs/`): check outputs per attempt, saved pass or fail. A task is done when a proof exists and a verifier signed it, not when an agent said so.

Mapped to the AI-OS framing (Context, Connections, Capabilities, Cadence): Context is memory index plus phase inputs; Connections are the tool registry and model adapters; Capabilities are workflows and role prompts; Cadence is the runner plus resumable journal (cron or CI can own the schedule).

Context hygiene rules: workers get exactly the inputs their task packet names, never the orchestrator's full context or the memory index; verifiers get artifacts and criteria, never worker transcripts; agent transcripts are never re-injected into later prompts, only phase reports flow forward. Prompt assembly keeps the stable prefix (role prompt, then machine-appended boundaries) byte-identical ahead of volatile content so provider prompt caching pays.

## 5. Routing, effort, and cost control

Effort is the primary quality/latency/cost dial (official levels low, medium, high, xhigh, max; sent as `output_config.effort` on Claude 5, `reasoning_effort` on OpenAI-compatible endpoints, prompt-level depth statement where unsupported). Routing policy in one config table (`config/models.yaml`):

- Frontier tokens go where they compound: decomposition (plan), synthesis (integrate), and the final gate (verify_final at xhigh).
- Bulk execution runs on mid or cheap tiers; mechanical work on local open-source brains.
- task_class is declared by the workflow author, never self-assessed by the model; escalation is earned by gate failures (evidence), not predicted.
- Budgets are hard ceilings enforced in code before every model call; an exhausted budget is a stop condition, not a warning.

## 6. Safety and verification layers

Defense in depth, ordered from cheap to expensive:

1. Structural permissions: tools are granted per role; the model never sees tools it cannot call, and dispatch re-checks anyway. Guarantees live in code, not prompts.
2. Workspace jail and per-role shell allowlists: filesystem path escapes rejected; only enumerated commands run, and verifiers lose interpreters and git so their read-only boundary is allowlist-enforced, not prompt-hoped; shell arguments containing absolute paths or `..` are rejected; approval-required tools fail closed under the default handler (headless runs cannot mutate silently). Honest limit: a worker's python3 or a verifier's pytest still executes code the argument jail cannot inspect; full containment is the OS-sandbox step in the implementation plan, and until then the events log records every call.
3. Deterministic gates: tests, linters, schema checks run under harness control on every attempt.
4. Independent verifier agents: fresh context, artifacts-only, fail-closed verdict parsing, falsification posture.
5. Escalation to human: `needs_human` halts the workflow; irreversible actions and scope changes are operator decisions by design.
6. Machine-owned boundary blocks: the harness appends role boundaries after the prompt file, so a prompt edit or an injected instruction cannot remove limits.

Quarantine rule for untrusted input (imported from the dynamic-workflows and prompt-injection literature): agents that read untrusted content (scraped pages, tickets, third-party docs) should hold read-only grants; a separate agent acts on the extracted, verified findings. The registry's per-role grants express this directly, and the mechanical layers below enforce it.

Prompt-injection defense is layered so that defeating one control still leaves the others (full model and operator checklist: [SECURITY.md](SECURITY.md)): (1) an ingress filter (`harness/quarantine.py`) runs at dispatch on any tool marked `quarantine=True` (read_file today), flagging directive phrasings and hidden/bidi Unicode, stripping invisibles, and fencing flagged content as data-not-instructions; (2) a loop tripwire re-asserts the boundary in-band and logs an `injection_flag` event when a result is flagged; (3) per-phase `deny_tools` in the workflow YAML drops tools a content-reading phase does not need, enforced at both schema and dispatch; (4) an OS sandbox (`harness/sandbox.py`, macOS Seatbelt via `sandbox-exec`) confines every child command's writes to the workspace and denies network by default, closing the interpreter escape that the allowlist and argument jail only narrow, and failing closed where no backend exists; (5) secret guards scrub child-process environments, redact credential-shaped strings from shell output, and refuse credential-bearing file writes; (6) the independent verifier catches behavior-level corruption; (7) needs_human and approval gates put a human on anything reasoning survives. With the tool-call and exfil paths mechanically confined, the honest residual is injection written as plausible prose aimed at the deliverable, which only layers 6 and 7 catch.

## 7. Brain-agnosticism: what degrades and what compensates

Swapping the brain is a config edit (`config/models.yaml`); nothing else changes. The design assumes weaker brains fail in known ways and pairs each failure with a structural compensation:

| Weak-model failure | Harness compensation |
|---|---|
| declares done at partial progress | task_complete requires an evidence-per-criterion report; verifier re-checks; gate fails closed |
| grades own work generously | verification is a different agent, optionally a different (stronger) model tier |
| malformed tool JSON | lenient argument parsing surfaces a correction message instead of crashing |
| wanders out of scope | out-of-scope fences in every task packet; workspace jail; role grants |
| loops on a failing action | stuck detector; step ceiling; budget ceiling |
| plausible fabricated citations | claims-verifier spot-checks provenance; one invented citation fails the deliverable |
| cannot hold long context | phases receive scoped inputs only; journal carries continuity, not the prompt |

Frontier brains get the opposite treatment: fewer, shorter instructions (strong instruction following makes over-prescription actively harmful), goal-first prompts, effort as the dial, and long-turn autonomy with evidence-grounded progress claims.

## 8. Source to design decision map

Every row verified 2026-07-06. Adopted means the pattern is implemented in this repo; adapted means implemented in modified form; noted means documented for Phase 2+.

| Source | Verdict | What it contributed |
|---|---|---|
| github.com/bybren-llc/safe-agentic-workflow (SAW) | real | role profiles with exit states and preconditions (adopted: RoleDef + gate statuses); templated evidence-asserting handoffs (adopted: task packets and verifier packets in PROMPTS.md); stop-the-line gate: criteria must exist before implementation (adopted: orchestrator boundary refuses to schedule work without a planned check); QAS bounce-back iteration (adopted: gate retry ladder); role independence policy, QAS never collapsed (adopted: verifier isolation); .claude layout (adopted: .claude/agents, commands, hooks) |
| harness-guide.com/guide/your-first-harness/ | real | minimal loop: call, execute tools, append, repeat (adopted: loop.py); append-only role-tagged message state (adopted: Message list); MAX_TURNS cap and errors-as-strings so the model self-corrects (adopted); ordering invariant assistant-before-tool-results (adopted in adapters) |
| github.com/nexu-io/harness-engineering-guide | real | loop detection and token budgets (adopted: stuck detector, Budget); tool registry with description quality emphasis (adopted); generator/evaluator split for long runs (adopted: worker/verifier); memory conventions MEMORY.md (adopted); sandboxing and classifier-permissions (noted: Phase 2/3); orchestration patterns pipeline/fan-out/supervisor (adapted: sequential phases now, parallel groups in plan step 14) |
| dev.to/thedailyagent (harness from scratch) | real | Tool = {name, description, parameters, fn} and registry dict (adopted verbatim shape); pre-dispatch validation returning structured errors (adopted); budget enforcer checked before every iteration (adopted); enforce budgets in code not prompts (adopted as design rule); SQLite session persistence (adapted: JSONL journal instead, diffable and dependency-free) |
| ovrflo.studio (build your own AI harness) | real | five parts instructions/state/scope/verification/lifecycle (adopted as subsystem boundaries); acceptance scenarios written before implementation, never derived from finished code (adopted: orchestrator plans checks with the work); evidence bundle per task (adopted: proofs/); layered verification, tests alone are not proof (adopted: checks then verifier); never store project memory in chat history (adopted: file memory) |
| atlan.com/know/how-to-build-ai-agent-harness/ | real | per-step done-when acceptance tests (adopted: IMPLEMENTATION_PLAN.md format); guardrails as code not prompts, a filter in code is a guarantee (adopted as design rule); never self-scoring, independent scorer (adopted: verifier role); event-sourced persistence with reload-on-boot (adopted: RunState); declarative YAML permissions (adopted: registry config); evals from real traces (noted: plan step 12) |
| dev.to/monuminu (production harness) | real | rescue parsing cascade for malformed model output (adapted: lenient verdict parse + malformed-args path); targeted retry nudges classified by failure mode (adapted: gate reformulation with evidence); bounded loop hard cap (adopted); AGENTS.md-style cross-session memory (adopted: memory index injection); tiered context compaction (noted: Phase 2) |
| platform.claude.com Prompting Claude Fable 5 (official) | real | effort as primary control, default high, xhigh for capability-sensitive (adopted: routing table, output_config.effort); fresh-context verifier subagents outperform self-critique (adopted: the verifier role exists because of this); evidence-grounded progress, audit each claim against a tool result (adopted: worker prompt and task_complete contract); boundary blocks and assessment-vs-action (adopted: machine-owned boundaries); anti-stall end-of-turn rule (adopted: orchestrator long-run discipline); do not request visible reasoning, reasoning_extraction refusals and silent fallback (adopted: no prompt asks for chain-of-thought; refusal is a first-class stop); file-based memory one lesson per file (adopted: memory.py); de-prescribe prompts written for older models (adopted: short single-voice prompts) |
| linkedin.com/pulse AlphaSignal Fable 5 | real | four deletions (step lists, visible reasoning demands, budget countdowns, long rule lists) applied to all three prompts; five additions (effort per task, verification mechanisms, boundary blocks, memory files, intent context) all present; about 8% of Fable 5 tasks route to fallback, design for it (adopted: refusal/error stop conditions and escalation) |
| linas.substack.com Fable 5 playbook | real (free preview; 12 patterns paywalled) | AI-OS Context/Connections/Capabilities/Cadence (adopted as memory-layer framing, section 4); orchestrator-and-cheaper-workers (the core routing thesis); goals not steps (prompt posture); persistent loop as operating partner (runner + cadence). Only the verifiable free-preview skeleton was used |
| lushbinary.com Fable 5 prompting guide | real | machine-checkable success criteria in every prompt (adopted: task packets); deterministic gates regardless of self-verification (adopted: checks run even when the worker claims green); reversibility gates autonomy (adopted: approval policy); cached stable prefix ahead of volatile content (adopted: prompt assembly order); detect and log fallback responses (adapted: refusal stop + journal) |
| conversionsystem.com Fable 5 | real | effort per task class table (adopted: routing table shape); pause only for irreversible, plan-deviating, or human-only-info moments (adopted: approval + needs_human semantics); require receipts on progress claims (adopted); lessons file between sessions (adopted) |
| kbcafe.com Fable 5 | real | intent-and-boundaries beats checklists (prompt posture); claim-audit loop (worker prompt); never prompt for hidden reasoning, silent fallback changes behavior mid-run (adopted: refusal handling, no CoT requests) |
| huggingface.co/blog Svngoku technical harness report | real | check stop_reason before reading content, refusal is structured (adopted: normalized stop_reason and refusal stop); orchestration topology tradeoffs (informed: blocking orchestrator chosen for v0.1, parallel in plan); effort sweeps per task class, cost plateaus before max (informed: routing defaults); allowlists and dry-run gates on mutating tools (adopted: shell allowlist, approval policy); count-tokens over heuristics and async minutes-long requests (noted: adapters use provider usage fields; CLI is async-friendly) |
| youtube.com/watch?v=vcU85OrwuV0 (Nate Herk, Anthropic engineers) | real | include the why in agent prompts (task packets carry goal context); negative prompting (out-of-scope fences); act once information suffices, no overplanning (worker prompt); prove done with evidence, never bare done (task_complete contract) |
| youtube.com/watch?v=R_Nf-IDVZEg (Jadan Jones) | unverified (agent died mid-check) | nothing depended on it; the frontier-designs-the-harness, cheap-models-run-it thesis arrives independently via the Jordan Urbs video and SAW |
| facebook.com/groups/claudeaicommunity post | unverified (login wall) | nothing depended on it; the engineer-habits content is covered by the verified YouTube breakdown and official docs |
| lushbinary.com full-stack apps with Fable 5 | real | plan/build/verify/gate/review with plan as human-reviewed contract (adopted: workflow shape); on red feed failure output back for bounded retries then escalate to human (adopted verbatim: gate ladder); difficulty-based model routing with frontier only for plan/debug (adopted: routing table); token metering and hard budget cap from day one (adopted: Budget); human-owned merge (adopted: needs_human and approval boundaries) |
| lushbinary.com Claude Code dynamic workflows | real | fan-out/synthesize and classify-and-act patterns (noted: plan step 14); agentic laziness, self-preferential bias, monolithic context as the three structural failure modes (adopted: the failure/compensation table in section 7 is organized against them); intermediate traces never enter the parent context (adopted: context hygiene rules); runaway caps and memoized resume (adopted: ceilings, journal resume) |
| youtube.com/watch?v=dJI2GRG1GEE (Jordan Urbs, GLM + harness) | real | cheap open-weight model inside a strong harness carries the workflow (the repo's central thesis); audit-as-checklist workflow template (adopted: workflows as YAML); cross-review between agents catches primary-model errors (adopted: verifier phases); final validation gate before returning to user (adopted: integrate phase cites gate verdicts) |
| github.com/coleam00/archon | real | workflows as repo-committed YAML in a dot-directory (adopted: workflows/); deterministic nodes interleaved with AI nodes, AI only where it adds value (adopted: checks are harness-run commands, not agent acts); plan/implement/validate/review stages (adopted); per-run isolation via worktrees (adapted: per-run workspace dir now, worktrees in plan step 14); model-agnostic client abstraction (adopted: ModelInterface) |
| youtube.com/watch?v=qMnClynCAmM (Cole Medin, harness builders) | real | layered architecture adapters/orchestrator/executors/pluggable models (mirrors section 2); persistent state store for auditability (journal); iterate against deterministic validation until green (gate loop) |

Rejected patterns, for the record: SQLite state (JSONL is diffable and dependency-free at this scale); classifier-based auto-permissions (Phase 3 at the earliest; approval policy must be legible first); more than three role kinds (SAW's 11 roles collapse cleanly into orchestrator/worker/verifier for a solo-operated harness; specializations are prompt files, not new machinery); letting the orchestrator execute (side-effect-free planning is worth more than saved handoffs).

## 9. Evaluation

The suite in tests/ covers the loop stop conditions, permission boundaries (including the verifier shell allowlist and the argument jail), the gate ladder and verdict parsing edge cases, resume semantics (including that a needs_human phase re-runs instead of silently passing), the injection-defense layers (ingress filter, loop tripwire, deny_tools, env scrub, output redaction, write-time secret refusal), the OS sandbox (interpreter writes outside the workspace are blocked, network is denied, and shell/checks fail closed when no usable backend exists), smoke tests over the shipped configs, workflows, and eval suites, the CLI exit codes, and an end-to-end mock-brain workflow including a sabotage case where a worker claims success without producing artifacts and the gate catches it. `harnessie eval` now runs a deterministic 10-scenario mock-brain scorecard covering golden, risky, and recovery cases. This repo's own build ran through the same discipline: a 4-dimension adversarial review workflow found ten evidenced defects (three high severity) that were fixed and regression-tested before delivery. The remaining Phase 2 work is live-endpoint smoke coverage and a brain-swap scorecard over real Anthropic and local OpenAI-compatible endpoints; a brain is admitted to a tier by passing the same scorecard, which is what makes brain-agnostic a testable claim rather than a slogan.
