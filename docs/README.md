# docs

The public served tree. GitHub Pages publishes from `main` `/docs`, so everything here is publicly fetchable at https://harnessie.com/. Internal engineering and planning docs live at the repo root, not here.

Contents:
- `index.html` plus `favicon.svg`, `CNAME`, `sitemap.xml`, `robots.txt`, byte-identical `llms.txt` and `llm.txt`, `site.webmanifest`, `404.html`: the canonical landing page and its crawler and discovery files.
- `quickstart.md`, `getting-started.md`, `ladder.md`, `GUIDE.md`, `agent-file-ownership.md`, `brains.md`, `threat-model.md`, `compare.md`, and `ringer.md`: user-facing docs, each also served as a styled HTML page so the site is navigable without GitHub. Ringer is a primary verifier-adoption surface and appears in site navigation and machine discovery.
- The `.html` doc pages are GENERATED from the markdown by `scripts/build_docs_html.py`. Do not edit them directly: edit the markdown, run `python3 scripts/build_docs_html.py`, and commit source and output together.
- `.well-known/`: the GuideCheck trust pair (`assistant-guide.txt`, byte-identical to the repo-root copy, plus its provenance sidecar `assistant-guide-manifest.txt`). Sync is enforced by `tests/test_guide_artifacts.py`. `.nojekyll` keeps Pages serving this dot-directory.
- `MANIFEST.yaml`: the trust-bundle integrity manifest; `python3 -m harness.cli verify-manifest` checks it.
- `agents.json`, `api/v1/index.json`, `changelog.json`, `llms.txt`, `llm.txt`, `robots.txt`, and `sitemap.xml`: public machine discovery, current-source CLI, release-history, crawler, and navigation contracts. They distinguish stable release artifacts from unreleased source and do not advertise a hosted API or agent.
