# Current state and next work

## Release boundary

Harnessie 1.2.0 is the stable core release on GitHub and PyPI. It contains OpenAI Responses support, v1 evidence-bundle intake, structured claim verdicts, deterministic Ringer regression fixtures, event-trace metrics, OpenAI-compatible token-parameter handling, and a portable shell-substitution regression test.

Homebrew and Harnessie Verify Action are separately versioned downstreams. Their exact pins and release results must be recorded here after propagation. The 1.2.0 assistant guide is byte-identical across the repository and served copy and pinned by its sidecar, but its new DNS TXT and hosted GuideCheck result remain separate external closeout gates. The tracked 1.1.0 receipt is historical evidence only.

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
- Release-closeout evidence for the exact 1.2.0 artifacts, PyPI attestations, downstream pins, DNS anchor, and hosted GuideCheck result is maintained in `RELEASE_NOTES-1.2.0.md` and updated as each independent surface completes.

Skip counts depend on local sandbox and live-provider availability. Treat command outcomes and exact revisions as the contract, not fixed counts copied into future guides.

## 1.2.0 release closeout

The repository, website, and agent-surface audit found one high-priority release-identity conflict: current-source verifier additions were described next to the stable 1.1.0 package without a channel boundary. The 1.2.0 release resolves it by:

1. Publishing the evidence-bound verifier behavior as stable core 1.2.0 across README, Guide, machine resources, and the site.
2. Making the Ringer adoption page discoverable through navigation, `llms.txt`, `llm.txt`, `agents.json`, the homepage, and deterministic tests.
3. Refreshing architecture, eval, operating-context, release-checklist, and assistant-guide documentation while preserving the 1.1.0 receipt as historical evidence.
4. Migrating durable content from ignored handoffs into tracked authority, removing processed handoffs, and keeping private scrub controls outside the handoff queue.
5. Rebuilding generated HTML, refreshing trust hashes, running search and machine-surface checks, and repairing the homepage issues found by Lighthouse accessibility auditing.

## Remaining release order

1. Confirm the exact release workflow, GitHub Release assets, PyPI files and attestations, and fresh public-index install against the recorded checksums.
2. Propagate the published core to Verify Action and Homebrew only after the immutable PyPI artifacts verify.
3. Update the DNS TXT anchor to the released guide hash and rerun hosted GuideCheck, then replace pending language only if the anchors agree.
4. Record the current OpenSSF Scorecard result and dispositions when the repository-owned workflow produces its first authoritative result.

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
