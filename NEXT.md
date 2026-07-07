# Next session handoff
## Current state
Harnessie is at v0.3.3 on `main`, pushed. Two bodies of work this cycle: core harness engineering, and a full public-facing surface built under an operator-authorized "prepare and stage" posture (everything staged, nothing live: GitHub Pages is still off).

Engineering:
- v0.3.2 verification rotation confirmed the Codex patch and surfaced three findings; v0.3.3 mitigates all three (refusal events carry `detail`/`why` and the eval checker asserts on the event not truncated `tool_result` content; the stuck detector counts policy refusals regardless of the `ok` flag; `find_secrets` returns kind labels, never value fragments).
- SEC-001 (from this cycle's security audit): inter-phase reports now pass through the quarantine filter before task substitution, like `read_file` results.
- 0.4 portability: Linux sandbox backends (bwrap preferred, firejail, docker; startup smoke tests; fail closed when unusable) plus `.github/workflows/ci.yml`. The CI matrix is GREEN on a real run (2026-07-07): macOS, Linux bubblewrap parity, and no-backend fail-closed all pass. The first run caught one macOS-hardcoded test (`test_wrap_returns_sandbox_prefixed_argv` asserted `sandbox-exec`); fixed to assert the admitted backend. This is the 0.4 portability acceptance met on a real run. Non-blocking annotation: the checkout/setup-python actions still target Node 20 (auto-forced to Node 24); bump the action versions when convenient.

Public surface (staged under prepare-and-stage; NOT live):
- Landing page `docs/index.html` at canonical `harnessie.com` plus crawler/discovery files (favicon, CNAME, sitemap, robots.txt with AI/SEO allowlist, llms.txt, site.webmanifest, 404). Light theme built around the Nessie mascot; copy rewritten for newcomers and developers both; the tenets appear as four plain-language guarantees.
- Brand: `brand/` (repo root, unserved) holds the source `harnessie2.png` and `harnessie_og.mp4`; `docs/imgs/` holds only web-optimized derivatives (`harnessie-mark.png`, `og.png`, `harnessie-hero.mp4`). Provenance in `brand/README.md`.
- Hero is the animated clip (autoplay once, no loop, accessible pause/replay control, reduced-motion aware). 404 is themed with a Nessie-myth joke.
- User docs: `docs/getting-started.md` and `docs/GUIDE.md`.
- PostHog wired into the landing page: cookieless (`persistence: 'memory'`, no cookies/storage), `identified_only`, masked session recording, pointed at Harnessie's dedicated project (US cloud). Fires only once Pages serves the page.
- Repo polish: `CONTRIBUTING.md` and `.github/` issue+PR templates.
- Audit reports from this cycle in `audits/` (security, repo-standards, clarity). All accessibility passes are axe-core clean (0 violations).
## Verification status
- `python3 -m pytest -q`: 133 passed.
- `python3 -m harness.cli eval`: 27/27 (includes 14 governance scenarios).
- Landing page + 404: axe-core WCAG 2.1 AA clean (0 violations).
- Scrub grep against staged diffs: clean on every commit.
## Go-live steps (operator, interactive — not doable headless)
1. Enable GitHub Pages: `main` branch, `/docs` folder. Verify `gh api repos/snapsynapse/harnessie/pages`.
2. DNS for `harnessie.com` at the registrar (A records to GitHub Pages IPs, or CNAME); the `docs/CNAME` file is already in place.
3. Make the repo public (or keep private; Pages serves publicly either way once enabled).
4. Verify PostHog: visit the live page, confirm a pageview lands in the dedicated Harnessie project (needs a PostHog login). Optionally set up dashboards.
5. On promotion, the standard release path applies (annotated tag, RELEASE_CHECKLIST, CI-gate-before-tag) per INTENT §8.
## Next rotation

The full task ladder for the next steward (0.4 remainder, then 0.5, then the 0.6 headless subset, with per-rung exit criteria and the operator gates) is in `handoffs/HANDOFF-CODEX.md` (gitignored), rewritten 2026-07-06 for stewardship rotation 2.

## Next unblocked engineering work (0.4 remainder)
- CI matrix is green on a real run (done). Optional: bump checkout/setup-python action versions to clear the Node 20 deprecation annotation.
- Live-endpoint smoke tests (one loop turn against a real Anthropic endpoint and one local OpenAI-compatible endpoint, opt-in by env var). Step 11.
- Scorecard expansion against real endpoints, including the governance suite per brain. Steps 11-12.
- Live contested phase across two real providers on `workflows/contested-decision.yaml`.
- Trust-bundle MANIFEST integrity.
## Non-goals standing
- Promotion PREP is done and staged; going LIVE (Pages/DNS/public) is a deliberate operator step, not yet taken.
- No annotated tags or release checklist ceremony until that promotion.
- No gated third-party names on tracked surfaces; scrub staged diffs before every commit using `handoffs/scrub-list.txt`.
- Provisional tenets claims remain provisional wherever cited.
- Private planning notes for this repo live in `ROADMAP-PRIVATE.md` at repo root (gitignored, not tracked); its contents are never referenced from any tracked file beyond this line.
## First commands for the next agent
- `git status --short --branch && git log --oneline -8`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
