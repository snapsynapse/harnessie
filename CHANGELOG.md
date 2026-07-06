# Changelog

All notable changes to Harnessie are recorded here. Format loosely follows Keep a Changelog; versions follow semver.

## 0.2.0 (2026-07-06)

The governance release: adversarial collaboration and evals promoted to foundational principles, importing the shipped lessons of Turnfile (consent-based coordination, ownership lanes, maintainer authority) and AIDR (independent positions, preserved dissent, human-only arbitration, earned claims) as harness-enforced mechanics. Design rationale: `GOVERNANCE.md`; direction record: `decisions/AIDR-0001` (open, awaiting arbitration). Displaces the previously roadmapped portability theme to 0.3.0.

### Added

- Consent-based orchestration: worker task packets are offers. Side-effecting tools stay locked until `accept_task`; `decline_task(reason, counter_proposal?)` is a first-class `declined` stop. The gate re-offers once on a counter-proposal and never escalates the route on a decline. Enforced at registry dispatch; worker phases default `consent: true` (opt out per phase).
- Ownership lanes (`harness/ownership.py` + root `OWNERSHIP.yaml`): agents own the files they create; cross-agent writes are refused at dispatch with a `request_change` remedy; operator lanes are locked to all agents; collaborative lanes are shared. The ledger lives outside the workspace jail so no agent can edit its own permissions.
- Adversarial contested phases (`harness/adversarial.py`, workflow `mode: adversarial`): independent read-only positions across configurable brains, bounded objection rounds, harness-assembled AIDR-shaped decision records under `runs/<id>/decisions/` with structurally earned claims (`independent-positions`, `dissent-preserved`, `human-arbitrated`). Contested outcomes halt as `needs_arbitration`; the operator arbitrates by editing the record in their own words and resuming. No agent and no harness code path writes the Arbitration section.
- Tamper-evident audit (`harness/audit.py`): events.jsonl is hash-chained (`seq`/`prev` per event, chain survives resume); `harnessie audit <run_id>` verifies the chain and renders the governance timeline (exit 1 on a broken chain).
- Governance eval suite (`evals/governance.yaml`, 12 scenarios) plus new eval kinds (`ownership`, `adversarial`, `audit`, consent-flagged `loop`), written red before the implementation per the eval-first change discipline.
- Shipped `workflows/contested-decision.yaml`: a two-brain adversarial panel whose record can earn `independent-positions` across providers.
- `harnessie eval` deterministic scorecard runner plus `evals/baseline.yaml` mock-brain scenarios: golden passes, risky fail-closed verdicts, and recovery/gate retries.
- `harnessie init` scaffold command for installed CLI usage; now also scaffolds `OWNERSHIP.yaml`.
- `decisions/` directory with the repo's own AIDR records; `templates/AIDR-0000-template.md`.

### Changed

- Workflow phase statuses gain `needs_arbitration` (halts the run exactly like `needs_human`).
- Role boundary blocks now state the consent contract, ownership rule, and agreement-is-evidence-not-authority posture; `agents/orchestrator.md` gains the offers-not-commands section.
- Sandbox availability now requires a real `sandbox-exec` profile-application smoke test. Hosts that expose the binary but reject `sandbox_apply` are treated as sandbox-unavailable and fail closed.
- Routing config now fails early when a workflow route references an unconfigured tier or invalid effort, instead of silently falling back to another tier.

### Tests

- 44 new tests across `test_consent.py`, `test_ownership.py`, `test_adversarial.py`, `test_audit.py`; suite at 100 passing (mock brain, no network). Eval scorecard at 21 scenarios. Repo-config smoke tests now validate adversarial phases in shipped workflows.
- Added eval runner, CLI eval, init scaffolding, and bad-routing-config regression coverage. The suite passes with unusable real sandbox backends by skipping only the backend-dependent confinement tests.

## 0.1.0 (2026-07-06)

Initial build: a brain-agnostic multi-agent harness (orchestrator / workers / verifiers) with verification gates, cost routing, file-based memory, and a layered prompt-injection defense.

### Added

- Brain-agnostic model interface (`harness/models/`) with Anthropic, OpenAI-compatible, and mock adapters. Effort is a first-class request parameter (low/medium/high/xhigh/max). Swapping the brain is a `config/models.yaml` edit.
- Tool registry (`harness/tools/`) as the single source of truth for capabilities and policy: per-role grants enforced at schema and dispatch, effects classes, approval gates, workspace jail, per-role shell allowlists, and argument jail.
- Agent loop (`harness/loop.py`) with enumerated stop conditions (complete, max_steps, budget, stuck, model_error, no_action, refusal); silence is never success.
- Verification gate (`harness/verify.py`): deterministic checks then an independent fresh-context verifier, fail closed, with a reformulate-and-escalate ladder (effort, then tier, then human).
- Routing and budgets (`harness/routing.py`): task_class to (tier, effort) from config, escalation ladder, hard cost ceilings.
- File-based memory and proofs (`harness/memory.py`), append-only run journal with resume (`harness/state.py`), and a single structured event log (`harness/events.py`).
- Workflow runner (`harness/runner.py`) executing `workflows/*.yaml` phase by phase through gates, with resume that skips only verified successes.
- Role prompts (`agents/`) with machine-owned boundary blocks assembled by `harness/roles.py`.
- Seven-layer prompt-injection defense (see `SECURITY.md`): ingress filter and secret detection (`harness/quarantine.py`), loop tripwire, per-phase `deny_tools`, OS sandbox (`harness/sandbox.py`, macOS Seatbelt, workspace-only writes, network deny, fail closed), secret guards (scrubbed child env, output redaction, write-time credential refusal), independent verifier, and human review.
- CLI (`harness/cli.py`): run, resume, report.
- Two workflows (`build-and-verify`, `policy-compliance`) and a worked example under `examples/`.
- Documentation: `INTENT.md` (9-section repo-standards template), `ARCHITECTURE.md` (with a verified source-to-decision map and `source-verification.json`), `IMPLEMENTATION_PLAN.md`, `ROADMAP.md`, `PROMPTS.md`, `SECURITY.md`, and `session-url-log.md`.
- Repo hygiene to portfolio Repo Standards (all-tier): baseline `.gitignore`, `.claude/` untracked as a full directory, `CHANGELOG.md` and `LICENSE` at root.
- Test suite: 53 tests over a mock brain, no network required.

### Notes

- Every external source relied on in the design was fetched and verified before use; two of the 22 charter sources were unverifiable and nothing depends on them.
- A four-dimension adversarial review during the build found and fixed three high-severity defects (resume skipping needs_human phases, a verifier shell escape, an unparseable shipped config) before this release.

### Not yet implemented (see `IMPLEMENTATION_PLAN.md` and `ROADMAP.md`)

- Live-endpoint smoke tests, golden-task eval scorecard, interactive approval handler, parallel workers, a Linux sandbox backend, tool plugins. Sequenced into 0.2.0 / 0.3.0 / 1.0.0 milestones in the roadmap; Linux support is the 0.2.0 headline.
