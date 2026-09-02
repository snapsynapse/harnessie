# Changelog

All notable changes to Harnessie are recorded here. Format loosely follows Keep a Changelog; versions follow semver.

## Unreleased

No unreleased changes.

## 1.2.0 (2026-09-01)

Theme: verify agent-produced changes. Harnessie makes its standalone verifier the smallest useful adoption surface, with evidence-bound intake and deterministic claim coverage, while preserving the full governed harness as the growth path.

### Added

- A direct OpenAI Responses API adapter supports current OpenAI reasoning models with function tools, including high reasoning effort, stateless encrypted-reasoning replay, strict response validation, and usage accounting. The existing `openai-compat` adapter remains the Chat Completions path for Ollama, vLLM, and compatible endpoints.
- Standalone verification accepts a v1 evidence bundle as an alternative to raw criteria. Bundles bind stable claim IDs to an exact Git revision and dirty state, content-addressed diffs and proof files, and recorded deterministic checks; unsafe paths, stale revisions, missing files, and hash drift refuse before model dispatch.
- Verifier verdicts support structured claim results (`reproduced`, `refuted`, or `not_verifiable`) with deterministic overall status and exact claim-coverage checks. Legacy boolean verdicts remain parseable for 1.x compatibility.
- Deterministic Ringer-derived fixtures, event-trace metrics, and a governance recovery case cover the failure modes exposed by the first current-head adoption cohort.
- Live scorecards can exercise OpenAI Responses models, including a high-effort reasoning-plus-tools continuation smoke.

### Fixed

- Parallel copies of the same denied tool call now count as one failed turn for stuck-loop detection, allowing a verifier to recover on its next turn without weakening the tool allowlist.
- The standalone verifier prompt now names its exact shell allowlist and directs agents to use `read_file` for staged diffs, reducing avoidable denied calls.
- Child-process checks ignore operator-wide Git configuration, preventing global signing, hooks, aliases, or credential helpers from contaminating verification fixtures.
- Release artifact inspection again loads private scrub patterns from `.private-controls/scrub-list.txt`, with a regression test that prevents the path from drifting back to the temporary handoff queue.

### Verified

- The composed release gate passes 493 tests with one environment-dependent skip, 51/51 deterministic evals, all nine shipped authoring documents, both manifests, ecosystem and generated-doc validation, isolated wheel and source builds, `twine check`, release-artifact inspection, and a fresh-install smoke from the built wheel.
- The exact release commit, artifact and SBOM digests, publication attestations, and downstream versions are recorded during release closeout in `RELEASE_NOTES-1.2.0.md` and `NEXT.md`.

## 1.1.0 (2026-08-20)

Theme: the Golden Rule becomes inspectable. Harnessie turns its ownership invariant into a memorable public contract, a read-only policy explanation command, and an executable collision proof.

### Added

- Harnessie's Golden Rule for agent work, "Read together. Write only what you own," now has a canonical, falsifiable public explanation connected to the ownership ledger, dispatch denial, child-process read-only overlays, parallel-write preflight, explicit exceptions, and proving tests.
- A read-only `harnessie ownership PATH --agent AGENT [--json]` command explains the exact ledger decision for one agent and workspace path, including the governing lane or first-writer claim, owner, matching pattern, reason, and available remedy. JSON output uses schema version 1. Valid allowed and denied decisions exit 0; invalid paths or ownership documents exit 2.
- `examples/ownership-collision/demo.py` performs a zero-model, zero-network overwrite attempt through the built-in `write_file` registry path and passes only when the second agent receives `ownership_denied` and the first agent's exact artifact survives.

### Fixed

- Search indexing now has repository-owned offline and production contracts, CI checks generated search output, all nine canonical pages carry valid structured data and crawl-visible discovery, and the dated Google Search Console baseline distinguishes intentional redirects and decorative-video noise from defects.
- Documentation and public agent surfaces use the actual `harnessie resume` syntax, name both runtime dependencies, mark the plugin contract stable for 1.x, and report the completed 1.1.0 PyPI, Verify Action v0.1.3, stable `v0`, and Homebrew release train.
- Guide trust copy distinguishes byte-identical repository and served provenance from the independently controlled DNS TXT anchor. After the final 1.1.0 bytes were public, the DNS TXT and repository-file anchors matched and hosted GuideCheck re-earned Level 4 on 2026-08-21 UTC with zero blocking findings.
- Website safety copy now scopes the containment boundary as opt-in, distinguishes configured models from models with earned evidence, and removes unsupported claims that every side effect is interactively approved or that an external delegated operator can be authenticated as human or agent.
- Roadmap, eval-count, sitemap, generated-doc inventory, canonical URL, and website metadata drift were reconciled with the shipped 1.0.0 surfaces.

