# Next session handoff

## Current state

Harnessie is at v0.4.0 locally after the Codex rotation-2 0.4 headless-buildable pass. The worktree has not been committed by Codex in this session.

Engineering:
- v0.4.0 portability is in: Linux sandbox backends (bwrap preferred, firejail, docker fallback), backend startup smoke tests, fail-closed behavior when no backend is usable, and the CI matrix from the prior rotation.
- v0.4.0 proof infrastructure is in: `harness/live_scorecard.py`, `tests/live/`, and `harnessie eval --live` provide opt-in live scorecards for Anthropic and local OpenAI-compatible targets. A keyless/no-endpoint environment skips visibly with `SKIP` rows and makes no provider calls.
- Live scorecard rows cover direct completion, verifier JSON, tool-loop completion, consent-loop completion, and the locked-side-effect boundary. Token/cost display is included when provider usage is reported.
- Trust-bundle MANIFEST integrity is in: `docs/MANIFEST.yaml` pins the SHA-256 hashes for public machine-readable trust/discovery files; `harnessie verify-manifest` and `tests/test_trust_manifest.py` verify drift and tamper detection.
- Version metadata is bumped to 0.4.0 in `pyproject.toml` and `harness/__init__.py`; `CHANGELOG.md`, `ROADMAP.md`, `IMPLEMENTATION_PLAN.md`, `EVALS.md`, README, and user docs are updated.

Public surface (staged under prepare-and-stage; NOT live):
- Landing page `docs/index.html` at canonical `harnessie.com` plus crawler/discovery files (favicon, CNAME, sitemap, robots.txt with AI/SEO allowlist, llms.txt, site.webmanifest, 404). Light theme built around the mascot; copy rewritten for newcomers and developers both; the tenets appear as four plain-language guarantees.
- Brand: `brand/` (repo root, unserved) holds the source image/video; `docs/imgs/` holds only web-optimized derivatives. Provenance in `brand/README.md`.
- User docs: `docs/getting-started.md`, `docs/GUIDE.md`, `docs/brains.md`.
- PostHog remains wired into the landing page but dormant until Pages serves it.

## Verification status

- `python3 -m pytest -q`: 136 passed, 4 skipped.
- `python3 -m harness.cli eval`: 27/27 passed.
- `python3 -m harness.cli verify-manifest`: passed, 7 files.
- `python3 -m harness.cli eval --live`: passed as keyless/no-endpoint skip path, 0/0 with explicit `SKIP` rows for Anthropic and OpenAI-compatible targets.
- Scrub check over tracked diff and new tracked-candidate files: clean.
- `git diff --check`: clean.

## Operator-attended steps ready and waiting

These remain outside Codex's headless authority:

1. Run live provider smokes when ready:
```bash
HARNESSIE_LIVE=1 \
HARNESSIE_OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1 \
python3 -m harness.cli eval --live
```
2. Run the live contested phase across two real providers on `workflows/contested-decision.yaml` if you want a real `independent-positions` record for the 0.4 proof trail.
3. Enable GitHub Pages: `main` branch, `/docs` folder. Verify with the GitHub API.
4. DNS for `harnessie.com` at the registrar. `docs/CNAME` is already in place.
5. Make the repo public, if that remains the launch choice.
6. Verify PostHog on the live page with a PostHog login.
7. Publish to PyPI only as a deliberate release act after the 0.6 launch gate closes.
8. Run the live Siteline scan only after the site is live.

## Next unblocked engineering work

### 0.5.0 operability

- Interactive approval handler: TTY prompt plus a headless allow/deny policy file; per-phase cost display. Implementation step 13.
- Parallel workers: independent phases fan out with per-phase workspaces. Implementation step 14.
- Exit bar: a `requires_approval` tool blocks headless by default and proceeds only under policy; two independent phases run concurrently, gate independently, and beat sequential wall-clock.

### 0.6.0 headless subset after 0.5

- Grow `harnessie init` into guided first run.
- Plain-language halt/report surface.
- Pre-run cost preview; refuse live runs without ceilings.
- Non-developer quickstart + glossary; honest Windows/WSL2 page.
- Threat-model comparison artifact citing enforcing code and tests.
- Default-deny posture audit extending `tests/test_repo_configs.py`.
- GuideCheck content rewrite + manifest sidecar prep; end-to-end `.well-known` verify waits for Pages.
- Graceful Boundaries conformance check and citation/gap list.
- PyPI packaging prep only; publishing is an operator act.

## Non-goals standing

- No Pages/DNS/public-repo/PyPI promotion from a headless agent session.
- No unattended live-provider calls.
- No external mention of Harnessie before operator launch.
- No agent-authored or edited Arbitration sections.
- No annotated tags or release-checklist ceremony until public promotion.
- Do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, `workspace/`, or `ROADMAP-PRIVATE.md`.
- Private planning notes for this repo live in `ROADMAP-PRIVATE.md` at repo root (gitignored, not tracked); its contents are never referenced from any tracked file beyond this line.

## Private review lane

`handoffs/HANDOFF-GEMINI.md` is populated for an optional Gemini 3.5 Flash review of the 0.4.0 patch shape, especially live-scorecard skip policy, manifest scope, and whether docs honestly distinguish implemented infrastructure from operator-attended live proof.

## First commands for the next agent

```bash
git status --short --branch && git log --oneline -8
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli eval --live
```
