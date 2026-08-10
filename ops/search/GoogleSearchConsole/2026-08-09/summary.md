# Google Search Console baseline: 2026-08-09

Property: `sc-domain:harnessie.com`

Audit date: 2026-08-09 America/Denver

Evidence type: authenticated Google Search Console UI observations through the existing Comet profile. No CSV export was downloaded.

## Page indexing

Report last update: 2026-08-06

- Indexed: 5 pages.
- Not indexed: 3 pages in 1 category.
- Category: `Page with redirect`, source `Website`, validation `Not Started`, first detected 2026-07-10.
- Examples: `http://harnessie.com/` last crawled 2026-07-11; `https://www.harnessie.com/` last crawled 2026-07-18; `http://www.harnessie.com/` last crawled 2026-07-30.
- Classification: expected noise. All three intentionally redirect to `https://harnessie.com/`; do not start fix validation.

Indexed examples and last crawl dates:

- `https://harnessie.com/`: 2026-07-30.
- `https://harnessie.com/compare.html`: 2026-07-19.
- `https://harnessie.com/threat-model.html`: 2026-07-08.
- `https://harnessie.com/quickstart.html`: 2026-07-07.
- `https://harnessie.com/getting-started.html`: 2026-07-07.

## Sitemaps

- `https://harnessie.com/sitemap.xml` submitted 2026-08-09.
- Last read: 2026-08-09.
- Status: `Success`.
- Discovered pages: 9.
- Discovered videos: 0.

## Video indexing

Report last update: 2026-08-05

- Video indexed: 0.
- Not indexed: 1, reason `Video isn't on a watch page`, validation `Not Started`.
- Classification: expected noise. The homepage uses a decorative product animation and does not claim `VideoObject`; page indexing is separate.

## Experience and safety

- Core Web Vitals last updated 2026-08-07: insufficient 90-day usage data for both mobile and desktop. This is missing field evidence, not a pass or failure.
- HTTPS last update 2026-08-08: 5 HTTPS URLs, 0 non-HTTPS URLs, no critical issues in the last 90 days.
- Manual actions: no issues detected.
- Security issues: no issues detected.

## Repository and production comparison

- Repository after the local repair: 9 intended canonical HTML pages; offline contract passes with 0 defects.
- Local production-equivalent HTTP server: 9 sitemap pages, 0 defects, 0 infrastructure failures.
- Production during the audit: the sitemap moved from 8 to 9 pages after commit `b1fb1c7`; all 9 routes and canonical redirects were healthy, but the 8 generated documentation pages still lacked the new JSON-LD.
- Console discovery predates the 9-page sitemap and reports only 5 canonical indexed pages plus 3 intentional redirects.

## Completed actions

1. Deployed the JSON-LD, internal-discovery, and deterministic search-contract changes in commit `47f7ec3`.
2. Verified production at 9 sitemap pages, 0 defects, and 0 infrastructure failures.
3. Submitted `https://harnessie.com/sitemap.xml`; GSC read it successfully and discovered all 9 pages.
4. Inspected `/guide.html`, `/ladder.html`, `/brains.html`, and `/ringer.html`. Each was `Discovered - currently not indexed`, had no prior crawl, and was eligible for indexing.
5. Requested indexing for all four pages; GSC confirmed that each entered the priority crawl queue.

## Remaining state

- Wait for Google to crawl and adjudicate the four requested canonical pages.
- Do not repeatedly request indexing; repeated submissions do not change queue priority.
- Recheck after the Page indexing report updates beyond 2026-08-06. A delayed report is pending recrawl, not a current site defect.
