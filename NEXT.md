# Next session handoff

## Current state

Harnessie 0.8.0 is shipped on PyPI and GitHub. The standalone `harnessie verify` surface remains published as `snapsynapse/harnessie-verify-action@v0` and listed in the GitHub Marketplace, but that separately owned action and the Homebrew formula still pin 0.7.1 pending explicit propagation work.

The next public milestone is 1.0.0, extensibility earned. Its admission bar remains strict: stable configuration and workflow schemas with a deprecation policy, plugin dispatch that cannot bypass the registry, and per-lane sandbox profiles must preserve every shipped fail-closed guarantee.

`decisions/AIDR-0008` was arbitrated on 2026-07-16 and executed on 2026-07-21 as [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers). The fresh-authored Apache-2.0 v0.1.0 seed contains a macOS Seatbelt reference wrapper, shared credential deny policy, and a deny/allow/symlink admission probe. Its macOS-14 CI probe passed, unsupported and unavailable backends fail closed, and the consent boundary remains intact: other developers' work enters only through their own consenting contribution.

All four 0.8 mechanics are shipped. Opt-in parallel `writes` declarations refuse invalid or overlapping groups before dispatch; declared ownership lanes remain enforced inside isolated parallel workspaces; opt-in phase/workflow `blast_radius` ceilings atomically roll back writes beyond declared artifact-volume bounds; `INWARD_MANIFEST.yaml` pins shipped prompts, YAML configs, and static ownership policy; and a new `phase_type` contract executes in a staged clone until the operator promotes the verified output with `approve-maiden`.

The 0.8 release includes the completed hardening pass. One composed gate runs the source checks, generated-doc verification, structural wheel/sdist inspection, SPDX metadata checks, private-surface scrubbing, `twine check`, and a fresh-venv smoke over the installed CLI. It found and fixed an empty-eval false pass, a stale assistant-guide registry URL, and a package `__version__` drift that the release suite now prevents.

The public first-harness gate is green. A fresh live Siteline 2.3.0 scan on 2026-08-05 UTC scored the deployed site A, 97/100, with Level 4 machine enablement at 16/18. The scan fetched the truthful `agents.json`, local CLI manifest, machine-readable changelog, RFC 9116 security contact, sitemap, and task routes while the declarations continued to deny a hosted API, hosted service, or MCP server. Siteline did not retain the fresh response in its public result store; the request ID, response hash, provenance, score, and that retrieval residual are preserved in [the tracked release-gate audit](audits/siteline-live-result-2026-08-05.json).

Cross-repo authority, dependency direction, and release propagation are defined in `ECOSYSTEM.md` and `ecosystem.yaml`. `python3 scripts/ecosystem_status.py` provides the offline local status view; use its optional `--github` mode only for non-authoritative release and pull-request observations.

## Verified baseline

Verified locally on 2026-08-04:

- `python3 -m pytest -q`: 352 passed, 1 skipped in the release-gate environment.
- `python3 -m harness.cli eval`: 47/47 passed.
- `python3 -m harness.cli verify-manifest`: passed, 13 files.
- `python3 -m harness.cli verify-inward-manifest`: passed, 9 files.
- `python3 scripts/build_docs_html.py --check`: passed, 8 pages.
- Built wheel and sdist: `twine check`, structural inspection, and fresh-install smoke passed.
- `git diff --check`: clean.

Skip counts depend on the available local sandbox and live-provider configuration. Treat the commands and outcomes as the contract, not a permanently fixed test count.

## Current cross-repo state

- `snapsynapse/harnessie-verify-action`: the local checkout at `~/Git/harnessie-verify-action` is clean and synchronized with remote `main` at `3a2f1bb`. The published action remains v0.1.0 and pins Harnessie 0.7.1.
- `snapsynapse/homebrew-tap`: remote `main` is `f3cd9a9`; the live formula serves Harnessie 0.7.1 with the correct PyPI sdist hash. The clean local checkout is two unrelated Agentlink commits behind remote. Draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1) remains open and adds Harnessie to the README formula list and install example; the formula itself is unchanged.
- `snapsynapse/harnessie-engine-wrappers`: v0.1.0 is released from `ad3d759`. CI passed its real macOS-14 containment probe and its Ubuntu unsupported-platform refusal; release archives, wheel, and `SHA256SUMS` are attached.
- This repo dogfoods `snapsynapse/harnessie-verify-action@v0` in `.github/workflows/verify-pr-claims.yml`. A live verdict still depends on the repository verifier endpoint/model variables and API-key secret.
- GitHub `main` carries the v0.8.0 release commit, and v0.8.0 is the latest release. Exact-commit CI, Pages, wheel, sdist, and fresh-install checks passed before publication. There were no open pull requests or issues at release preparation.

## Handoff disposition

The detailed inventory and relevance assessment is in `audits/handoff-relevance-2026-07-21.md`. In short:

- The delivered 0.3 through 0.5 rotation packets, site-refresh packet and assets, consolidated session log, and retired position sweep were removed after the audit. Tests, evals, decisions, the tracked audit, and git history preserve the durable evidence.
- `handoffs/HANDOFF-protocol-resistant-mechanisms.md` remains design input, not an executable handoff.
- `handoffs/skills-inventory-preliminary.md` remains a private standing research task and needs a fresh inventory before any adoption decision.
- `handoffs/scrub-list.txt` remains an active pre-commit control.

## Recommended work order

1. Under separately authorized adjacent-repository scope, test Harnessie 0.8.0 in `harnessie-verify-action`, update its default core pin, run CI, and release the action using its own train.
2. Under separately authorized adjacent-repository scope, update the Homebrew formula to the immutable PyPI 0.8.0 sdist and hash, run its install and test checks, and reconcile draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1).
3. Before opening 1.0 implementation, choose the smallest acceptance-complete slice. Typed configuration validation and the written schema/deprecation contract are the natural first candidate because they define the stable extension boundary.
4. Keep engine-wrapper contributions consent-based and probe-gated. The smaller core backlog remains malformed provider-response handling, structured memory frontmatter, and macOS sandbox parity for non-workspace temporary writes.

## Operator-attended or external checks

- Propagate core 0.8.0 through the separately owned verify-action and Homebrew release trains when those repositories are explicitly in scope.
- Configure the dogfood verifier repository variables and secret if live PR verdicts are desired.
- Live provider scorecards remain explicit opt-in operations via `HARNESSIE_LIVE=1`.

## Session start commands

Literal
```bash
git status --short --branch
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli verify-inward-manifest
git diff --check
```
Private planning notes remain in `ROADMAP-PRIVATE.md`. Do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, `workspace/`, or `ROADMAP-PRIVATE.md`.
