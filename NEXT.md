# Next session handoff

## Current state

Harnessie 0.7.1 is shipped on PyPI and GitHub. The standalone `harnessie verify` surface is also published as `snapsynapse/harnessie-verify-action@v0` and listed in the GitHub Marketplace. The Homebrew formula serves 0.7.1.

The next public milestone is 0.8.0, write-safety and self-integrity. Its four roadmap mechanics are blast-radius ceilings, declared write-path conflict refusal for parallel groups, the maiden-voyage rule, and an inward manifest for role prompts and shipped configuration.

`decisions/AIDR-0008` was arbitrated on 2026-07-16 and executed on 2026-07-21 as [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers). The fresh-authored Apache-2.0 v0.1.0 seed contains a macOS Seatbelt reference wrapper, shared credential deny policy, and a deny/allow/symlink admission probe. Its macOS-14 CI probe passed, unsupported and unavailable backends fail closed, and the consent boundary remains intact: other developers' work enters only through their own consenting contribution.

All four 0.8 mechanics are implemented. Opt-in parallel `writes` declarations refuse invalid or overlapping groups before dispatch; declared ownership lanes remain enforced inside isolated parallel workspaces; opt-in phase/workflow `blast_radius` ceilings atomically roll back writes beyond declared artifact-volume bounds; `INWARD_MANIFEST.yaml` pins shipped prompts, YAML configs, and static ownership policy; and a new `phase_type` contract executes in a staged clone until the operator promotes the verified output with `approve-maiden`. The milestone now needs a pre-release hardening and packaging pass, not another core mechanism.

Cross-repo authority, dependency direction, and release propagation are defined in `ECOSYSTEM.md` and `ecosystem.yaml`. `python3 scripts/ecosystem_status.py` provides the offline local status view; use its optional `--github` mode only for non-authoritative release and pull-request observations.

## Verified baseline

Verified locally on 2026-07-28:

- `python3 -m pytest -q`: 328 passed, 8 skipped.
- `python3 -m harness.cli eval`: 47/47 passed.
- `python3 -m harness.cli verify-manifest`: passed, 9 files.
- `python3 -m harness.cli verify-inward-manifest`: passed, 9 files.
- `git diff --check`: clean.

Skip counts depend on the available local sandbox and live-provider configuration. Treat the commands and outcomes as the contract, not a permanently fixed test count.

## Current cross-repo state

- `snapsynapse/harnessie-verify-action`: the local checkout at `~/Git/harnessie-verify-action` is clean and synchronized with remote `main` at `3a2f1bb`. The published action remains v0.1.0 and pins Harnessie 0.7.1.
- `snapsynapse/homebrew-tap`: the live `Formula/harnessie.rb` serves Harnessie 0.7.1 and has the correct PyPI sdist hash. Draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1) adds Harnessie to the README formula list and install example; the formula itself is unchanged.
- `snapsynapse/harnessie-engine-wrappers`: v0.1.0 is released from `ad3d759`. CI passed its real macOS-14 containment probe and its Ubuntu unsupported-platform refusal; release archives, wheel, and `SHA256SUMS` are attached.
- This repo dogfoods `snapsynapse/harnessie-verify-action@v0` in `.github/workflows/verify-pr-claims.yml`. A live verdict still depends on the repository verifier endpoint/model variables and API-key secret.
- GitHub `main` was `e5fc58b` at the 2026-07-28 session start; the latest observed CI and Pages runs succeeded. There were no open pull requests or issues, and v0.7.1 remained the latest release.

## Handoff disposition

The detailed inventory and relevance assessment is in `audits/handoff-relevance-2026-07-21.md`. In short:

- The delivered 0.3 through 0.5 rotation packets, site-refresh packet and assets, consolidated session log, and retired position sweep were removed after the audit. Tests, evals, decisions, the tracked audit, and git history preserve the durable evidence.
- `handoffs/HANDOFF-protocol-resistant-mechanisms.md` remains design input, not an executable handoff.
- `handoffs/skills-inventory-preliminary.md` remains a private standing research task and needs a fresh inventory before any adoption decision.
- `handoffs/scrub-list.txt` remains an active pre-commit control.

## Recommended work order

1. Review and merge Homebrew tap draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1) when ready. The local verify-action checkout was synchronized on 2026-07-21.
2. Run the 0.8 pre-release hardening pass: exercise build artifacts and fresh-install behavior, verify the new CLI surfaces from an installed package, compose the release gate, and reconcile public claims before any version bump or release authorization.
3. Invite wrapper-engine contributions only after the v0.1.0 original seed, and accept another developer's implementation only through their own consenting contribution. Keep backend claims probe-gated and platform-specific.
4. Take the smaller hardening backlog after the 0.8 write boundary is structurally defined: malformed provider-response handling, structured memory frontmatter, and macOS sandbox parity for writes outside the workspace.

## Operator-attended or external checks

- Confirm whether the live Siteline score has reached the roadmap bar of 90; the tracked roadmap still treats it as open.
- Configure the dogfood verifier repository variables and secret if live PR verdicts are desired.
- Live provider scorecards remain explicit opt-in operations via `HARNESSIE_LIVE=1`.

## Session start commands

```bash
git status --short --branch
python3 -m pytest -q
python3 -m harness.cli eval
python3 -m harness.cli verify-manifest
python3 -m harness.cli verify-inward-manifest
git diff --check
```

Private planning notes remain in `ROADMAP-PRIVATE.md`. Do not stage `.agents/`, `.codex/`, `handoffs/`, `runs/`, `workspace/`, or `ROADMAP-PRIVATE.md`.
