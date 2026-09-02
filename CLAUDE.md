# CLAUDE.md — agent guidance for Harnessie

Concise orientation for an AI agent working in this repo. Read alongside README.md,
ARCHITECTURE.md, GOVERNANCE.md, SECURITY.md, and NEXT.md (current source and release state).

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

- Python 3.11+ (packaged as `harnessie`, stable version 1.1.0, Apache-2.0).
- Runtime dependencies: PyYAML and jsonschema. Model adapters remain stdlib-only (no vendor SDK).
- Dev dependency: pytest 8+. Console entry point: `harnessie = harness.cli:main`.
- OS sandbox: macOS `sandbox-exec` (Seatbelt); Linux bubblewrap / firejail / docker.
  Backends are admitted only after a startup smoke test; no usable backend fails closed
  (Windows is unsupported for shell-using workflows).
- Adopted open standards (as lesson imports, not conformance claims): Turnfile, AIDR,
  Graceful Boundaries, Aggregated Intelligence tenets.

## Directory layout

- `harness/` — the runtime package: `cli.py`, `runner.py`, `loop.py`, `verify.py`,
  `verify_standalone.py`, `verify_evidence.py`, `trace_eval.py`, `routing.py`, `cascade.py`, `boundary.py` (PII/secret
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
- `tests/` — the done-tests for every subsystem, including evidence-bundle, structured-verdict, trace-metric, and synthetic Ringer intake coverage.
- `docs/` — the live served tree (harnessie.com via GitHub Pages): markdown sources plus
  generated HTML (built by `scripts/build_docs_html.py`) and the `.well-known/`
  GuideCheck trust pair. `docs/MANIFEST.yaml` pins the machine-readable public artifacts.
- Root `*.md` — ARCHITECTURE, GOVERNANCE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN,
  PROMPTS, EVALS, INTENT (9-section standard), CHANGELOG, NEXT (current state).

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
python3 -m harness.cli verify-manifest  # outward public trust-bundle integrity
python3 -m harness.cli verify-inward-manifest  # shipped harness-input integrity
python3 -m harness.cli validate         # authoring schemas + cross-document references
python3 -m harness.cli run workflows/build-and-verify.yaml --goal "..."
python3 -m harness.cli report <run_id>  # plain-language run summary
python3 -m harness.cli audit <run_id>   # verify the hash chain + governance timeline
```

Live provider scorecards are opt-in and never part of the default suite; without
`HARNESSIE_LIVE=1` plus provider config they report `SKIP` and exit clean. Pages/DNS/
PyPI promotion and live-provider calls are deliberate operator acts, never headless.

## Current state (2026-09-01)

- Version 1.1.0 is the stable core release on GitHub, PyPI, and Homebrew. Harnessie
  Verify v0.1.3 and stable `snapsynapse/harnessie-verify-action@v0` pin 1.1.0.
- Current `main` contains unreleased work intended for the next minor release:
  OpenAI Responses support, v1 evidence bundles, structured claim verdicts,
  deterministic Ringer fixtures, trace metrics, and compatibility fixes.
- Stable and source channels must remain explicit. Do not claim the 1.1.0 wheel or
  Action contains those additions. The assistant guide stays the externally anchored
  1.1.0 artifact until an atomic release rotation.
- The latest verified source baseline before this documentation pass was 481 passed,
  9 skipped, 51/51 deterministic evals, 20 outward trust files, and 16 inward files.
  Counts are observations, not a permanent contract; rerun the gates before claiming
  current status.
- The lead adoption surface is `harnessie verify` for agent-produced changes. Ringer
  is the first named composition target through its existing exit-code check contract;
  the full harness is the growth path for consent, ownership, containment, arbitration,
  and tamper-evident run audits.
- CI (`.github/workflows/ci.yml`) proves Linux bubblewrap, macOS, Linux no-backend
  fail-closed behavior, package artifacts, and fresh installation. `NEXT.md` records
  the exact current work order and release authority boundaries.
