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

- Python 3.11+ (packaged as `harnessie`, current version 1.0.0, Apache-2.0).
- Runtime dependencies: PyYAML and jsonschema. Model adapters remain stdlib-only (no vendor SDK).
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
- `harness/schemas/v1/` — packaged Draft 2020-12 authoring contracts; public copies
  are generated into `docs/schemas/v1/` and must remain byte-identical.
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
python3 -m harness.cli validate         # authoring schemas + cross-document references
python3 -m harness.cli run workflows/build-and-verify.yaml --goal "..."
python3 -m harness.cli report <run_id>  # plain-language run summary
python3 -m harness.cli audit <run_id>   # verify the hash chain + governance timeline
```

Live provider scorecards are opt-in and never part of the default suite; without
`HARNESSIE_LIVE=1` plus provider config they report `SKIP` and exit clean. Pages/DNS/
PyPI promotion and live-provider calls are deliberate operator acts, never headless.

## Current state (2026-08-09)

- Version 1.0.0 is the current core release on GitHub and PyPI. The separately owned
  Verify Action v0.1.1 and Homebrew formula still pin 0.8.0 pending their own release
  trains; `NEXT.md` records that intentional lag and remaining forward work.
- All four 0.8 write-safety and self-integrity mechanics plus the composed package
  release gate pass with 352 tests, one environment-dependent skip, 47/47 evals, both
  manifests, built-artifact inspection, and a fresh install.
- The first 1.0 development slice freezes six v1 authoring schemas, validates them
  without starting a run, and preserves schema-less 0.8 documents as implicit v1.
- The second 1.0 slice compiles ownership denials into per-agent read-only sandbox
  overlays for shell calls, deterministic checks, and verifier execution. Unsupported
  nested profiles fail closed.
- The third 1.0 slice admits installed tool extensions only through explicit
  `harnessie.tools.v1` entry points. Plugin code is operator-trusted in process; tool
  calls remain registry-mediated, namespaced, provenance-stamped, and resume-pinned.
- The composed gate passes 413 tests with one environment-dependent skip, 50/50
  evals, authoring validation, both manifests, artifact inspection, and fresh install.
- The public Siteline follow-up is green. A fresh live rubric 2.3.0 scan on 2026-08-05
  UTC scored the deployed site A, 97/100, with Level 4 machine enablement at 16/18.
- AIDR-0008 was arbitrated and executed as the separately released, probe-gated
  `harnessie-engine-wrappers` repository. Its release train remains independent.
- CI (`.github/workflows/ci.yml`) proves Linux bubblewrap, macOS, Linux no-backend
  fail-closed behavior, package artifacts, and fresh installation. See NEXT.md for
  the full handoff, current worktree status, and operator-attended steps.
