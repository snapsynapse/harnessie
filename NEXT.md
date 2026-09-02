# Current state and next work

## Release boundary

Harnessie 1.2.0 is the stable core release on GitHub and PyPI. It contains OpenAI Responses support, v1 evidence-bundle intake, structured claim verdicts, deterministic Ringer regression fixtures, event-trace metrics, OpenAI-compatible token-parameter handling, and a portable shell-substitution regression test.

Homebrew and Harnessie Verify Action are separately versioned downstreams. Both now consume the published 1.2.0 core through independently verified releases: Verify Action v0.2.0 and stable `v0`, plus the Homebrew tap formula at 1.2.0. The 1.2.0 assistant guide is byte-identical across the repository and served copy and pinned by its sidecar, but its new DNS TXT and hosted GuideCheck result remain separate external closeout gates. The tracked 1.1.0 receipt is historical evidence only.

## Adoption direction

The lead adoption surface is `harnessie verify` as a fail-closed intake gate for agent-produced changes. Ringer is the first named composition target because its task-check contract already treats process exit as authority. Harnessie composes through that seam rather than replacing Ringer's orchestration model. The full harness remains the growth path for consent, ownership lanes, containment, human arbitration, and a tamper-evident run audit.

## Verified evidence

The deployed documentation-remediation head `388c490` has the following evidence:

- `python3 -m pytest -q`: 483 passed, 9 skipped.
- `python3 -m harness.cli eval`: 51/51 passed.
- `python3 -m harness.cli verify-manifest`: 21 outward files passed.
- `python3 -m harness.cli verify-inward-manifest`: 16 inward files passed.
- Exact-head GitHub CI run `33578047382` and Pages deployment run `33578046788` passed.
- Sixteen deployed page and machine-resource surfaces were byte-identical to the commit, and the production search contract reported ten sitemap pages with zero defects or infrastructure failures.
- Tag `v1.2.0` peels to release commit `5bb46378464d3636b43762ededc507beb8f7ddf8`; exact-tag CI run `33581149207` passed.
- The GitHub Release carries the wheel, source distribution, CycloneDX 1.6 SBOM, and checksum record. Their SHA-256 digests are recorded in `RELEASE_NOTES-1.2.0.md`.
- Recovery run `33583589070` checksum-verified the existing release assets and published those exact distributions to PyPI through the protected `pypi` environment. PyPI attestations and publisher identity verified, and a clean Python 3.13 public-index install exposed the evidence-bundle CLI contract.
- Harnessie Verify Action v0.2.0 and stable `v0` resolve to `bc6f94f93cade0e722f525bd0b387005b88cd3a2`; its seven-job CI run `33584285698` passed.
- Homebrew tap commit `118ca530971f3d4b5fb6100f117f14a96b464fb8` pins the PyPI 1.2.0 source distribution. Strict online audit, an installed 1.1.0 to 1.2.0 upgrade, formula test, linkage, metadata, and evidence-bundle CLI smoke all passed.
- Repository-owned OpenSSF Scorecard run `33585734990` measured exact commit `2c00a7ddfc3d0e134f52f55b811ae630cea01403` at aggregate 5.9 after deterministic remediations. `audits/openssf-scorecard-2026-09-02.json` records every individual check and disposition; the aggregate is not a release gate.

Skip counts depend on local sandbox and live-provider availability. Treat command outcomes and exact revisions as the contract, not fixed counts copied into future guides.

## 1.2.0 release closeout

The repository, website, and agent-surface audit found one high-priority release-identity conflict: current-source verifier additions were described next to the stable 1.1.0 package without a channel boundary. The 1.2.0 release resolves it by:

1. Publishing the evidence-bound verifier behavior as stable core 1.2.0 across README, Guide, machine resources, and the site.
2. Making the Ringer adoption page discoverable through navigation, `llms.txt`, `llm.txt`, `agents.json`, the homepage, and deterministic tests.
3. Refreshing architecture, eval, operating-context, release-checklist, and assistant-guide documentation while preserving the 1.1.0 receipt as historical evidence.
4. Migrating durable content from ignored handoffs into tracked authority, removing processed handoffs, and keeping private scrub controls outside the handoff queue.
5. Rebuilding generated HTML, refreshing trust hashes, running search and machine-surface checks, and repairing the homepage issues found by Lighthouse accessibility auditing.

## Remaining release order

1. Update the DNS TXT anchor to released guide SHA-256 `ff77d219add6f1cf6a22c4570830f9fbd70cedd59f3caa933fbd0c7ae3733421` and rerun hosted GuideCheck, then replace pending language only if all anchors agree.

## Specific follow-up sessions

1. Review Dependabot pull requests [#4](https://github.com/snapsynapse/harnessie/pull/4), [#5](https://github.com/snapsynapse/harnessie/pull/5), [#6](https://github.com/snapsynapse/harnessie/pull/6), and [#7](https://github.com/snapsynapse/harnessie/pull/7). Merge only updates whose immutable commits, release tags, diffs, and required checks verify; otherwise close with a recorded rationale. Consolidate future GitHub Actions updates if separate PR churn outweighs review clarity.
2. Decide the `main` branch and review policy as a provider-governance session. Model the current maintainer path before enabling rules, require the exact CI and security checks that should gate merges, preserve an explicit emergency path, and verify the ruleset does not deadlock release recovery.

## External and optional checks

- Live provider scorecards require explicit opt-in through `HARNESSIE_LIVE=1` and the relevant configured endpoint or credential.
- Local Lighthouse 13.4.1 runs against the remediated homepage and all nine generated documentation routes each scored accessibility 1.00 with no failing accessibility audits. Browser automation still does not substitute for manual assistive-technology testing.
- GitHub repository description and discovery topics now reflect the verifier-first adoption wedge. The canonical homepage, Issues-on, and Wiki-off settings remain correct; Discussions remain disabled.

## Session start commands

Literal
```bash
git status --short --branch
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli verify-inward-manifest
python3 scripts/build_docs_html.py --check
git diff --check
```

Private planning notes remain in `ROADMAP-PRIVATE.md`. Do not stage `.agents/`, `.codex/`, `runs/`, `workspace/`, or `ROADMAP-PRIVATE.md`.
