# Next session handoff
## Current state
Harnessie is at v0.3.3 on `main`. The v0.3.2 verification rotation (independent Claude review of the Codex patch) confirmed the implementation and surfaced three findings; v0.3.3 mitigates all three:
- `refusal` events carry `detail` and `why`; the eval checker asserts `content_fields` on the `refusal` event and never parses truncated `tool_result` content.
- The stuck detector counts policy refusals regardless of the `ok` flag; `run_shell` denials keep `ok=True` observation semantics but can no longer spin the loop (operator-authorized semantic change, governance scenario `risky_repeated_identical_denial_ends_stuck`).
- `find_secrets` returns kind labels, never credential value fragments.
0.4 portability is underway: Linux sandbox backends (bwrap preferred, firejail, docker; startup smoke tests; fail closed when unusable) plus a CI matrix (`.github/workflows/ci.yml`: Linux bubblewrap parity with the backend asserted admitted, macOS, no-backend fail-closed) are committed. CI has not run yet — it needs a push, which awaits the operator.
## Verification status
- `python3 -m pytest -q`: 131 passed on this host (macOS; 3 formerly-skipped sandbox tests run here).
- `python3 -m harness.cli eval`: 27/27 (includes 14 governance scenarios).
- Scrub grep against staged diffs: clean on every commit.
## Next unblocked work (0.4 remainder)
- Push and prove the CI matrix green; treat a red Linux job as the top priority.
- Live-endpoint smoke tests (one loop turn against a real Anthropic endpoint and one local OpenAI-compatible endpoint, opt-in by env var). Implementation step 11.
- Scorecard expansion against real endpoints, including the governance suite per brain. Steps 11-12.
- Live contested phase across two real providers on `workflows/contested-decision.yaml`.
- Trust-bundle MANIFEST integrity.
## Standing task
Skills and runbook inventory (ROADMAP standing task, Claude-session scoped): preliminary shortlist at `handoffs/skills-inventory-preliminary.md` (local, gitignored). Full pass should verify, extend, and produce the decision-ready shortlist.
## Non-goals standing
- No public promotion work yet.
- No annotated tags or release checklist ceremony until public promotion.
- No gated third-party names on tracked surfaces; scrub staged diffs before every commit using `handoffs/scrub-list.txt`.
- Provisional tenets claims remain provisional wherever cited.
## First commands for the next agent
- `git status --short --branch && git log --oneline -8`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
