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

- Python 3.11+ (packaged as `harnessie`, stable version 1.4.1, Apache-2.0).
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
- `decisions/` — the repo's own AIDR records (AIDR-0001..0009; AIDR-0009 historically approves the offline observer first, while current program direction lives in INTENT, NEXT and ROADMAP).
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

## Current state (2026-09-09)

- Core 1.4.1 is published and verified on GitHub and PyPI, with original-build
  provenance and package attestations. It includes strict open-record AIDR export,
  platform refusal, and the installed mock consumer example. Export is an
  operator-issued file write outside runner ownership/consent mediation; it
  makes no model calls and keeps Arbitration empty.
- Verify Action 0.2.2 and stable `v0` are published at
  `9f18d70017f395ef4d15ac5746e30ac633f00f8e`, pinning core 1.4.1.
  Homebrew 1.4.1 is published at tap commit
  `953760f3968200f99658bfb068609532cb9fbf4d`; the real upgrade, formula tests,
  and installed version are verified.
  Engine wrappers remain independently released at 0.1.0.
- The final 1.4.1 guide earned hosted Level 4 under profile 2.0.0 with zero blockers;
  see `audits/release-1.4.1/guidecheck-prepublication.json`. Preserve its frozen
  bytes during release closeout. Any later guide change requires a new sidecar,
  trust pins, independent anchor, and hosted receipt.
- The accessibility handoff is processed, its repairs are deployed, and current-source
  automated evidence is recorded. Human browser and assistive-technology acceptance is
  a nonblocking roadmap item. No full-conformance claim is made.
- `audits/release-1.4.1.md` records current release and provider evidence;
  `audits/release-1.3.1.md` remains historical. `NEXT.md` names remaining work.
  Test counts are dated observations, not contracts.
- The lead adoption surface remains `harnessie verify` for agent-produced changes.
  Ringer composes through its existing process-exit contract. The controlled-review
  live pilot is the next active tranche. Bidding, commentary, follow mode, automatic
  runner observation and bid-driven model selection are an evidence-gated capability
  sequence; AIDR-0009 remains historical authority for its observer-only first slice.