### Verified

- The composed release gate passes 433 tests with one environment-dependent skip, 50/50 deterministic evals, all six v1 authoring contracts, both manifests, ecosystem and generated-doc validation, isolated wheel and source builds, `twine check`, release-artifact inspection, and a fresh-install smoke that exercises `harnessie ownership` from the built wheel.
- The immutable GitHub and PyPI artifacts share wheel SHA-256 `c400b913fdb9401c8669163532dd23aeccf9800cdb68be48d97831465784a465` and sdist SHA-256 `8a8c6e62348b647b2b9e02ecb1de846160d83ea224e7a467bdde6445d0486ba1`. A public-index consumer exercised the ownership command; Harnessie Verify v0.1.3 passed its four-job matrix before stable `v0` advanced; and Homebrew passed strict online audit, a 1.0.0 to 1.1.0 source upgrade, formula test, linkage, and installed-command smoke.
- Hosted GuideCheck 0.7.1 fetched the 7,947-byte public assistant guide, matched SHA-256 `f7d45f62f2941f5541d1342be0fc037c1ef7fc3e06f44ad39cf94a5b50e5080d` across the sidecar, DNS TXT, and repository-file anchor, and reported Level 4 with zero blocking findings. The two warnings are the known GitHub Pages header limitations for `X-Content-Type-Options` and HSTS.

## 1.0.0 (2026-08-09)

Theme: extensibility earned. Harnessie freezes its authoring contracts, closes the interpreter ownership gap, and admits installed tool extensions through one explicit trust boundary.

### Added

- Six stable Draft 2020-12 authoring schemas now cover models, cascade, boundary, approval-policy, ownership, and workflow documents. `harnessie validate` checks one document or a complete project without starting a run, reports deterministic path and code diagnostics, and performs cross-document checks for roles, tiers, cascade policies, phase references, and placeholders.
- Runtime loaders use the same strict validation contract and fail closed before model dispatch. Project scaffolds and shipped documents declare `schema_version: 1`; schema-less 0.8 documents remain implicit v1 throughout 1.x under the compatibility and deprecation rules in `SCHEMA_COMPATIBILITY.md`.
- Schema JSON ships inside the Python package, is pinned by the inward manifest, and is served byte-identically from `/schemas/v1/` under the public trust manifest. Release artifact checks require the validator and all six packaged schemas.
- Per-lane sandbox profiles close the interpreter ownership gap. Operator lanes, other-agent lanes, and other agents' first-writer claims become conservative read-only overlays for worker shell calls, deterministic checks, and verifier execution. Each backend must separately prove nested read-only enforcement; an invalid pattern or unsupported profile blocks the child process fail-closed. Unowned paths retain existing first-writer behavior.
- Installed tool plugins now use one explicit versioned mechanism: `harnessie.tools.v1` Python package entry points selected with repeatable `--plugin NAME` arguments. Admission validates declarations, namespaces tools, applies the normal registry policy, stamps immutable provenance, and pins exact receipts across resume. Imported implementations are explicitly operator-trusted in-process code; untrusted plugins remain unsupported pending an out-of-process protocol.

### Fixed

- Anthropic and OpenAI-compatible adapters now validate provider response envelopes, tool calls, stop reasons, and usage counters before constructing a turn. Invalid JSON or structurally malformed responses become non-echoing `stop_reason="error"` turns instead of raising into the run, while OpenAI-compatible content-filter finishes normalize to the existing refusal stop.
- Adversarial rebuttal rounds now receive each peer position in full and exclude the reviewing agent's own position by value. This removes the 2,000-character clipping that previously made a complete position appear truncated and could create a spurious standing objection.

