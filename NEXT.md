# Next session handoff

## Current state

Harnessie is at v0.5.0 locally after the Codex v0.5 operability pass. The branch is ahead of `origin/main`; do not assume it has been pushed.

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

- `python3 -m pytest -q`: 141 passed, 4 skipped.
- `python3 -m harness.cli eval`: 29/29 passed.
- `python3 -m harness.cli verify-manifest`: passed, 7 files.
- `python3 -m harness.cli eval --live`: keyless/no-endpoint skip path should still return 0/0 with explicit `SKIP` rows unless live env vars are set.
- Scrub check and `git diff --check` still need to be run after any final edits/commit.

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

- Grow `harnessie init` into guided first run: Python check, sandbox-backend detect, env-var API-key walk-through, ends on a green zero-dollar mock-brain run.
- Plain-language operator surface: `harnessie report` and halt messages should self-explain with one named next action.
- Pre-run cost preview; refuse to start a live run when no ceiling is set.
- Non-developer quickstart + glossary; honest Windows/WSL2 page.
- Threat-model comparison artifact: SECURITY.md properties vs prevailing harness failure modes, each row citing enforcing code and tests.
- Default-deny posture audit extending `tests/test_repo_configs.py`.
- GuideCheck content rewrite of `assistant-guide.txt` to Level 3+ and manifest sidecar prep; end-to-end `.well-known` verify waits for Pages.
- Graceful Boundaries conformance check and citation/gap list.
- PyPI packaging prep only; publishing is an operator act.

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
