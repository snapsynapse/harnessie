# Current state and next work

## Release boundary

Harnessie 1.1.0 is the stable core release on GitHub, PyPI, and Homebrew. Harnessie Verify v0.1.3 and stable `snapsynapse/harnessie-verify-action@v0` pin that exact core. The 1.1.0 assistant guide remains byte-identical across the repository and served copy, independently anchored through DNS and the repository release, and confirmed by the tracked hosted GuideCheck receipt.

Current `main` is ahead of those artifacts. It contains OpenAI Responses support, v1 evidence-bundle intake, structured claim verdicts, deterministic Ringer regression fixtures, event-trace metrics, OpenAI-compatible token-parameter handling, and a portable shell-substitution regression test. These additions are intended for the next minor release but are not yet published. Public and machine surfaces must preserve that distinction.

No version bump, tag, GitHub Release, PyPI publication, Homebrew update, Verify Action propagation, assistant-guide rotation, DNS change, or hosted GuideCheck rerun has been authorized or completed for the next release.

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
- PyPI, GitHub Release, Homebrew, and stable Verify Action remain on 1.1.0.

Skip counts depend on local sandbox and live-provider availability. Treat command outcomes and exact revisions as the contract, not fixed counts copied into future guides.

## Documentation remediation

The repository, website, and agent-surface audit found one high-priority release-identity conflict: current-source verifier additions were described next to the stable 1.1.0 package without a channel boundary. The documentation tranche resolves it by:

1. Labeling stable 1.1.0 and unreleased current-source behavior separately across README, Guide, machine resources, and the site.
2. Making the Ringer adoption page discoverable through navigation, `llms.txt`, `llm.txt`, `agents.json`, the homepage, and deterministic tests.
3. Refreshing architecture, eval, operating-context, and release-checklist documentation without changing the externally anchored 1.1.0 assistant-guide bytes.
4. Migrating durable content from ignored handoffs into tracked authority, removing processed handoffs, and keeping private scrub controls outside the handoff queue.
5. Rebuilding generated HTML, refreshing trust hashes, running search and machine-surface checks, and repairing the homepage issues found by Lighthouse accessibility auditing.

## Release candidate order

With the documentation remediation deployed:

1. Re-run the full repository, docs, search, manifest, and accessibility checks and record the exact candidate evidence.
2. Review the 1.2.0 milestone and release provenance requirements, including Trusted Publishing, protected environment approval, artifact attestations, SBOM digests, signing policy, and the current OpenSSF Scorecard result.
3. Request separate authority for the version bump and release commit.
4. Build and verify exact artifacts before requesting separate publication authority.
5. Propagate the published core to Verify Action and Homebrew only after the immutable PyPI artifacts verify.
6. Rotate assistant-guide bytes, sidecar, release URL, trust pins, DNS TXT, and hosted GuideCheck evidence atomically if the guide changes.

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
