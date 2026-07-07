# Changelog

All notable changes to Harnessie are recorded here. Format loosely follows Keep a Changelog; versions follow semver.

## Unreleased

### Added

- Served HTML doc pages: every markdown doc in `docs/` (quickstart, getting started, user guide, brains, threat model) now has a styled, navigable HTML page on harnessie.com, generated from the markdown by the new `scripts/build_docs_html.py` (dependency-free; edit the markdown, run the script, commit source and output together). Site nav, cross-links, and a per-page footer naming the generating source; internal links between docs resolve on-site, links to repo-root engineering docs still point at GitHub.
- Landing page Quick start gains "Option 1: AI-assisted, with a verifiable guide": point an assistant at the served GuideCheck guide instead of letting it improvise an install from web search, with the safety rationale stated (same bytes for human and assistant, verify-then-approve, pre-declared read-only actions, nothing installs or spends without explicit approval). The hand-install path becomes Option 2.
- Landing page and JSON-LD "builds on" credits swap HardGuard25 for GuideCheck; hero CTA, feature links, and footer doc links now point at the on-site pages instead of GitHub; footer gains a Quickstart link.
- `docs/sitemap.xml` lists the five new doc pages; `docs/llms.txt` Key files point at the on-site pages; `docs/MANIFEST.yaml` re-pinned for both.
- Published harnessie 0.6.0 to PyPI (wheel + sdist; twine check passed; artifacts swept for private files before upload; LICENSE and NOTICE ship in both). `pip install harnessie` (or pipx / `uv tool install`) is now the documented entry across README, quickstart, getting-started, and the landing page's Option 2, each ending on the guided init's zero-dollar green run; source install is kept for development. Verified by a fresh install from the live index reaching the green readiness report.
- Tagged and published the v0.6.0 GitHub release with the PyPI artifacts attached; the GuideCheck sidecar's `immutable-release-url` now resolves, completing the Level 4 provenance chain.
- Homebrew formula in the existing `snapsynapse/homebrew-tap` (PyPI-sourced Python virtualenv, pattern shared with the tap's other Python formula): `brew install snapsynapse/tap/harnessie`, verified locally with `brew install` + `brew test` (the test scaffolds a project and asserts the guided zero-dollar run reports ready). Named alongside pipx/uv in the install docs.
- ROADMAP gains a Post-1.0 candidates section: an official Docker image (deferred deliberately — the sandbox story inverts inside a container, so the image is a security-docs problem as much as packaging, with its acceptance bar stated) and a conda-forge feedstock if demand appears.
- Documentation and agentic-surface sync pass after the launch-day changes: GUIDE.md installs from PyPI first (source second) and its CLI table now describes the cost preview + plain summary on `run`, the plain-language `report` with `--raw`, and the guided `init` with `--no-verify`; README's layout note, requirements line, and assistant-guide entry (now "GuideCheck Level 4, verified") updated; INTENT.md header, scope boundary (Linux backends shipped, Windows-native is the out-of-scope remainder), and the stale pre-launch `docs/` exception rewritten to the live reality; `docs/llms.txt` gains an Install section (pip/pipx/uv/brew plus the AI-assisted GuideCheck path) and links to the brains and threat-model pages.
- `assistant-guide.txt` refreshed (hash rotation): expected suite count moved to 195 passed / 1 skipped, and a `registry-url` metadata field added pointing at the PyPI 0.6.0 record — the package-registry channel joins DNS TXT as cross-channel provenance. Byte-identical pair, sidecar hash/bytes, and trust-bundle pins all re-synced (test-enforced); the DNS TXT anchor at `_assistant-guide.harnessie.com` must be updated to the new hash by the operator, and a hosted Level 4 re-verify follows that.

## 0.6.0 (2026-07-07)

### Added

- Relicensed MIT -> Apache-2.0 ahead of public release (sole author, no external contributors; copyright Snap Synapse LLC). Adds NOTICE with the trademark carveout (Apache section 6), the PAICE.work PBC specifications carveout (adoption and credit, not ownership), and the standing rule that PBC-originated code enters only under an explicit written grant recorded in NOTICE before any public commit. License references updated in README, pyproject.toml, and the landing page.
- Expanded `evals/operability.yaml` with risky/recovery coverage for invalid approval policies, phase-scoped approval denial, parallel failure halting downstream work, root-workspace bleed prevention, and audit-chain survival under concurrent phases.
- Added `evals/stewardship.yaml` for public-surface local-path hygiene and `NEXT.md` handoff quality checks.
- Documented the agent operating posture for optional local OpenAI-compatible/Ollama checks and CLI fan-out review: useful verification evidence, not a replacement for deterministic evals and operator-gated live-provider rules.
- Pre-run cost preview and ceiling-less-live-run refusal (`harness/preflight.py`, wired into CLI `run`/`resume`): before any run state is created or any brain is built, the harness states whether the configured brains are live or mock (zero-dollar), shows the budget ceilings and a worst-case dollar figure with which ceiling binds first, and refuses to start a live run when no ceiling is set. Mock runs are always free and never refused; an unknown provider is treated as billable (fail-safe). First 0.6.0 "Ease" rung; satisfies the 0.6 acceptance "a fresh install on a ceiling-less config refuses a live run."
- Default-deny posture audit (0.6.0 launch gate) extending `tests/test_repo_configs.py`: eleven assertions proving the shipped `register_builtin` registry, `OWNERSHIP.yaml`, and both CLI seams default closed — orchestrator holds no side-effecting tool, verifier never writes, every write/execute tool excludes the orchestrator and includes the worker, `expire_fact` is approval-gated, `dispatch`/`_loop_for` default network off, and unknown-tool / wrong-role / unapproved / pre-consent dispatches all fail closed.
- Published threat-model comparison artifact `docs/threat-model.md` (0.6.0 "Safety" launch gate): an eleven-row falsifiable table mapping Harnessie's structural properties against the failure modes of prevailing harness patterns (unsandboxed shell, prompt-level-only guardrails, self-verification, silent dissent-merging, plus cost, secrets, approval, ownership, consent, and audit), each row citing the enforcing code and the test that proves it. All 25 cited `file::test` nodes resolve and pass; the honest residual and the tamper-evident / per-file limits are stated in the artifact. Linked from `README.md` and `SECURITY.md`.
- Graceful Boundaries conformance for the refusal surface (0.6.0 standards-adoption gate), documented in `GOVERNANCE.md` §8 and `INTENT.md` §7: checked against GB spec 1.5.1 and adopted transport-adapted. Every denial site carries the GB Level 1 `{error, detail, why}` grammar (plus a `boundary` tag), structurally guaranteed by the required-field `Refusal` type; the action-refusal codes `authority_insufficient` / `approval_required` / `action_unsupported` match GB's Action Boundaries vocabulary (spec Appendix C.4); SC-16 (guidance-is-untrusted-data) holds both directions. The HTTP-shaped Levels 2 through 4 (limits-discovery endpoint, proactive RateLimit headers) are N/A by transport for a local harness and explicitly not claimed. `INTENT.md` §7 moved from "non-binding future integration" to adopted.
- Standing "break it" invitation (0.6.0 "Safety" launch gate): `SECURITY.md` gains a vulnerability-disclosure path (GitHub private vulnerability reporting, with scope drawn from the threat model) and a "Break it" section publishing `evals/redteam.yaml` as falsifiable red-team targets. Three canary-exfiltration scenarios attack the write-time exfil guard, the kind-label-only refusal grammar, and the shell allowlist; passing proves the canary credentials reach no workspace artifact and appear nowhere in the events log. New loop-scenario expectation `expect_events_absent` asserts canary absence over the raw events stream (failure messages name canaries by prefix only), documented in `EVALS.md`.
- Refreshed `assistant-guide.txt` expected-results block (was stale at v0.5.0 counts) and noted that the block must move in the same change that moves the numbers; `docs/MANIFEST.yaml` re-pinned accordingly.
- `ROADMAP.md` gains the planned 0.7.0 milestone (sovereignty cascade routing and the containment boundary), double-gated on the 0.6 launch and an adoption AIDR through the contested-decision workflow; the 1.0 gate now includes 0.7 acceptance.
- Plain-language operator surface (`harness/explain.py`, wired into CLI `run`/`resume`/`report`; 0.6.0 "Ease" rung): `run` and `resume` end with a plain summary that leads with the outcome and, on a halt, names one next action; `harnessie report` now leads with a plain-language summary reconstructed from the event log (works on a crashed run with no `workflow_done`) instead of a raw JSON dump. A `needs_human` halt names `harnessie resume <run_id> <workflow>`; a `needs_arbitration` halt names the exact decision record to edit. `workflow_start` now records the workflow path so the resume command is precise. The raw journal/events/proofs view moved behind `report --raw`.
- Guided first run for `harnessie init` (`harness/firstrun.py`; 0.6.0 "Ease" rung): after scaffolding, `init` prints a readiness report — Python 3.11+ check, OS sandbox backend detection (with the fail-closed framing when none is present), env-var API-key guidance (the mock scaffold needs no key and bills nothing), and a zero-dollar mock run of the eval baseline that must be green — then names the next commands to run. `--no-verify` skips the guided run for scripted scaffolding. Closes most of the acceptance clause "a non-developer reaches a green first run without touching a config file."
- Non-developer quickstart `docs/quickstart.md` (0.6.0 "Ease" rungs): the gentlest on-ramp, assuming no git or shell fluency, walking the `harnessie init` (guided readiness + zero-dollar mock run) → `run` → `report` flow end to end, with a 19-term glossary in the order a newcomer meets each and an honest "Running on Windows" section (bare Windows has no usable sandbox so shell steps are blocked, mock/offline work still runs; WSL2 is the supported path). Linked from `README.md` and `docs/getting-started.md`; passes the stewardship public-surface hygiene eval.
- GuideCheck adoption for the assistant guide (0.6.0 standards-adoption gate): `assistant-guide.txt` rewritten from a minimal dev note to a conforming GuideCheck Level 3 profile for the bounded task "review a Harnessie checkout before authorizing a run" (metadata block, compact verification instruction, authority and safety rules, read-only action blocks, stop-and-ask, acceptance checklist, restated threat model / untrusted-content / disclaimer; ASCII-only, 7620 bytes). Byte-identical served copy at `docs/.well-known/assistant-guide.txt` with a sidecar provenance manifest `docs/.well-known/assistant-guide-manifest.txt` (`guide-sha256`, `guide-bytes`, `immutable-release-url`), a `docs/.nojekyll` so Pages serves the dot-directory, discovery via `<link rel="assistant-guide">` + landing footer + `docs/llms.txt` + a `pyproject.toml` `[project.urls]` `Assistant-Guide` entry (the PyPI cross-channel pointer), and the three files pinned in `docs/MANIFEST.yaml` (now 9 files). Verified with the GuideCheck reference verifier: Level 3, zero blocking findings, zero warnings. After launch, Level 4 was confirmed end-to-end by the hosted fetching verifier (guidecheck-hosted 0.7.0: achieved level 4, zero blocking findings) against the live `.well-known/` pair, the sidecar manifest, and an independent DNS TXT anchor published at `_assistant-guide.harnessie.com` (registrar control plane, distinct credentials from the GitHub-hosted web root, resolved via DoH). Guide-artifact sync is enforced by `tests/test_guide_artifacts.py`; the DNS TXT value is the fifth, manual sync point.

### Tests

- Eval scorecard now passes 38/38 (redteam suite added).
- `tests/test_explain.py`: plain-status translation, halt next-action wording for needs_human and needs_arbitration, run-summary success vs halt, and `format_report` over completed / halted / crashed-before-first-phase / missing runs. `tests/test_roles_cli.py` updated to the plain-language report and halt output plus a `report --raw` check.
- `tests/test_firstrun.py`: Python check passes on a supported interpreter, sandbox check frames a missing backend as protection, key guidance needs no key for the mock scaffold and names the env var for a real provider, the mock verification is green and zero-dollar, and the full guided run is ready after scaffold. Suite now 189 passed, 1 skipped.
- `tests/test_evals.py`: redteam suite green, plus falsifiability tests for `expect_events_absent` (a planted canary is reported with a prefix-only message; a clean log passes). Suite now 173 passed, 1 skipped.
- `tests/test_preflight.py`: mock never refuses, live-without-ceiling refuses with a fix pointer, live-with-ceiling proceeds, worst-case math and binding-ceiling selection, unknown-provider fail-safe.
- `tests/test_repo_configs.py`: eleven default-deny posture assertions over the shipped registry and configs.
- `tests/test_graceful_boundaries.py`: nine GB-conformance assertions (grammar completeness across denial paths, snake_case error, why-is-a-reason, required-field structural guarantee, Action Boundaries vocabulary). Suite now 170 passed, 1 skipped.

## 0.5.0 (2026-07-07)

### Added

- Headless approval policy files (`harness/approval.py`, CLI `--approval-policy`): `allow:` and `deny:` rules name approval-gated tools, optionally scoped to a phase. Default remains deny; explicit deny wins; invalid broad rules deny closed.
- TTY approval prompt path (`--approve-interactive`) for approval-gated tool calls when stdin is interactive.
- Per-phase cost display: `PhaseOutcome` and `phase_done` events now carry phase-local token and USD deltas alongside cumulative run spend; CLI run output prints per-phase cost.
- Parallel worker groups: consecutive phases with the same `parallel:` label run concurrently, gate independently, and use isolated workspaces under `workspace/.phases/<phase>` to avoid write conflicts.
- `evals/operability.yaml` with v0.5 red-then-green scenarios for approval-policy execution and parallel phase isolation.

### Changed

- `EventLog.emit` and `Budget.charge` are lock-guarded so concurrent phases preserve a valid hash chain and consistent spend accounting.

### Tests

- 141 passed, 4 skipped locally; eval scorecard 29/29.

## 0.4.0 (2026-07-07)

### Added

- Linux sandbox backends in `harness/sandbox.py`: bubblewrap (preferred: read-only root, workspace-only writes, private `/tmp`, `--unshare-net`, `--die-with-parent`, `--new-session`), firejail (alternate), docker (fallback, non-root, `--network none`, image override via `HARNESSIE_SANDBOX_IMAGE`). Each admitted only after a startup smoke test; present-but-unusable backends fail closed.
- Policy-construction unit tests for backend preference order, per-backend confinement flags, network opt-in, and Linux fail-closed; the escape parity tests accept the bwrap read-only-root kernel phrasing.
- GitHub Actions CI: Linux bubblewrap parity job (asserts the backend is admitted, not silently skipped), macOS job, and a no-backend job asserting fail-closed.
- SECURITY.md backend table: platform, backend, confinement primitive, known gaps.
- README: "What governs a run" (decision-to-file table) and "When a run halts" (stop-condition-to-operator-action table), from the clarity-conformance audit's two highest-leverage fixes.
- Opt-in live provider scorecard infrastructure (`harness/live_scorecard.py`, `tests/live/`, `harnessie eval --live`): discovers Anthropic and local OpenAI-compatible targets, skips visibly without `HARNESSIE_LIVE=1` or provider configuration, and runs direct, verifier, tool-loop, consent-loop, and consent-lock rows under explicit operator opt-in.
- Trust-bundle manifest integrity (`docs/MANIFEST.yaml`, `harness/trust_manifest.py`, `harnessie verify-manifest`): pins SHA-256 hashes for the public machine-readable trust/discovery files and fails on drift or path escape.

### Security

- SEC-001 (A04, from the 2026-07-06 security audit): prior-phase reports are prior-model output and are now run through the quarantine filter (`guard_result`) before substitution into the next phase's task, exactly as `read_file` results are — flagged content is fenced as data-not-instructions and an `injection_flag` event is emitted. The operator `goal` is never fenced. Closes the asymmetry where inter-phase report text reached the next phase's prompt unfiltered. Audit reports under `audits/`.

### Tests

- 136 passed, 4 skipped locally; eval scorecard 27/27. The extra skipped test is the live-provider pytest path, which is intentionally visible in a keyless environment.

## 0.3.3 (2026-07-06)

Mitigation patch for the three findings from the v0.3.2 verification rotation (independent Claude review of the Codex implementation).

### Changed

- `refusal` events now carry `detail` and `why` (truncated at 300 chars) beside `error` and `boundary`, so audit consumers and the eval checker never parse the 300-char-truncated `tool_result` content. `expect_refusal.content_fields` is asserted against the `refusal` event.
- The stuck detector counts policy refusals regardless of the `ok` flag: three consecutive identical refused calls end the loop as `stuck`. `run_shell` denials keep their `ok=True` observation semantics for the model (the v0.3.2 exclusion holds), but can no longer spin the loop until `max_steps`. Operator-authorized semantic change; new governance scenario `risky_repeated_identical_denial_ends_stuck` covers it.
- `find_secrets` returns kind labels (`perplexity_key`, `anthropic_key`, ...) instead of the first 12 characters of the matched value, so secret-write refusal details carry no credential fragment into model observations or the audit timeline.

### Tests

- 125 passed (was 120 on this host); governance scorecard 14/14; unit coverage for kind-label secrecy, refusal-streak stuck detection, streak reset on success, and `detail`/`why` on `refusal` events.

## 0.3.2 (2026-07-06)

Structured refusal and identifier patch approved under the v0.3.2 one-day cap in `decisions/AIDR-0002`.

### Added

- Structured refusal grammar for tool denials: `ToolResult.refusal` carries `{error, boundary, detail, why}`, and refusal content is emitted as single-line JSON for model observations.
- `ToolRefusal` threading for workspace jail, ownership, operator-lane, and secret-write denials so policy refusals are not collapsed into generic tool exceptions.
- `refusal` events in the hash-chained event stream and rendered governance audit timeline, with `tool`, `error`, `boundary`, `agent`, and `role`.
- `harness/ids.py`, vendored from HardGuard25's 25-character human-safe alphabet with Mod-25 check digit.
- Human-readable checked refs for run-id suffixes, `request_change` events and messages, and generated decision-record frontmatter.
- Governance eval assertions for structured refusals, including the consent lock and a `run_shell` allowlist denial.

### Changed

- `run_shell` allowlist, argument jail, and sandbox-unavailable denials now return the structured refusal JSON while preserving `ok=True` loop semantics.
- Denial tests now assert structured error and boundary values instead of brittle prose substrings.
- Generated decision records keep deterministic filenames for resume safety while adding a separate `ref: DR-...` field.

### Tests

- 117 passed, 3 skipped locally; eval scorecard at 26/26 scenarios.

## 0.3.1 (2026-07-06)

Coherence patch following an adversarially verified sweep of the v0.2/v0.3 release sequence. Fix-first only; no new features.

### Fixed

- GOVERNANCE.md §4 documented a stance vocabulary (`support`) the code rejects; corrected to the implemented `recommend|oppose|alternative|abstain` with convergence = all `recommend`, and the `independent-positions` criterion corrected from distinct model_ids to distinct providers.
- v0.3 audit-timeline defect: `approval_granted`, `approval_denied`, `operator_action`, `fact_saved`, and `fact_expired` events reached events.jsonl but were filtered out of the rendered `harnessie audit` timeline. Fixed eval-first (red scenario `audit_timeline_shows_operator_and_memory_events` + red test, then `GOVERNANCE_KINDS` extended and both stale enumerations updated).
- NEXT.md moved out of `docs/` (the declared future GitHub Pages tree) to the repo root; references updated.
- Documentation drift swept: suite-count corrections, EVALS.md kind contract and live-scorecard version, IMPLEMENTATION_PLAN milestone reference, SECURITY.md layer 7 control description, INTENT.md GuideCheck conditional, README layout, stale assistant-guide.txt verification anchors.

### Tests

- 115 tests, 25/25 eval scenarios (audit-timeline scenario added to the governance suite).

## 0.3.0 (2026-07-06)

The aggregated-intelligence release: the operator enters the audit stream, and project memory becomes self-maintaining substrate. Operator-directed; tenets-to-mechanics mapping in `GOVERNANCE.md` §7; direction record `decisions/AIDR-0002` (open, awaiting arbitration). Portability displaced a second time, to 0.4.0 — the roadmap now flags that a third displacement should be declined absent operator arbitration.

### Added

- Operator actions in the audit stream: per-phase approval handling emits `approval_granted` / `approval_denied` events (with their source), and a resume that detects human arbitration emits `operator_action`. The audit timeline is one composite record of agents and human, not an agent log with invisible human edits.
- `approve_tools:` workflow phase key — the operator's recorded pre-approval for approval-gated tools, granted through the operator-owned workflow file, journaled, and restored to default-deny the moment the phase ends.
- Memory as substrate (`harness/memory.py`): facts carry `verified` / `verify_by` freshness dates (default 30 days) plus stamped provenance; `stale_facts()` surfaces expiry by date; `archive_fact()` moves to `memory/archive/` with a dated reason — deletion does not exist at this layer; `lint()` checks index/fact/provenance consistency.
- Memory tools: `save_fact` (provenance stamped by the harness from run + agent — any agent-claimed source is ignored) and `expire_fact` (requires approval; archival-only). Both side-effecting, so consent-gated like every write.
- `inject_memory_status:` phase key — a deterministic, harness-prepared digest (index, stale facts, recent run outcomes) injected into the task, keeping memory and `runs/` outside every agent's read surface.
- `memory_lint:` verify key — an in-process deterministic gate check, proofed and evented like shell checks.
- `workflows/memory-triage.yaml`: the scheduled maintenance-agent pattern under enforcement — harvest run lessons into facts, refresh or archive stale facts, propose-only when approval is absent; routed to the local tier by design.
- Eval kind `triage` + `evals/triage.yaml` (golden: recorded approval applies expiry; risky: headless is propose-only; recovery: lint failure halts), written red first.

### Changed

- Gate `needs_human` reports now carry the last verdict's evidence instead of a generic message.
- `GOVERNANCE.md` gains §7 (aggregated-intelligence tenets mapped to mechanics); `ROADMAP.md` re-themed: 0.3 tenets+triage, 0.4 portability, 0.5 operability.

### Tests

- 14 new tests across `test_memory_tools.py` and `test_triage.py`; suite at 114 passing, eval scorecard at 24 scenarios (all mock-brain, no network).

## 0.2.0 (2026-07-06)

The governance release: adversarial collaboration and evals promoted to foundational principles, importing the shipped lessons of Turnfile (consent-based coordination, ownership lanes, maintainer authority) and AIDR (independent positions, preserved dissent, human-only arbitration, earned claims) as harness-enforced mechanics. Design rationale: `GOVERNANCE.md`; direction record: `decisions/AIDR-0001` (open, awaiting arbitration). Displaces the previously roadmapped portability theme to 0.3.0.

### Added

- Consent-based orchestration: worker task packets are offers. Side-effecting tools stay locked until `accept_task`; `decline_task(reason, counter_proposal?)` is a first-class `declined` stop. The gate re-offers once on a counter-proposal and never escalates the route on a decline. Enforced at registry dispatch; worker phases default `consent: true` (opt out per phase).
- Ownership lanes (`harness/ownership.py` + root `OWNERSHIP.yaml`): agents own the files they create; cross-agent writes are refused at dispatch with a `request_change` remedy; operator lanes are locked to all agents; collaborative lanes are shared. The ledger lives outside the workspace jail so no agent can edit its own permissions.
- Adversarial contested phases (`harness/adversarial.py`, workflow `mode: adversarial`): independent read-only positions across configurable brains, bounded objection rounds, harness-assembled AIDR-shaped decision records under `runs/<id>/decisions/` with structurally earned claims (`independent-positions`, `dissent-preserved`, `human-arbitrated`). Contested outcomes halt as `needs_arbitration`; the operator arbitrates by editing the record in their own words and resuming. No agent and no harness code path writes the Arbitration section.
- Tamper-evident audit (`harness/audit.py`): events.jsonl is hash-chained (`seq`/`prev` per event, chain survives resume); `harnessie audit <run_id>` verifies the chain and renders the governance timeline (exit 1 on a broken chain).
- Governance eval suite (`evals/governance.yaml`, 11 scenarios as shipped in 0.2.0) plus new eval kinds (`ownership`, `adversarial`, `audit`, consent-flagged `loop`), written red before the implementation per the eval-first change discipline.
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

- Live-endpoint smoke tests, golden-task eval scorecard, interactive approval handler, parallel workers, a Linux sandbox backend, tool plugins. Sequenced into 0.2.0 / 0.3.0 / 1.0.0 milestones in the roadmap; Linux support is the 0.2.0 headline. [Historical note: portability was later displaced to 0.4.0 by the governance (0.2.0) and aggregated-intelligence (0.3.0) releases.]
