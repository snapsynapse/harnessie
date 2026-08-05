# Next session handoff

## Current state

Harnessie 0.7.1 is shipped on PyPI and GitHub. The standalone `harnessie verify` surface is also published as `snapsynapse/harnessie-verify-action@v0` and listed in the GitHub Marketplace. The Homebrew formula serves 0.7.1.

The next public milestone is 0.8.0, write-safety and self-integrity. Its four roadmap mechanics are blast-radius ceilings, declared write-path conflict refusal for parallel groups, the maiden-voyage rule, and an inward manifest for role prompts and shipped configuration.

`decisions/AIDR-0008` was arbitrated on 2026-07-16 and executed on 2026-07-21 as [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers). The fresh-authored Apache-2.0 v0.1.0 seed contains a macOS Seatbelt reference wrapper, shared credential deny policy, and a deny/allow/symlink admission probe. Its macOS-14 CI probe passed, unsupported and unavailable backends fail closed, and the consent boundary remains intact: other developers' work enters only through their own consenting contribution.

All four 0.8 mechanics are implemented. Opt-in parallel `writes` declarations refuse invalid or overlapping groups before dispatch; declared ownership lanes remain enforced inside isolated parallel workspaces; opt-in phase/workflow `blast_radius` ceilings atomically roll back writes beyond declared artifact-volume bounds; `INWARD_MANIFEST.yaml` pins shipped prompts, YAML configs, and static ownership policy; and a new `phase_type` contract executes in a staged clone until the operator promotes the verified output with `approve-maiden`. The milestone needs release preparation, not another core mechanism.

The pre-release hardening pass is complete. One composed gate now runs the source checks, generated-doc verification, structural wheel/sdist inspection, SPDX metadata checks, private-surface scrubbing, `twine check`, and a fresh-venv smoke over the installed CLI. It found and fixed an empty-eval false pass and a stale assistant-guide registry URL. The operator retired the obsolete private scrub-list entry for an established public reference already shipped in v0.7.1, and the complete gate passes.

The remaining public first-harness gate is in progress. A [Siteline scan on 2026-08-05 UTC](https://siteline.to/results/harnessie-com-20260805) scored the deployed site 77 with a raw score of 91: the current rubric capped the grade because only 6/16 machine-resource quality points were visible. The local candidate adds truthful `agents.json`, local CLI, machine-readable changelog, RFC 9116 security, and explicit contact handoffs. Siteline's current scoring function evaluates the candidate at Level 4, 14/16, while the files explicitly deny a hosted API, hosted service, or MCP server. This is a local prediction only; the roadmap's 90+ gate remains open until deployment and a dated live rescan.

Cross-repo authority, dependency direction, and release propagation are defined in `ECOSYSTEM.md` and `ecosystem.yaml`. `python3 scripts/ecosystem_status.py` provides the offline local status view; use its optional `--github` mode only for non-authoritative release and pull-request observations.

## Verified baseline

Verified locally on 2026-08-04:

- `python3 -m pytest -q`: 351 passed, 1 skipped in the release-gate environment.
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
- GitHub `main` is `50068e8`; all observed CI and Pages checks on that commit succeeded. There are no open pull requests or issues, and v0.7.1 remains the latest release. This worktree carries an uncommitted public-readiness candidate on top of that commit.

## Handoff disposition

The detailed inventory and relevance assessment is in `audits/handoff-relevance-2026-07-21.md`. In short:

- The delivered 0.3 through 0.5 rotation packets, site-refresh packet and assets, consolidated session log, and retired position sweep were removed after the audit. Tests, evals, decisions, the tracked audit, and git history preserve the durable evidence.
- `handoffs/HANDOFF-protocol-resistant-mechanisms.md` remains design input, not an executable handoff.
- `handoffs/skills-inventory-preliminary.md` remains a private standing research task and needs a fresh inventory before any adoption decision.
- `handoffs/scrub-list.txt` remains an active pre-commit control.

## Recommended work order

1. Review the local public-readiness candidate. If authorized, commit and deploy it, then run a fresh Siteline scan. Mark the roadmap gate green only when the live result is 90 or above; the local 14/16 calculation is not deployment evidence.
2. Review and merge Homebrew tap draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1) when ready.
3. After the public gate is green, prepare the separately authorized 0.8 release change: version bump, dated changelog section, assistant-guide resync, final exact-commit artifacts, tag, GitHub Release, PyPI upload, verify-action pin, and Homebrew update. Do not infer any publication act from the completed hardening pass.
4. Keep engine-wrapper contributions consent-based and probe-gated. The smaller core backlog remains malformed provider-response handling, structured memory frontmatter, macOS sandbox parity for non-workspace temporary writes, and typed config validation.

## Operator-attended or external checks

- Deploy the public-readiness candidate and record a new live Siteline result; the tracked 90+ bar remains open until then.
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
