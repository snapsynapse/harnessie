# CLAUDE.md — agent guidance for Harnessie

Concise orientation for an AI agent working in this repo. Read alongside README.md,
ARCHITECTURE.md, GOVERNANCE.md, SECURITY.md, and NEXT.md (the live session handoff).

## Purpose

Harnessie is a brain-agnostic multi-agent harness: an orchestrator decomposes a goal
into consented task packets, cheap swappable workers execute inside an OS sandbox with
allowlisted tools and per-agent file ownership, and independent fresh-context verifiers
gate every side-effecting phase (deterministic checks first, then model judgment, both
fail-closed). Contested decisions fan out to an adversarial panel whose dissent lands in
AIDR-style decision records that only a human may arbitrate. Everything is budgeted,
resumable, and recorded in a hash-chained tamper-evident audit log. Design thesis: the
harness structure carries the quality floor, the model carries the ceiling.

## Stack

- Python 3.11+ (packaged as `harnessie`, current version 0.7.1, Apache-2.0).
- Runtime dependency: PyYAML only. Model adapters are stdlib-only (no vendor SDK).
- Dev dependency: pytest 8+. Console entry point: `harnessie = harness.cli:main`.
- OS sandbox: macOS `sandbox-exec` (Seatbelt); Linux bubblewrap / firejail / docker.
  Backends are admitted only after a startup smoke test; no usable backend fails closed
  (Windows is unsupported for shell-using workflows).
- Adopted open standards (as lesson imports, not conformance claims): Turnfile, AIDR,
  Graceful Boundaries, Aggregated Intelligence tenets.

## Directory layout

- `harness/` — the runtime package: `cli.py`, `runner.py`, `loop.py`, `verify.py`,
  `verify_standalone.py`, `routing.py`, `cascade.py`, `boundary.py` (PII/secret
  containment), `memory.py`, `state.py`, `roles.py`, `quarantine.py`, `sandbox.py`,
  `ownership.py`, `adversarial.py`, `audit.py`, `events.py`, `approval.py`,
  `preflight.py`, `firstrun.py`, `explain.py`, plus `models/` and `tools/`.
- `agents/` — role prompts (markdown): `orchestrator.md`, `workers/`, `verifiers/`.
- `workflows/` — declared phase sequences (YAML) with per-phase gates and adversarial
  (`mode: adversarial`) contested phases.
- `config/` — `models.yaml` (tiers + routing + budgets: the ONLY file to edit to swap
  brains), `cascade.yaml`, `boundary.yaml`.
- `OWNERSHIP.yaml` — ownership lanes + first-writer auto-claims; operator-owned.
- `decisions/` — the repo's own AIDR records (AIDR-0001..0008).
- `memory/` — project memory: `MEMORY.md` index + stamped facts with `verify_by` expiry.
- `evals/` — deterministic scorecards over mock-brain golden/risky/recovery scenarios.
- `examples/policy-compliance/` — worked end-to-end example with sample data.
- `tests/` — the done-tests for every subsystem (~35 test files).
- `docs/` — the live served tree (harnessie.com via GitHub Pages): markdown sources plus
  generated HTML (built by `scripts/build_docs_html.py`) and the `.well-known/`
  GuideCheck trust pair. `docs/MANIFEST.yaml` pins the machine-readable public artifacts.
- Root `*.md` — ARCHITECTURE, GOVERNANCE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN,
  PROMPTS, EVALS, INTENT (9-section standard), CHANGELOG, NEXT (session handoff).

## Conventions

- Eval-first change discipline: a behavior change needs a scenario that fails before
  (red) and passes after (green). See EVALS.md and CONTRIBUTING.md.
- Assert on structured outcomes (a refusal's `error`/`boundary`, a phase's stop
  condition), never on prose wording.
- Keep policy in the harness, enforced at dispatch. Never move a guarantee into a role
  prompt. Controls that cannot be enforced fail closed, never skip.
- Consequential / direction-setting or contested changes are recorded in `decisions/`
  with independent positions and human-only arbitration — never decided inside a PR.
  Agents never author or edit Arbitration sections.
- Markdown style: plain headings, bare `https` URLs, no em dashes. Match surrounding
  code; comment only to state a constraint the code cannot show.
- Docs: HTML pages are generated from markdown — edit the markdown, run
  `scripts/build_docs_html.py`, commit both. A guide edit must move five sync points
  together (root `assistant-guide.txt`, `.well-known/` copy, sidecar hash, trust-bundle
  pins, and the manual DNS TXT value); four are enforced by `tests/test_guide_artifacts.py`.
- `.claude/` (local dogfooding config) is gitignored and does not ship; the canonical
  role prompts live in `agents/` and the CLI is the primary interface.
- Do NOT stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, `workspace/`, or
  `ROADMAP-PRIVATE.md` (all gitignored).

## Build / test / run (from docs — do not assume; run only when asked)

```bash
pip install -e ".[dev]"                 # dev install from source
python3 -m pytest -q                    # unit + integration, mock brain, no network
python3 -m harness.cli eval             # deterministic eval scorecards
python3 -m harness.cli verify-manifest  # trust-bundle integrity (pins ~9 files)
python3 -m harness.cli run workflows/build-and-verify.yaml --goal "..."
python3 -m harness.cli report <run_id>  # plain-language run summary
python3 -m harness.cli audit <run_id>   # verify the hash chain + governance timeline
```

Live provider scorecards are opt-in and never part of the default suite; without
`HARNESSIE_LIVE=1` plus provider config they report `SKIP` and exit clean. Pages/DNS/
PyPI promotion and live-provider calls are deliberate operator acts, never headless.

## Current state (2026-07-12)

- Branch `main`, clean working tree, level with `origin/main` (0 ahead / 0 behind).
- Version 0.7.1 shipped 2026-07-09 (standalone `harnessie verify` surface). Post-release
  surfaces live: harnessie-verify-action v0.1.0 on the GitHub Marketplace, Homebrew tap
  current, dogfood PR-verification workflow armed. Last verification at ship: 269 passed
  / 1 skipped, 43/43 eval, manifest OK.
- CI (`.github/workflows/ci.yml`): three jobs — Linux bubblewrap (portability proof),
  macOS, and Linux no-backend (fail-closed proof). Plus `verify-pr-claims.yml` dogfooding
  the standalone verifier on PR bodies.
- Open item: AIDR-0008 (operator-side engine-wrapper containment) awaiting arbitration.
  See NEXT.md for the full handoff and operator-attended step list.
