# Next session handoff

## Current state

Harnessie is at v0.6.0 (first-harness-readiness line): the repo and the canonical page (harnessie.com) are public, and the 0.6.0 release is cut in `CHANGELOG.md`, `pyproject.toml`, the landing page, and `assistant-guide.txt`. Two 0.6 acceptance items close as follow-ups now the site is live: the Siteline live-page bar (hero CTAs sharpened; re-scan after Pages redeploys) and GuideCheck (`.well-known` pair + Level 3+ rewrite, in progress).

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

Public surface (staged under prepare-and-stage; NOT live):
- Landing page `docs/index.html` at canonical `harnessie.com` plus crawler/discovery files. Version text now says v0.5.0.
- Brand assets remain staged only; Pages/DNS/public promotion is still an operator action.
- `docs/MANIFEST.yaml` was refreshed after `assistant-guide.txt` count updates.

## Verification status

Current (after the 0.6 first-harness-readiness work):
- `python3 -m pytest -q`: 189 passed, 1 skipped.
- `python3 -m harness.cli eval`: all PASS (default, `evals/operability.yaml`, `evals/stewardship.yaml`, `evals/redteam.yaml`).
- `python3 -m harness.cli verify-manifest`: passed, 7 files.
- `python3 -m harness.cli eval --live`: keyless/no-endpoint skip path returns 0/0 with explicit `SKIP` rows unless live env vars are set. Confirmed.
- `git diff --check`: clean.
- Scrub check still needs to be run before any commit that stages public surface.

## Known limits

- Budget ceiling is a soft cap across a parallel worker group, not a hard one. Each parallel phase gets a fresh `Budget` seeded with the full run ceiling (`harness/runner.py` `_run_parallel_phase`), blind to already-spent run total and to sibling phases running concurrently. A group entered near the ceiling can collectively overshoot the global budget by up to ~(N-1)x the ceiling before the merge-back via `Budget.add_spend` reconciles the run total. Post-merge accounting is coherent and the hash-chain audit is intact; only mid-group enforcement is loose. `phase_start_usd`/`phase_start_tokens` in `_run_parallel_phase` are captured but unused (each phase budget starts at zero). Fix path when hardened: seed each phase budget with remaining headroom (`max - spent`), or check `self.budget.exhausted` before submitting the group. Tracked as budget-safety hardening under 0.6.0; not a launch blocker given per-phase ceilings already bound a single runaway.

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
5. Publish to PyPI only after the 0.6 launch gate closes.
6. Run the live Siteline scan only after the site is live.

## Next unblocked engineering work

### 0.6.0 headless subset

- Grow `harnessie init` into guided first run: Python check, sandbox-backend detect, env-var API-key walk-through, ends on a green zero-dollar mock-brain run. DONE 2026-07-07: `harness/firstrun.py` + `init` wiring (readiness report, zero-dollar baseline run, named next commands; `--no-verify` to skip); proven by `tests/test_firstrun.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Plain-language operator surface: `harnessie report` and halt messages should self-explain with one named next action. DONE 2026-07-07: `harness/explain.py` + CLI wiring (`run`/`resume` summary, plain `report` with `--raw` fallback); each halt names one command; proven by `tests/test_explain.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Pre-run cost preview; refuse to start a live run when no ceiling is set. DONE 2026-07-07: `harness/preflight.py` + CLI wiring + `tests/test_preflight.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Non-developer quickstart + glossary; honest Windows/WSL2 page. DONE 2026-07-07: `docs/quickstart.md` (init→run→report flow, 19-term glossary, Windows/WSL2 section), linked from README + getting-started; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Threat-model comparison artifact: SECURITY.md properties vs prevailing harness failure modes, each row citing enforcing code and tests. DONE 2026-07-07: `docs/threat-model.md` (11 rows, 25 cited test nodes all passing), linked from README + SECURITY.md; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- Default-deny posture audit extending `tests/test_repo_configs.py`. DONE 2026-07-07: 11 assertions over the shipped registry, OWNERSHIP.yaml, and CLI seams; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- GuideCheck content rewrite of `assistant-guide.txt` to Level 3+ and manifest sidecar prep; end-to-end `.well-known` verify waits for Pages. (Stale expected-results block refreshed 2026-07-07 and manifest re-pinned; the Level 3+ structural rewrite is still open.)
- Standing "break it" invitation. DONE 2026-07-07: `SECURITY.md` disclosure path (GitHub private vulnerability reporting) + "Break it" section publishing `evals/redteam.yaml` (3 canary-exfiltration scenarios, new `expect_events_absent` loop expectation); see CHANGELOG Unreleased and ROADMAP 0.6.0 Safety. End-to-end GHSA flow verifiable only once the repo is public.
- Graceful Boundaries conformance check and citation/gap list. DONE 2026-07-07: transport-adapted GB adoption (Level 1 grammar MET across all denial sites, Action Boundaries vocab aligned, SC-16 met, HTTP Levels 2-4 N/A); cited in GOVERNANCE.md §8 + INTENT.md §7, proven by `tests/test_graceful_boundaries.py`; see CHANGELOG Unreleased and ROADMAP 0.6.0.
- PyPI packaging prep only; publishing is an operator act.

### 0.7.0 planned (post-launch, design gated)

ROADMAP.md now carries a full 0.7.0 section: sovereignty cascade routing (policy scoping over the existing reformulate/effort/tier gate ladder, containment-constrained ladders, sideways provider fallback distinct from upward escalation, sovereign tier slot, routing_trace) plus a containment boundary (deterministic PII strip/rehydrate adapted from PAICE.work PBC production code, a stricter secrets class with tool-output scrubbing, per-tool rehydration grants on the approval-policy grammar) and its eval-shaped proof (canary leak evals, gate-integrity canaries, bundle-identity proven-brain claims). Implementation does not start until the 0.6 launch gate closes AND an adoption AIDR runs through `workflows/contested-decision.yaml` with human arbitration. Fuller planning context is in the operator's private planning note.

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
