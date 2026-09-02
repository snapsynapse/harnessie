# Repository, documentation, website, and agent-surface audit

Date: 2026-09-01
Audited base: `965670a8d0fe8dc34cb7a5a20bb4afd75551b5c2`
Scope: Harnessie repository, generated and deployed documentation, public machine resources, Ringer adoption surface, temporary handoffs, release truth, search contracts, and homepage accessibility.

## Verdict

The source implementation was healthy, but the public contract had one high-priority release-identity defect: the site and machine resources labeled the product as stable 1.1.0 while describing evidence bundles and structured claim verdicts that exist only on current `main`. Ringer was a credible adoption surface but was hidden from normal navigation and machine discovery. Operating docs and ignored handoffs had accumulated stale state. The deployed pages otherwise matched the audited local generated pages, returned HTTP 200, and passed the repository search contract.

This remediation separates stable release artifacts from current source, makes Ringer discoverable, refreshes durable operating authority, empties the processed handoff queue, adds the `llm.txt` alias, strengthens deterministic regression checks, repairs the accessibility findings, and aligns GitHub description and topics with the verifier-first adoption wedge. It does not bump a version, publish package artifacts, or change Verify Action.

## Findings and disposition

| Priority | Finding | Disposition |
|---|---|---|
| High | Stable 1.1.0 and unreleased current-source verifier capabilities were presented without a channel boundary. | Fixed in README, Guide, Ringer guide, homepage, `agents.json`, CLI manifest, changelog JSON, `llms.txt`, and deterministic tests. |
| High | Ringer was intentionally hidden from navigation and absent from normal machine discovery. | Fixed in generated navigation and footer, homepage, `agents.json`, `llms.txt`, `llm.txt`, and regression tests. The stale subscriber-gated external guide URL now points to the public Ringer repository. |
| Medium | `CLAUDE.md`, `PROJECT_CONTEXT.md`, `NEXT.md`, architecture, eval documentation, and private roadmap state were stale. | Reconciled to stable 1.1.0 plus unreleased current source. Fixed counts are labeled observations rather than permanent contracts. |
| Medium | Three processed handoffs and a private scrub control remained in `handoffs/`. | Durable release-provenance, positioning, and current-state material moved to tracked authority or the private roadmap. Processed handoffs were removed. The scrub control moved to ignored `.private-controls/`; `handoffs/` is empty. |
| Medium | Release checklist still treated local `twine upload` as the normal PyPI path and omitted signing, SBOM, attestations, protected environment, and Scorecard gates. | Checklist now requires a Trusted Publisher and protected release environment, PyPI attestations and integrity verification, SBOM digests, a signing decision, and current Scorecard review. No external release infrastructure was changed. |
| Medium | Homepage Lighthouse accessibility score was 0.89 because of footer contrast, skipped heading levels, an accessible-name mismatch, and color-only inline links. Generated routes scored 0.90 or 0.91 because of muted-label contrast and color-only links. | Fixed the homepage and shared generator styles. The local remediated homepage and all nine generated routes each score 1.00 in Lighthouse 13.4.1 with no failing accessibility audits. |
| Low | `/llm.txt` was absent although `/llms.txt` was present. | Added a byte-identical alias, trust-manifest pin, search requirement, and equality tests. |
| Low | Sitemap modification dates remained 2026-08-20 after later content changes. | Updated all ten canonical entries to 2026-09-01. |
| Low | Homepage publisher identity was limited. | Added the publisher's GitHub identity to structured data. |
| Low | GitHub description and topics reflected general orchestration more strongly than agent-change verification. | Updated the description to lead with verification before merge and added `code-review`, `verification`, and `github-actions` topics. Homepage, Issues, and Wiki settings were already correct. |

## Verification

- Before remediation, all ten deployed canonical pages returned HTTP 200 and were byte-identical to the corresponding audited local pages; major AI crawler user agents also received HTTP 200. This proves the pre-change deployment state only.
- `.venv/bin/python -m pytest -q`: 483 passed, 9 skipped.
- `.venv/bin/python -m harness.cli eval`: 51/51 passed.
- `.venv/bin/python -m harness.cli verify-manifest`: 21 files passed.
- `.venv/bin/python -m harness.cli verify-inward-manifest`: 16 files passed.
- `.venv/bin/python -m harness.cli validate`: 9 documents valid under schema v1.
- `python3 scripts/build_docs_html.py --check`: 9 generated pages current.
- `node scripts/check-search.mjs`: 10 sitemap pages, 0 defects, 0 infrastructure failures.
- JSON parsing passed for `agents.json`, CLI manifest, and changelog JSON.
- `docs/llms.txt` and `docs/llm.txt` are byte-identical.
- Root and served assistant guides remain byte-identical at SHA-256 `f7d45f62f2941f5541d1342be0fc037c1ef7fc3e06f44ad39cf94a5b50e5080d`.
- Local Lighthouse 13.4.1 accessibility score: 1.00 with no failing accessibility audits on the homepage and all nine generated documentation routes.
- `git diff --check`: passed.

## Remaining gates

- These changes are working-tree edits until separately committed and pushed. The remediated website is not deployed until GitHub Pages publishes that commit and exact live bytes are rechecked.
- Browser automation does not substitute for manual screen-reader, keyboard, zoom, and other assistive-technology testing.
- The 1.2.0 candidate remains open. Version bump, release commit, artifact build, publication, downstream propagation, assistant-guide rotation, DNS, and hosted verification remain separate authority gates.
