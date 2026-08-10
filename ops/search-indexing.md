<!-- Upstream template: portfolio-search-indexing-audit contract v2 -->
---
title: "Search indexing"
purpose: "Property-specific index policy, validation commands, deployment gate, and console follow-up."
status: active
updated: 2026-08-09
owner: "Harnessie maintainers"
open_tasks:
  - "Monitor the four requested canonical pages after Google updates the Page indexing report beyond 2026-08-06."
---
# Search indexing

Canonical origin: `https://harnessie.com/`

Generated output: `docs`

## Index policy

| Surface | Policy | Reason |
|---|---|---|
| `/`, `/quickstart.html`, `/getting-started.html`, `/ladder.html`, `/guide.html`, `/compare.html`, `/brains.html`, `/threat-model.html`, `/ringer.html` | Index and include in sitemap | Canonical reader destinations with unique titles, descriptions, and crawl-visible internal discovery |
| `/404.html` | `noindex` and omit from sitemap | Error response, not a content destination |
| `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/agents.json`, `/api/v1/index.json`, `/changelog.json`, `/.well-known/*`, `/schemas/v1/*` | Crawlable machine surfaces, omit from HTML sitemap | Discovery, trust, or machine consumption rather than canonical HTML search results |
| Markdown source files under `/docs/` | Omit from sitemap; canonical served HTML remains the index target | GitHub Pages may serve source files, but generated HTML is the reader surface |
| GitHub, PyPI, and other platform copies | Omit from sitemap | External distribution surfaces are not site canonical pages |

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