### Verified

- The composed release gate passes 413 tests with one environment-dependent skip, 50/50 deterministic evals, side-effect-free authoring validation, both manifests, ecosystem and generated-doc validation, isolated wheel and source builds, `twine check`, packaged-schema inspection, and a fresh-install smoke.

## 0.8.0 (2026-08-04)

Theme: bound what a governed run may change and pin the harness inputs that define its behavior. This release completes the four 0.8 write-safety and self-integrity mechanics, hardens the package gate, and publishes truthful machine handoffs.

### Added

- Public machine handoff resources now describe only Harnessie's shipped local surfaces: `agents.json` declares the review and CLI capabilities plus explicit no-hosted-API/MCP boundaries; `api/v1/index.json` documents the local process interface while explicitly denying a hosted network service; `changelog.json` provides machine-readable release history; RFC 9116 `security.txt` routes private reports; and the landing page and `llms.txt` expose specific support, security, and change-discovery paths. The trust bundle and deterministic tests pin these artifacts and prevent version, boundary, URL-policy, command-contract, or expiry drift.
- A composed pre-release gate now runs source verification, checks generated docs without rewriting them, builds and inspects one wheel and source distribution, rejects unsafe or private archive members, validates SPDX package metadata, and exercises the installed CLI in a fresh virtual environment. CI runs the artifact and install portion on every change.
- `harnessie eval` now refuses an empty suite discovery instead of reporting the vacuous success `0/0 passed`.
- Maiden-voyage protection completes the 0.8 write-safety milestone: worker phases may declare `phase_type`, which fingerprints the complete phase contract. A new or changed contract executes and verifies in an isolated staged clone, with network and non-workspace mutations disabled, then halts as `needs_approval` without changing the target workspace. `harnessie approve-maiden <run_id> <phase>` promotes only when the run audit chain, proposal, staged artifacts, staged ownership ledger, and unchanged target all match their recorded hashes; approval becomes part of the audit and journal, resume skips the promoted worker, and future runs of the exact fingerprint write normally. Parallel and adversarial phase types refuse before dispatch until their distinct promotion semantics are defined.
- The inward manifest's ownership entry pins only static ownership policy, excluding auto-maintained first-writer claims. This preserves self-integrity without making a legitimate first write invalidate the next run.
- Inward self-integrity manifest, the third 0.8 slice: `INWARD_MANIFEST.yaml` hash-pins every shipped role prompt, YAML config, and the static policy portion of `OWNERSHIP.yaml`, and exact coverage catches newly added unpinned inputs. Auto-maintained first-writer claims are excluded from the policy projection. Clean runs emit the manifest hash and file count plus the selected workflow hash. Divergence follows the manifest's explicit `on_divergence` policy: the shipped `refuse` default halts before model dispatch, while `record` preserves an audited local-development escape hatch. A missing manifest remains a legacy-compatible no-op for downstream projects; a present malformed manifest fails closed. Proven by focused tests and a deterministic integrity eval.
- Federated project control plane: `ECOSYSTEM.md` defines authority, repository boundaries, and the two release trains; `ecosystem.yaml` carries the machine-readable topology; and the offline, read-only `scripts/ecosystem_status.py` reports local revisions, versions, downstream pins, and drift without requiring GitHub or a dashboard. The release checklist now propagates core releases through the verify action and Homebrew while keeping probe-gated engine wrappers independent.
- Blast-radius ceilings, the second 0.8 write-safety slice: phases and workflows may declare cumulative `max_files_touched`, `max_edits_applied`, and `max_bytes_written` limits under `blast_radius`. `write_file`, sandboxed shell calls, and deterministic verification commands are measured as atomic filesystem transactions; a breach restores the exact pre-operation workspace, emits the measured count and limit, and halts without retrying or dispatching another tool. Shared run counters are lock-safe across parallel phases and reconstruct from the hash-chained usage events on resume. Invalid or unknown limit fields refuse before model dispatch; workflows that do not opt in retain their prior behavior. Proven by rollback, shell, check, aggregation, invalid-config, and resume tests plus a deterministic operability eval.
- The first 0.8 write-safety slice: parallel phases may declare exact files and directory subtrees with `writes`. Once a group opts in, every member must declare its writes, including `writes: []` for read-only work; malformed, partial, case/Unicode-aliased, or overlapping declarations refuse the whole group before workspace creation or model dispatch and emit a structured event. Declared ownership lanes now remain enforced inside isolated parallel workspaces without treating physically separate phase-local files as one first-writer claim. Proven by parser adversarial tests, runner dispatch-spy tests, ownership tests, and a new operability eval.
- AIDR-0008 has been executed in the separate Apache-2.0 [harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers) repository. Its fresh-authored v0.1.0 macOS Seatbelt reference wrapper admits the backend only after a deny/allow/symlink probe, fails closed on unsupported or unavailable engines, and was release-gated by a live macOS-14 CI probe.
- `harnessie verify` now ships as a GitHub Action, published to the Marketplace as [Harnessie Verify](https://github.com/marketplace/actions/harnessie-verify) (repo: [harnessie-verify-action](https://github.com/snapsynapse/harnessie-verify-action), v0.1.0, adopted via `decisions/AIDR-0007`). This repo dogfoods it: `.github/workflows/verify-pr-claims.yml` verifies every PR's claims once the verifier endpoint variables and secret are configured, and skips politely until then.
- A current handoff-relevance audit classifies every private rotation packet, retires the completed position sweep, reconciles the Homebrew tap and verify-action release channels, incorporates the arbitrated AIDR-0008 separate-repository work, and scopes the 0.8 work order. `NEXT.md` now carries only current state and executable next work; the stewardship eval checks that contract instead of requiring shipped 0.6 headings.

### Verified

- The complete release gate passes 352 tests with 1 environment-dependent skip, 47/47 deterministic evals, outward and inward manifest verification, generated-doc checks, artifact inspection, `twine check`, and a fresh-install smoke test.
- A fresh live Siteline 2.3.0 scan on 2026-08-05 UTC scored the deployed site A, 97/100, with Level 4 machine enablement at 16/18. The response provenance and the result-store residual are recorded in `audits/siteline-live-result-2026-08-05.json`.

## 0.7.1 (2026-07-09)

Theme: the verifier leaves the harness. One addition, adopted through the contested-decision process like everything before it.

### Added

- Standalone verification surface `harnessie verify` (`harness/verify_standalone.py`), adopted via `decisions/AIDR-0006` (four-provider position sweep, human-arbitrated): point the VerificationGate's two layers at any workspace plus a claims file with no project scaffold, orchestrator, or run manifest. Deterministic checks run sandboxed and network-denied (opt-in `--allow-network` for artifacts whose own tests bind sockets; the verifier agent stays denied regardless), then a read-only fresh-context verifier tests the criteria claim by claim. Exit contract is scriptable and fail-closed: 0 verified, 1 failed, 2 cannot-verify (missing config, sandbox unavailable, provider error — neither pass nor fail was earned). Single pass by design: a foreign artifact's failure is the answer, not a prompt to reformulate and retry. The report carries the workspace git revision, criteria hash, verifier model, and network mode. First proving ground: independent verification of agent-produced pull requests. Proven by `tests/test_verify_standalone.py`.

## 0.7.0 (2026-07-09)

Theme: sovereignty cascade routing and the containment boundary. Route every task to the least-exposed environment that can complete it, and make containment a mechanical property of the run rather than an operator habit. The whole milestone — routing layer, boundary, and its eval-shaped proof — was adopted through Harnessie's own contested-decision process: five arbitrated decision records (`decisions/AIDR-0001` through `AIDR-0005`), three of them run on six- and three-model Ollama Cloud panels spanning eight providers. A workflow that does not opt in to any of the new machinery routes byte-identically to 0.6.

### Added

- Containment boundary (`harness/boundary.py`), the data-exposure half of the sovereignty claim, adapted with provenance from PAICE.work PBC production PII code released under Apache-2.0 (see [NOTICE](NOTICE)). Opt-in via `config/boundary.yaml`. Its guarantee is a per-data-class coverage table, not a blanket claim: structured PII is stripped to stable placeholders before any content reaches a model (goal, phase tasks, and tool results), so no model call and no run artifact carries a raw value; secrets are never mapped or rehydrated and a secret in an egress payload halts the run (`secret_egress`, kind labels only, no warn mode); unstructured free-text PII is explicitly not filter-caught and is covered by contained routing (never egresses past the local/sovereign tier set). The strip map lives outside the run tree (`.boundary/<run_id>.json`, 0600), reloads fail-closed on resume, and rehydration happens only at the operator boundary under deny-all per-tool grants. Proven by `tests/test_boundary.py`, `tests/test_boundary_integration.py`, and `evals/canary-leak.yaml` (zero canary bytes in any run artifact); unstructured containment proven by routing in `tests/test_cascade_wiring.py`.
- Placeholder-impact scorecard (0.7 proof suite, the AIDR-0003 round-two claim): the live scorecard gains a per-brain `placeholder_impact` row measuring whether the boundary's placeholder substitution changes the brain's gate parseability (clean prompt vs placeholder-laden prompt), turning "placeholder soup may hurt small models" from an open question into a published number. Verified live: qwen3.6:35b-mlx delta=none.
- Cascade policies wired into the verification gate (0.7 task 2): a workflow phase opts in with `cascade: <policy-name>`; its route starts on the policy ladder's first rung, effort still climbs first within a tier (the 0.6 motion), and tier climbs become the policy's decision via a `cascade_decision` event per climb/hold/exhaust with the plain-language reason. Refusals hold rather than up-tier. An unknown policy name fails closed before any model dispatch with the fix named; a policy naming an unconfigured tier refuses at runner startup. Acceptance proven in `tests/test_cascade_wiring.py`: a workflow without the `cascade` key produces the byte-identical pre-cascade escalation sequence with zero cascade events.
- Sideways provider fallback, escalation headroom, and routing_trace (0.7 task 3): a tier may declare `fallbacks:` in `config/models.yaml` (each inherits the primary's fields and overrides what it names); on a cascade-opted phase, refusals and availability failures (model_error) move sideways to the tier's next fallback — same tier, never upward — before any effort or ladder motion, availability never climbs at all, and a contained policy naming `refusal` in `escalate_on` is a load-time error. A policy-approved climb is refused before dispatch when the remaining run budget cannot cover the target tier's worst-case first turn (`refused_headroom` event with the arithmetic; estimate shape pending the AIDR-0005 arbitration, single-turn floor provisionally). Every attempt now emits a `routing_trace` event (tier, effort, fallback index, model, provider, outcome), and route payloads in existing events stay `{tier, effort}` so 0.6 event shapes are unchanged. Proven by `tests/test_sideways_headroom_trace.py`.
- Gate-integrity canaries (0.7 proof suite): `evals/gate-integrity.yaml` injects the three manipulation shapes the roadmap names — phantom prior context, the autonomy grab, and a counterfeit system frame — into phase inputs via a scripted upstream report, and asserts the shipped pipeline catches them: the quarantine layer emits `injection_flag`, the tainted content is fenced as data, and a worker that obeys the injection still halts `needs_human` at the gate instead of shipping unverified work. The eval framework gains `expect_events_contain`, the positive twin of `expect_events_absent`.
- Bundle identity (0.7 proof suite): a live scorecard result now pins the exact bundle it proves — model, provider, endpoint, prompt tree hash, verdict-parser version (`PARSER_VERSION` in `harness/verify.py`, bumped on any parsing-contract change), and sampling — printed as a `BUNDLE <id>` line and returned in the scorecard payload. `bundle_drift()` names every component that differs between a recorded claim and the current bundle: change control, not drift monitoring. Editing any role prompt, swapping any endpoint, or bumping the parser rotates the bundle and stales the claim (proven by `tests/test_bundle_identity.py`).
- Sovereign tier slot and the reserved pre-gate (0.7 task 4, closing the routing half): `sovereign` is a valid fifth tier in `config/models.yaml` — any OpenAI-compatible controlled endpoint with the same swap-by-config contract — reachable only where policy names it (a routing row or a cascade ladder, where it counts as unexposed for containment). It is deliberately not on the default escalation walk: sovereign is an exposure class, not a capability rung, so automatic escalation never enters or passes a controlled endpoint, and existing configs escalate byte-identically (test-proven). Work classes under `reserved:` in `config/cascade.yaml` never reach any model at any tier — enforced at all three dispatch sites (sequential, parallel, adversarial positions) with the operator action named; `arbitration` ships reserved by default, turning the human-only rule from convention into config. Proven by `tests/test_sovereign_reserved.py`.
- Escalation-headroom estimate finalized via `decisions/AIDR-0005` (three-brain panel: gpt-oss:120b, glm-5, minimax-m3; two rounds, AIDR-0003-style reframe; human-arbitrated): the single-turn worst-case floor ships coupled to the per-turn enforcement invariant — overspend is structurally bounded to ceiling plus one maximal in-flight turn, the floor guarantees an admitted climb's worst first turn fits the ceiling, and the invariant is a passing test (`test_escalated_run_never_exceeds_ceiling_plus_one_turn`) with the input-token proxy limit stated. The panel's objection round earned its keep: fabricated line-number citations in one position were caught by a peer and discounted in arbitration. `glm-5:cloud` and `minimax-m3:cloud` enter the brains.md proven table on this record (eleven models, eight providers). A three-position workflow variant (`workflows/contested-decision-3panel.yaml`) ships.
- docs/brains.md proven table grows from four to nine models and four to eight providers: `gpt-oss:120b-cloud` (OpenAI) and `glm-4.7:cloud` (Z.ai) ran contested phases inside the harness via Ollama Cloud and the openai-compat adapter, and `deepseek-v4-pro:cloud` (DeepSeek), `kimi-k2.5:cloud` (Moonshot), and `minimax-m2.1:cloud` (MiniMax) formed isolated positions — all five backed by the arbitrated AIDR-0003/AIDR-0004 records.
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

### Changed

- Roadmap re-cut ahead of 0.7 delivery: the three write-safety items (blast-radius ceilings, declared-write-path conflict refusal, maiden-voyage propose-only rule) moved from 0.7.0 into a new 0.8.0 "Write-safety and self-integrity" milestone with its own acceptance bar, joined by the inward manifest (hash-pinning the harness's own role prompts and configs). Rationale: they bound write damage rather than data exposure, had no 0.7 acceptance coverage, and are mechanically independent of the routing engine and containment boundary.
- 0.7.0 spec redrafted after its own governance said no: a six-model contested panel (Anthropic, OpenAI, Z.ai, DeepSeek, Moonshot, MiniMax — the first AIDR run on Ollama Cloud brains) split 3-3 on the original design, and the arbitration (`decisions/AIDR-0003`) directed a redraft before adoption. The redraft (`decisions/AIDR-0004`, unanimously adopted) makes the containment claim a per-data-class coverage table instead of a blanket statement, hands the unstructured residual to contained routing, designs the strip-map lifecycle with fail-closed resume, and turns placeholder impact into a published per-brain scorecard number. Escalation-headroom estimate settled the same way in `decisions/AIDR-0005` (three-brain panel, two rounds): the single-turn floor coupled to a per-turn enforcement invariant, ceiling-plus-one-turn bounded, proven by a test.
- Documentation pass for the 0.7 surfaces: ARCHITECTURE.md gains the cascade and boundary subsystems, the `secret_egress` stop condition, the routing and containment sections, and updated eval counts; docs/GUIDE.md gains "Cascade routing and the sovereign tier" and "The containment boundary" sections, the new config files in the governance table, and the `secret_egress` halt row.

### Fixed

- Budget-safety hardening (the 0.6 known limit, now the named 0.7 prerequisite): parallel phases now run on headroom-scoped child budgets (`Budget.child()`) instead of independent copies seeded with the full run ceiling. A child's ceiling is the run's remaining headroom at group start, every charge flows through to the run budget live, and `exhausted` consults the parent — so sibling phases see each other's spend mid-group and a group entered near the ceiling can no longer collectively overshoot by up to (N-1)x the ceiling; overshoot is bounded to model turns already in flight when the ceiling crosses. A parallel phase whose group starts with the run budget already exhausted refuses before any dispatch (`needs_human`, no workspace created, brain never called), and the post-group `add_spend` merge is gone (charge-through replaces it; totals stay coherent with per-phase accounting). Proven by three new `Budget.child()` unit tests and two runner tests.

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
