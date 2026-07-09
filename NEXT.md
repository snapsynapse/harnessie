# Next session handoff

## Current state

Harnessie is at v0.7.0 (sovereignty cascade routing + containment boundary), SHIPPED 2026-07-09: tagged `v0.7.0`, GitHub release published with wheel + sdist attached, and `harnessie 0.7.0` live on PyPI (fresh-install verified from the live index). The whole milestone was adopted through the harness's own contested-decision process (five arbitrated AIDRs, three on six- and three-model Ollama Cloud panels). Routing (cascade policies, sideways fallback, escalation headroom, sovereign tier, reserved pre-gate, routing_trace) and the containment boundary (PII strip/rehydrate, secret egress halt, fail-closed strip-map lifecycle, per-tool rehydration grants, per-data-class coverage table) are both live and opt-in; a workflow that does not opt in routes byte-identically to 0.6. The boundary is vendored under the PAICE.work PBC Apache-2.0 release recorded in NOTICE (sole-director consent on file, July 9). Verification at ship: 255 passed / 1 skipped, 43/43 eval, manifest OK. GuideCheck DNS TXT anchor updated to the 0.7.0 guide hash and confirmed resolving on two resolvers; the hosted Level-4 re-verify against the live `.well-known/` pair is the one remaining operator confirmation (needs Pages to redeploy the served guide). The 0.6 Siteline live-page re-scan remains open from the prior line.

The prior release (v0.6.0, first-harness-readiness) shipped 2026-07-07: repo and canonical page live, on PyPI, GuideCheck Level 4 confirmed.

Engineering:
- v0.4.0 portability/proof remains in: Linux sandbox backends, opt-in live provider scorecards, and trust-bundle manifest integrity.
- v0.5.0 operability is in: headless approval policy files, optional TTY approval prompts, per-phase cost deltas, and parallel worker groups with per-phase workspaces.
- Approval policy shape is intentionally small:
```yaml
allow:
  - tool: expire_fact
    phase: triage
deny:
  - tool: deploy
```
Rules name a `tool` and may name a `phase`; explicit deny wins; no match denies closed. CLI flags: `--approval-policy <path>` and `--approve-interactive`.
- Parallel phases are consecutive workflow phases with the same `parallel:` label. They run concurrently, gate independently, and use `workspace/.phases/<phase>` as their workspace. Later phases receive each phase report by phase name.
- Event logging and budget charging are lock-guarded for concurrent phase execution.

Public surface (LIVE):
- harnessie.com serves the landing page (v0.7.0), the five generated doc pages (quickstart, getting-started, guide, brains, threat-model), the GuideCheck `.well-known/` trust pair, and the crawler/discovery files.
- The HTML doc pages are generated from the markdown by `scripts/build_docs_html.py`; edit markdown, run the script, commit both.
- `docs/MANIFEST.yaml` pins 9 files; `tests/test_guide_artifacts.py` enforces guide-artifact sync.

## Verification status

Current (after the 0.6 first-harness-readiness work):
- `python3 -m pytest -q`: 195 passed, 1 skipped.
- `python3 -m harness.cli eval`: all PASS (default, `evals/operability.yaml`, `evals/stewardship.yaml`, `evals/redteam.yaml`).
- `python3 -m harness.cli verify-manifest`: passed, 9 files.
- `python3 -m harness.cli eval --live`: keyless/no-endpoint skip path returns 0/0 with explicit `SKIP` rows unless live env vars are set. Confirmed.
- `git diff --check`: clean.
- Scrub check still needs to be run before any commit that stages public surface.

## Known limits

- Budget-safety hardening CLOSED 2026-07-07 (was: parallel phase budgets seeded with the full run ceiling, mid-group enforcement loose, up to ~(N-1)x overshoot). Now: `Budget.child()` headroom-scoped child budgets with live charge-through to the run budget and parent-aware `exhausted`; a group entered with the budget already exhausted refuses per-phase before dispatch; the post-group `add_spend` merge is removed. Residual (accepted): overshoot bounded to model turns already in flight when the ceiling crosses — a turn cannot be un-called mid-flight. Proven by `tests/test_routing_verify.py` (3 child-budget tests) and `tests/test_runner.py` (pre-dispatch refusal; no double count). This was the named 0.7 prerequisite; it no longer blocks routing work.

## Operator-attended steps ready and waiting

These remain outside Codex's headless authority:

1. Run live provider smokes when ready:
```bash
HARNESSIE_LIVE=1 \
HARNESSIE_OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1 \
python3 -m harness.cli eval --live
```
2. Run the live contested phase across two real providers on `workflows/contested-decision.yaml` if you want a real `independent-positions` record for the 0.4 proof trail.
3. Enable GitHub Pages, DNS, and public-repo settings only as deliberate operator acts.
4. Verify PostHog on the live page with a PostHog login.
5. Publish to PyPI only after the 0.6 launch gate closes. DONE 2026-07-07: harnessie 0.6.0 on PyPI, verified installable from the live index.
6. Run the live Siteline scan only after the site is live.

## Next unblocked engineering work

### 0.6.0 headless subset

