# Changelog

All notable changes to Harnessie are recorded here. Format loosely follows Keep a Changelog; versions follow semver.

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
