# Repo Standards Audit — harnessie — 2026-07-06

Audit-only (recon) run against Repo Standards v0.7 (`0_Across/Repo Standards.md`). No remediation applied; no version bump. harnessie is private and pre-public-promotion (standing non-goal).

## Effective tiers

| Tier | Signal | Applies |
|---|---|---|
| all | every repo | yes |
| personal-utility | private, not in `portfolio.yaml` | yes (base tier, per INTENT §8) |
| agent-facing | tracked `assistant-guide.txt` | deferred (recorded exception, INTENT §8) |
| hosted | no CNAME / vercel.json / Pages / landing page | no |
| open-spec | no `spec.md`; not under paice.foundation | no |
| commercial | not a paid product | no |
| skill-home | no `MANIFEST.yaml` / `SKILL.md` | no |
| fork | origin is `snapsynapse/harnessie` | no |

The entire hosted-tier row set (robots.txt, llms.txt, sitemap, OG image, GH description/topics/homepage, social preview, a11y gate, Siteline) is N/A while the repo is unpublished. This matches the repo's own INTENT §8, which pre-records the deferral.

## Findings

| # | Matrix row | Observed | Severity | Verdict |
|---|---|---|---|---|
| 1 | Layout: audit/internal docs stay at repo root (private, not served) | Audit reports were initially written to `docs/audits/`, but INTENT §8 reserves `docs/` as the future GitHub-Pages public served tree | Medium | RESOLVED this run — relocated to root-level `audits/` |

Everything else walked conformant or is a recorded exception (below).

### Finding 1 (Medium, RESOLVED) — audit output location conflicted with the docs/-is-public-served-tree exception

INTENT §8 records: "docs/ is reserved for the canonical web page … when Harnessie goes public GitHub Pages will publish from main /docs, so that directory is kept as the future public served tree." The standards doc's GitHub Pages rule is explicit that internal/strategy docs live at the repo root (private, not served), and `docs/` is public.

These audit reports are internal. Under `docs/audits/` they would have become publicly fetchable the moment Pages is enabled from `/docs` on promotion — a latent promotion-time leak (Pages is not enabled today, so there was no live exposure).

Resolution: the reports were relocated to a root-level `audits/` directory (the repo root stays private and unserved), consistent with "internal docs live at root, docs/ is the served tree." `docs/` again holds only its placeholder, and no INTENT §8 carve-out is needed.

## Conformant rows (walked, passed)

| Matrix | Row | Evidence |
|---|---|---|
| Hygiene | Baseline `.gitignore` (all 13 patterns) | all present, full-directory ignores |
| Hygiene | `handoffs/`, `working/`, `.claude/` gitignored | present as full-dir ignores |
| Hygiene | No tracked `.DS_Store` | `git ls-files` count 0 |
| Layout | `INTENT.md` 9-section template, correct order | headers 1–9 match template exactly |
| Layout | `CHANGELOG.md` Keep-a-Changelog | present, dated entries, newest first |
| Layout | `SECURITY.md` at root | present |
| Layout | `LICENSE` (single) | correct — no spec text, so no LICENSE/LICENSE-SPEC split needed |
| Versioning | Version consistency across surfaces | `pyproject.toml` 0.3.3 = `harness/__init__.py` 0.3.3 = `CHANGELOG.md` 0.3.3; no stale mentions |
| Exceptions | Every recorded exception still applies | §8's 6 exceptions all current and accurate |

## Recorded exceptions (INTENT §8, all valid)

- Personal-utility tier: hosted/open-spec/agent-facing/commercial rows N/A until promotion.
- `.claude/` gitignored; canonical role prompts tracked in `agents/`; CLI is the primary interface.
- `INTENT.md` pre-applied ahead of the tier requirement.
- `assistant-guide.txt` present but agent-facing tier deferred until public promotion (versions are commits-not-releases by choice).
- Turnfile adoption not taken: single-operator one-process orchestration, out of scope per GOVERNANCE.md.
- `docs/` reserved as the future public served tree (this is the row Finding 1 intersects).

## Assessment

Exemplary conformance for its tier. The exceptions discipline is the strongest signal: §8 pre-records six deviations with reasons and dates, which is exactly what the standards doc asks for and is better than most promoted repos in the portfolio. The single finding is a location conflict introduced by this audit run itself, not pre-existing drift.

Nothing here requires `repo-polish` or `release-checklist` while the repo stays private. On promotion, the standard path (annotated tags, RELEASE_CHECKLIST.md, CI-gate-before-tag, hosted-tier rows) applies — already anticipated in §8.

## For the standing findings register

One open item for `0_Across/findings.yaml` (judgment finding, not auto-detectable): `harnessie | audit output under docs/ collides with docs/-is-public-served-tree exception | medium | check: judgment`. Not written to the register in this audit-only run; surfaced for the operator.
