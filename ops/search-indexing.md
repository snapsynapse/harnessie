<!-- Upstream template: portfolio-search-indexing-audit contract v2 -->
---
title: "Search indexing"
purpose: "Property-specific index policy, validation commands, deployment gate, and console follow-up."
status: active
updated: 2026-08-20
owner: "Harnessie maintainers"
open_tasks:
  - "On the next authorized console-maintenance pass, recheck after the Page indexing report advances beyond 2026-08-06 or one of the four requested pages is recrawled."
---
# Search indexing

Canonical origin: `https://harnessie.com/`

Generated output: `docs`

Property type: website

Provider property ID: Google Search Console `sc-domain:harnessie.com`

No Bing property was observed in the 2026-08-09 task. Its existence and state are unknown, not zero.

## Index policy

| Surface | Policy | Reason |
|---|---|---|
| `/`, `/quickstart.html`, `/getting-started.html`, `/ladder.html`, `/guide.html`, `/compare.html`, `/brains.html`, `/threat-model.html`, `/ringer.html` | Index and include in sitemap | Canonical reader destinations with unique titles, descriptions, and crawl-visible internal discovery |
| `/404.html` | `noindex` and omit from sitemap | Error response, not a content destination |
| `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/agents.json`, `/api/v1/index.json`, `/changelog.json`, `/.well-known/*`, `/schemas/v1/*` | Crawlable machine surfaces, omit from HTML sitemap | Discovery, trust, or machine consumption rather than canonical HTML search results |
| Markdown source files under `/docs/` | Omit from sitemap; canonical served HTML remains the index target | GitHub Pages may serve source files, but generated HTML is the reader surface |
| GitHub, PyPI, and other platform copies | Omit from sitemap | External distribution surfaces are not site canonical pages |

## Multilingual policy

Harnessie currently declares no localized route set. Canonical sitemap targets are the English pages listed above. A future translated route must define its own canonical and `hreflang` relationships before entering the sitemap.

## Evidence governance

- This file owns the current property policy, classified state, action ledger, do-not-repeat rules, and next-review conditions.
- Sanitized dated observations live under `ops/search/<provider>/YYYY-MM-DD/`; the current baseline is [`ops/search/GoogleSearchConsole/2026-08-09/summary.md`](search/GoogleSearchConsole/2026-08-09/summary.md).
- Historical observations are append-only evidence. Later provider changes receive a new dated record rather than rewriting the old observation.
- `.playwright-mcp/` and `.search-evidence-private/` are ignored private locations. Never commit account identity, queries, authenticated URLs, exports, screenshots, traces, cookies, profiles, or unreviewed browser artifacts.
- Missing, stale, insufficient, unknown, and zero are distinct states. No export is inferred when only authenticated UI evidence was observed.

## Validation lanes

- Offline: `node scripts/check-search.mjs`
- Production after deployment: `node scripts/check-production-search.mjs`
- Machine-readable output: add `--json`
- Local HTTP test: add `--base=http://127.0.0.1:PORT/`

Exit code `0` is pass, `1` is a site defect, and `2` is configuration or infrastructure failure.

## Deployment and console sequence

1. Run the normal build and offline search contract.
2. Deploy through the repository's normal release path.
3. Wait for the deployment to complete.
4. Run the production search contract.
5. Submit or refresh discovery surfaces only after the production check passes.
6. Inspect or request indexing for canonical HTML pages.
7. Start issue-group validation only when matching production behavior is live.
8. Record console state under `ops/search/<provider>/YYYY-MM-DD/`.

## Expected noise

- `http://harnessie.com/`, `https://www.harnessie.com/`, and `http://www.harnessie.com/` redirect to `https://harnessie.com/`.
- `/404.html` is intentionally `noindex`; arbitrary nonexistent routes return HTTP 404.
- Machine-readable resources are intentionally crawlable but absent from the HTML sitemap.
- Google console observations can predate the repository and production fixes; classify those rows as pending recrawl only after the live contract passes.

