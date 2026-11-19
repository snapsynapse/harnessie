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

- Python 3.11+ (packaged as `harnessie`, published stable version 1.5.1, Apache-2.0).
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

## Current state (2026-11-19)

- Core 1.5.1 is published on GitHub and PyPI from signed tag `v1.5.1`
  at `2bb78f24ad029db7e1c1545fdc6ab3a39f808c92`. Original-build assets,
  publisher attestations and a fresh public-index consumer are verified.
  The security repair passed 2,319 tests and 76 deterministic evals in the
  recorded release gate. Read [release execution](audits/release-1.5.1.md)
  for publication and downstream evidence, and [NEXT.md](NEXT.md) before
  selecting follow-up work or resuming the pilot.
- The 1.5.0 interoperability features remain shipped, including harness identity,
  tool-contract metrics, ATIF-v1.7 export, Harbor examples, AIDR export and the
  offline observer. Their dated acceptance records cover their tested versions.
- `examples/harbor-verifier/` and `examples/harbor-agent/` run Harnessie on either side
  of a Harbor trial; exit 0 is reward 1, exit 1 is reward 0, exit 2 is no reward file
  (cannot-verify stays unscorable). Dated acceptance audits are under `audits/`
  (`atif-export-acceptance-2026-10-05.md`, `harbor-verifier-acceptance-2026-10-05.md`,
  `harbor-agent-acceptance-2026-10-05.md`, `live-scorecard-2026-10-05/`). They are
  plumbing results on one backend and one local model, not brain evidence; token-level
  ATIF agreement needs vLLM or SGLang.
- Verify Action v0.2.4 and stable `v0` default to core 1.5.1 at
  `d3fe8ac756cd2d2e968237781d4614cb52c7f55b`. Nine merged-commit offline
  fixtures and a fresh Ubuntu stable-tag consumer passed. Harnessie's
  claim-verification workflow pins this commit through merged PR #52.
  Homebrew 1.5.1 passed a fresh source install and CLI smoke on arm64 macOS
  in an isolated prefix using the host's installed dependency versions.
  Engine wrappers remain independently released at 0.1.0.
  See [downstream acceptance](audits/release-1.5.1.md#downstream-acceptance).
- The 8,054-byte 1.5.1 guide earned hosted Level 3 under profile 2.0.0 with
  zero blockers. Independent checks matched the served guide, sidecar, DNS,
  repository pins and signed tag source. The hosted result retains
  `anchor.hosted.unverified`. The earlier 1.5.0 Level 4 receipt covers its
  historical bytes. See [guide acceptance](audits/release-1.5.1.md#revised-guidecheck-gate).
  A guide change requires a new sidecar, trust pins, independent anchor and
  hosted receipt.
- Human browser and assistive-technology accessibility acceptance remains a
  nonblocking roadmap item. No full-conformance claim is made.
- `audits/release-1.5.1.md` records current release evidence. Earlier release
  records remain historical. `NEXT.md` names remaining work.
  Test counts are dated observations, not contracts.
- The lead adoption surface remains `harnessie verify` for agent-produced changes.
  Ringer composes through its existing process-exit contract; the Harbor verifier
  example composes the same contract with Harbor's reward interface. The Qwen
  controlled-review pilot remains the active tranche and is unchanged by this release.
  Bidding, commentary, follow mode, automatic runner observation and bid-driven model
  selection are an evidence-gated capability sequence; AIDR-0009 remains historical
  authority for its observer-only first slice.
