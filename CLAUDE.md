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

- Python 3.11+ (packaged as `harnessie`, stable version 1.5.0, Apache-2.0).
- Runtime dependencies: PyYAML and jsonschema. Model adapters remain stdlib-only (no vendor SDK).
- Dev dependency: pytest 8+. Console entry point: `harnessie = harness.cli:main`.
- OS sandbox: macOS `sandbox-exec` (Seatbelt); Linux bubblewrap / firejail / docker.
  Backends are admitted only after a startup smoke test; no usable backend fails closed
  (Windows is unsupported for shell-using workflows).
- Adopted open standards (as lesson imports, not conformance claims): Turnfile, AIDR,
  Graceful Boundaries, Aggregated Intelligence tenets.

## Directory layout

- `harness/` — the runtime package: `cli.py`, `runner.py`, `loop.py`, `verify.py`,
  `verify_standalone.py`, `verify_evidence.py`, `trace_eval.py`, `identity.py` (harness identity on
  every result), `atif.py` (ATIF-v1.7 trajectory export), `routing.py`, `cascade.py`, `boundary.py` (PII/secret
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
- `examples/` — `policy-compliance/` (worked end-to-end example with sample data), `ownership-collision/`,
  `aidr-export/`, `harbor-verifier/` (Harnessie as a Harbor verifier, both shapes) and `harbor-agent/`
  (Harnessie as a Harbor external agent).
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

## Current state (2026-10-06)

- Core 1.5.0 is published and verified on GitHub and PyPI from signed tag `v1.5.0`
  (commit `4ccf3f304bca0c88c8997c0a0cf33a909145d3ef`), with original-build provenance
  and publisher attestations. Theme: Harbor and OpenEnv interoperability. It adds
  harness identity on every result (`harness/identity.py`, verify report header,
  `harness_identity` event), tool-contract break metrics with a `tool_contract` live
  scorecard row and the first measured local brains, `harnessie atif` ATIF-v1.7
  export (no model calls; refuses a broken chain, an unfinished loop or a step gap;
  absent fields are reported, never invented), richer `model_turn` and `tool_result`
  events, `evals/tool-contract.yaml`, the urllib3 2.8.0 lock refresh, a working
  default `local` tier and Linux-portable pilot tests. AIDR export and the offline
  observer are retained unchanged.
- `examples/harbor-verifier/` and `examples/harbor-agent/` run Harnessie on either side
  of a Harbor trial; exit 0 is reward 1, exit 1 is reward 0, exit 2 is no reward file
  (cannot-verify stays unscorable). Dated acceptance audits are under `audits/`
  (`atif-export-acceptance-2026-10-05.md`, `harbor-verifier-acceptance-2026-10-05.md`,
  `harbor-agent-acceptance-2026-10-05.md`, `live-scorecard-2026-10-05/`). They are
  plumbing results on one backend and one local model, not brain evidence; token-level
  ATIF agreement needs vLLM or SGLang.
- Downstream bumps are in progress and still pin 1.4.1: Verify Action 0.2.3 is proposed
  at https://github.com/snapsynapse/harnessie-verify-action/pull/4 (seven fixtures
  green, unmerged); the Homebrew 1.5.0 formula is in progress at https://github.com/snapsynapse/homebrew-tap/pull/5, where the exact formula passed `brew audit --strict --online`, a real 1.4.1 to 1.5.0 upgrade, `brew test` and `brew linkage --test`; it is not merged.
  Verify Action 0.2.2/stable `v0` and Homebrew 1.4.1 remain current. Engine wrappers
  remain independently released at 0.1.0.
- The final 1.5.0 guide (8,054 bytes) earned hosted Level 4 under profile 2.0.0 on
  2026-10-06 with zero blockers; see `audits/release-1.5.0/guidecheck-prepublication.json`.
  Preserve its frozen bytes. Any later guide change requires a new sidecar, trust
  pins, independent anchor, and hosted receipt.
- Human browser and assistive-technology accessibility acceptance remains a
  nonblocking roadmap item. No full-conformance claim is made.
- `audits/release-1.5.0.md` records current release and provider evidence;
  `audits/release-1.4.1.md` remains historical. `NEXT.md` names remaining work.
  Test counts are dated observations, not contracts.
- The lead adoption surface remains `harnessie verify` for agent-produced changes.
  Ringer composes through its existing process-exit contract; the Harbor verifier
  example composes the same contract with Harbor's reward interface. The Qwen
  controlled-review pilot remains the active tranche and is unchanged by this release.
  Bidding, commentary, follow mode, automatic runner observation and bid-driven model
  selection are an evidence-gated capability sequence; AIDR-0009 remains historical
  authority for its observer-only first slice.