## Current baseline

- Repository baseline on 2026-08-09: nine intended canonical HTML pages after adding `/ringer.html`.
- Production after commit `47f7ec3`: nine sitemap pages, 0 contract defects, canonical HTTPS redirects healthy, real 404 behavior healthy, and all sitemap pages carry valid JSON-LD.
- Google Search Console baseline: `ops/search/GoogleSearchConsole/2026-08-09/summary.md`.
- GSC sitemap status: `Success`, last read 2026-08-09, 9 discovered pages.
- Indexing requested for `/guide.html`, `/ladder.html`, `/brains.html`, and `/ringer.html`; all four are pending recrawl.

## Current classified state

| Evidence lane or report | Evidence date | State | Classification |
|---|---|---|---|
| Repository contract | 2026-08-09 | 9 sitemap pages and 0 defects | Pass |
| Production contract | 2026-08-09 | 9 sitemap pages, 0 defects, and 0 infrastructure failures | Pass |
| Page indexing | Report updated 2026-08-06; observed 2026-08-09 | 5 indexed; 3 intentional host or protocol redirects excluded | Redirect exclusions are expected noise; four additional canonical pages are pending recrawl after accepted indexing requests |
| Sitemap | Observed and last read 2026-08-09 | `Success`; 9 discovered pages | Accepted action; do not repeat while healthy |
| Video indexing | Report updated 2026-08-05; observed 2026-08-09 | Decorative homepage video was not indexed | Expected noise |
| Core Web Vitals | Report updated 2026-08-07; observed 2026-08-09 | Insufficient field data on mobile and desktop | Unknown due to insufficient evidence, not pass or failure |
| HTTPS | Report updated 2026-08-08; observed 2026-08-09 | 5 HTTPS URLs and 0 non-HTTPS issues | Pass as observed |
| Manual actions and security issues | Observed 2026-08-09 | No issues detected | Zero issues as observed |
| Console exports | 2026-08-09 | No CSV export downloaded | Absent |

## Action ledger

| Provider and property | Action and target | Accepted | Visible confirmation | Classification | Repeat policy | Next review condition |
|---|---|---|---|---|---|---|
| GSC `sc-domain:harnessie.com` | Submit `https://harnessie.com/sitemap.xml` | 2026-08-09; exact time not recorded | `Success`, last read 2026-08-09, 9 discovered pages | Accepted discovery action | Do not resubmit while healthy; refresh once only after a verified material sitemap revision whose last-read state is stale | Material sitemap revision or a sitemap error |
| GSC `sc-domain:harnessie.com` | Request indexing for `/guide.html`, `/ladder.html`, `/brains.html`, and `/ringer.html` | 2026-08-09; exact times not recorded | Each entered Google's priority crawl queue | Pending recrawl | Do not request any of these URLs again while queued | Page indexing advances beyond 2026-08-06, one URL is recrawled, or Google reports a new actionable reason |

Active validation batches: none. The `Page with redirect` group is intentional and validation was deliberately not started.

## Do not repeat

- Do not resubmit the accepted healthy sitemap merely because its status remains `Success`.
- Do not repeat indexing requests for `/guide.html`, `/ladder.html`, `/brains.html`, or `/ringer.html` while they remain queued or pending recrawl.
- Do not start validation for the three intentional host and protocol redirects.
- Do not treat the decorative video exclusion as a page-indexing defect.
- Do not classify insufficient Core Web Vitals field data as either a pass or a failure.
- Do not open GSC merely to restate the 2026-08-09 evidence; wait for a next-review condition and appropriate console authority.

## Next review

Review the property on the next authorized console-maintenance pass after the Page indexing report advances beyond 2026-08-06, any requested URL receives a crawl, the sitemap reports an error, or production search validation reveals a new defect. Until then, the four indexing requests are pending recrawl and no repository defect is open.
