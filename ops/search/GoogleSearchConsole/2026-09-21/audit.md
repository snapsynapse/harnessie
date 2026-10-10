# Google Search Console observation, 2026-09-21

Dated observation (read-only audit, 2026-09-21) for `sc-domain:harnessie.com`. Historical evidence: later provider changes get a new dated record. No GSC mutation was performed; no export data retained.

## Current GSC state

Page indexing was last updated 2026-09-17:

- Indexed: 8.
- Not indexed: 6 across 3 reasons.
- `Page with redirect`: 3 intentional host or protocol redirects, validation not started. Expected noise.
- `Discovered - currently not indexed`: `/agent-file-ownership.html` and `/ringer.html`, neither crawled. Pending recrawl.
- `Crawled - currently not indexed`: `/.well-known/security.txt`, last crawled 2026-08-22. Expected noise because it is a machine surface, not an HTML index target.

Three of the four indexing requests accepted on 2026-08-09 have completed:

- `/guide.html`: indexed, last crawled 2026-09-15.
- `/brains.html`: indexed, last crawled 2026-09-16.
- `/ladder.html`: indexed, last crawled 2026-09-17.
- `/ringer.html`: still discovered and never crawled. Its accepted request remains do-not-repeat.

Other provider observations:

- Sitemap `https://harnessie.com/sitemap.xml`: submitted 2026-08-09, last read 2026-09-16, `Success`, 10 discovered pages, 0 discovered videos.
- Video indexing, updated 2026-09-20: 0 indexed, 1 excluded as `Video isn't on a watch page`. Expected noise for the decorative homepage video.
- Core Web Vitals, updated 2026-09-19: insufficient 90-day usage data for mobile and desktop. Unknown, not pass or failure.
- HTTPS, updated 2026-09-10: 8 HTTPS URLs, 0 non-HTTPS URLs, no critical issues.
- Breadcrumbs, updated 2026-09-19: 6 valid items, 0 invalid.
- Manual actions: no issues detected.
- Security issues: no issues detected.

An export control was briefly activated during read-only navigation. No export data was downloaded, retained, or used.