- Grow `harnessie init` into guided first run: Python check, sandbox-backend detect, env-var API-key walk-through, ends on a green zero-dollar mock-brain run. DONE 2026-07-07: `harness/firstrun.py` + `init` wiring (readiness report, zero-dollar baseline run, named next commands; `--no-verify` to skip); proven by `tests/test_firstrun.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Plain-language operator surface: `harnessie report` and halt messages should self-explain with one named next action. DONE 2026-07-07: `harness/explain.py` + CLI wiring (`run`/`resume` summary, plain `report` with `--raw` fallback); each halt names one command; proven by `tests/test_explain.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Pre-run cost preview; refuse to start a live run when no ceiling is set. DONE 2026-07-07: `harness/preflight.py` + CLI wiring + `tests/test_preflight.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Non-developer quickstart + glossary; honest Windows/WSL2 page. DONE 2026-07-07: `docs/quickstart.md` (init→run→report flow, 19-term glossary, Windows/WSL2 section), linked from README + getting-started; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Threat-model comparison artifact: SECURITY.md properties vs prevailing harness failure modes, each row citing enforcing code and tests. DONE 2026-07-07: `docs/threat-model.md` (11 rows, 25 cited test nodes all passing), linked from README + SECURITY.md; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Default-deny posture audit extending `tests/test_repo_configs.py`. DONE 2026-07-07: 11 assertions over the shipped registry, OWNERSHIP.yaml, and CLI seams; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- GuideCheck content rewrite of `assistant-guide.txt` to Level 3+ and manifest sidecar prep; end-to-end `.well-known` verify waits for Pages. DONE 2026-07-07: conforming GuideCheck Level 3 profile (verifier: 0 findings), byte-identical `docs/.well-known/` pair + sidecar manifest, `docs/.nojekyll`, discovery wired (landing/README/llms.txt/pyproject), trust manifest re-pinned (9 files). Level 4 CONFIRMED end-to-end 2026-07-07 (guidecheck-hosted 0.7.0, achieved level 4, 0 blocking) against the live pair + sidecar + independent DNS TXT anchor at `_assistant-guide.harnessie.com`. Reminder: any future guide edit must move five sync points together — root file, `.well-known` copy, sidecar hash, trust-bundle pins (all four test-enforced by `tests/test_guide_artifacts.py`), and the DNS TXT value (manual). See CHANGELOG 0.6.0 and ROADMAP 0.6.0.
- Standing "break it" invitation. DONE 2026-07-07: `SECURITY.md` disclosure path (GitHub private vulnerability reporting) + "Break it" section publishing `evals/redteam.yaml` (3 canary-exfiltration scenarios, new `expect_events_absent` loop expectation); see CHANGELOG Unreleased and ROADMAP 0.6.0 Safety. End-to-end GHSA flow verifiable only once the repo is public.
- Graceful Boundaries conformance check and citation/gap list. DONE 2026-07-07: transport-adapted GB adoption (Level 1 grammar MET across all denial sites, Action Boundaries vocab aligned, SC-16 met, HTTP Levels 2-4 N/A); cited in GOVERNANCE.md §8 + INTENT.md §7, proven by `tests/test_graceful_boundaries.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- PyPI packaging prep only; publishing is an operator act. DONE 2026-07-07: published (operator-authorized in session); `pip install harnessie` is the documented entry.

### 0.7.0 planned (post-launch, design gated)

ROADMAP.md now carries a full 0.7.0 section: sovereignty cascade routing (policy scoping over the existing reformulate/effort/tier gate ladder, containment-constrained ladders, sideways provider fallback distinct from upward escalation, sovereign tier slot, routing_trace) plus a containment boundary (deterministic PII strip/rehydrate adapted from PAICE.work PBC production code, a stricter secrets class with tool-output scrubbing, per-tool rehydration grants on the approval-policy grammar) and its eval-shaped proof (canary leak evals, gate-integrity canaries, bundle-identity proven-brain claims). Scope was re-cut 2026-07-07: the three write-safety bullets (blast-radius ceilings, declared-write-path conflict refusal, maiden-voyage rule) moved to a new 0.8.0 "Write-safety and self-integrity" section together with the inward manifest, because they bound write damage rather than data exposure and had no 0.7 acceptance coverage. The 0.6 budget-safety hardening prerequisite CLOSED 2026-07-07 (see Known limits). GATE SATISFIED 2026-07-07: the adoption decision ran twice through `workflows/contested-decision.yaml` on Ollama Cloud brains — `decisions/AIDR-0003` (six models, six providers, 3-3 split, arbitrated: redraft first), spec redrafted (coverage-table claim scoping, routing owns the unstructured residual, strip-map lifecycle designed, placeholder-impact deltas published), then `decisions/AIDR-0004` (same panel, unanimous recommend, arbitrated: implement; the clean-convergence run `20260707-105241-DUJM8J` completed the workflow end-to-end). Both records lint PASS with independent-positions, dissent-preserved, human-arbitrated. 0.7 implementation is OPEN. Note for the boundary work: vendoring `pii_service.py` -> `harness/boundary.py` requires the PBC written grant recorded in NOTICE before any public commit (operator act, per the standing NOTICE rule). Fuller planning context is in the operator's private planning note.

## Non-goals standing

- No Pages/DNS/public-repo/PyPI promotion from a headless agent session.
- No unattended external live-provider calls.
- No external mention of Harnessie before operator launch.
- No agent-authored or edited Arbitration sections.
- No annotated tags or release-checklist ceremony until public promotion.
- Do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, `workspace/`, or `ROADMAP-PRIVATE.md`.
- Private planning notes for this repo live in `ROADMAP-PRIVATE.md` at repo root (gitignored, not tracked); its contents are never referenced from any tracked file beyond this line.

## First commands for the next agent

```bash
git status --short --branch && git log --oneline -8
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli eval --live
```
