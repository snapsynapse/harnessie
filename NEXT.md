# Next session handoff

## Current state

Harnessie 1.1.0 is the current core release. It retains the six stable v1 authoring contracts and explicit operator-trusted plugin boundary from 1.0.0, then makes Harnessie's Golden Rule inspectable through the read-only `harnessie ownership` decision command and a zero-model executable collision proof. The core release is published independently before its downstream release train.

The 1.1.0 downstream release train is pending. Harnessie Verify v0.1.2 and stable `snapsynapse/harnessie-verify-action@v0` currently pin 1.0.0, and the public Homebrew formula currently installs 1.0.0 from the immutable PyPI sdist. Both must move only after the 1.1.0 core package is public and independently tested. `harnessie-engine-wrappers` remains independently released at v0.1.0 because core 1.1.0 consumes no new wrapper seam.

The 1.1.0 ownership inspector calls the same ledger decision function as enforcement and performs no claim or write. Human output names the governing lane or first-writer claim, owner, pattern, reason, and remedy. JSON output uses schema version 1. The executable collision proof attempts a real built-in `write_file` overwrite and passes only if the second agent is denied and the first artifact survives byte-for-byte.

The first 1.0 slice freezes six stable Draft 2020-12 authoring schemas, a side-effect-free `harnessie validate` command, runtime startup validation, cross-document checks, explicit v1 scaffolds, packaged and served schema artifacts, and the compatibility and deprecation contract in `SCHEMA_COMPATIBILITY.md`. Schema-less 0.8 documents remain implicit v1 throughout 1.x.

The second 1.0 slice compiles ownership decisions into agent-specific read-only sandbox overlays for shell calls, deterministic checks, and verifier execution. Operator lanes, other-agent lanes, and other agents' first-writer claims are kernel-protected from interpreter-hidden writes. Invalid patterns and unsupported nested profiles fail closed; unowned paths retain first-writer compatibility.

The third 1.0 slice admits installed tool extensions only through the `harnessie.tools.v1` entry-point group and never auto-loads them. Operators select plugins explicitly with repeatable `--plugin NAME` arguments. Admission validates and namespaces declarations before model dispatch, records loader-supplied provenance, and pins exact plugin receipts across resume. Imported implementation code is explicitly operator-trusted and not lane-confined. Untrusted plugins are unsupported pending a separately versioned out-of-process protocol.

All three planned 1.0 slices and the 1.1.0 ownership inspection release are complete. The active work is the separately gated 1.1.0 downstream release train and external guide-anchor rotation. Do not expand it into deferred multi-orchestrator or untrusted-plugin designs without new evidence and authority.

The pre-1.0 correctness packet ships in 1.0.0. Anthropic and OpenAI-compatible adapters turn invalid JSON, malformed envelopes, invalid tool calls, and invalid usage counters into non-echoing provider error turns. Adversarial rebuttal agents receive each peer position in full and exclude their own position by value, removing the truncation that previously produced a spurious objection.

`decisions/AIDR-0008` was arbitrated on 2026-07-16 and executed on 2026-07-21 as [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers). The fresh-authored Apache-2.0 v0.1.0 seed contains a macOS Seatbelt reference wrapper, shared credential deny policy, and a deny/allow/symlink admission probe. Its macOS-14 CI probe passed, unsupported and unavailable backends fail closed, and the consent boundary remains intact: other developers' work enters only through their own consenting contribution.

All four 0.8 mechanics are shipped. Opt-in parallel `writes` declarations refuse invalid or overlapping groups before dispatch; declared ownership lanes remain enforced inside isolated parallel workspaces; opt-in phase/workflow `blast_radius` ceilings atomically roll back writes beyond declared artifact-volume bounds; `INWARD_MANIFEST.yaml` pins shipped prompts, YAML configs, and static ownership policy; and a new `phase_type` contract executes in a staged clone until the operator promotes the verified output with `approve-maiden`.

The 0.8 release includes the completed hardening pass. One composed gate runs the source checks, generated-doc verification, structural wheel/sdist inspection, SPDX metadata checks, private-surface scrubbing, `twine check`, and a fresh-venv smoke over the installed CLI. It found and fixed an empty-eval false pass, a stale assistant-guide registry URL, and a package `__version__` drift that the release suite now prevents.

The public first-harness gate is green. A fresh live Siteline 2.3.0 scan on 2026-08-05 UTC scored the deployed site A, 97/100, with Level 4 machine enablement at 16/18. The scan fetched the truthful `agents.json`, local CLI manifest, machine-readable changelog, RFC 9116 security contact, sitemap, and task routes while the declarations continued to deny a hosted API, hosted service, or MCP server. Siteline did not retain the fresh response in its public result store; the request ID, response hash, provenance, score, and that retrieval residual are preserved in [the tracked release-gate audit](audits/siteline-live-result-2026-08-05.json).

Cross-repo authority, dependency direction, and release propagation are defined in `ECOSYSTEM.md` and `ecosystem.yaml`. `python3 scripts/ecosystem_status.py` provides the offline local status view; use its optional `--github` mode only for non-authoritative release and pull-request observations.

## Verified baseline

Verified for the 1.1.0 release on 2026-08-20: the composed release gate passed with 433 tests, one environment-dependent skip, 50/50 evals, all six shipped authoring contracts, both manifests, ecosystem and generated-doc validation, the ten-page search contract, isolated wheel and sdist inspection, `twine check`, and a fresh-install smoke that exercised the ownership inspector from the built wheel.

Verified for the 1.0.0 release on 2026-08-09: the composed release gate passed with 413 tests, one environment-dependent skip, 50/50 evals, all six shipped authoring contracts, both manifests, ecosystem and generated-doc validation, isolated wheel and sdist inspection, `twine check`, and a fresh-install smoke.

Verified locally on 2026-08-04:

- `python3 -m pytest -q`: 352 passed, 1 skipped in the release-gate environment.
- `python3 -m harness.cli eval`: 47/47 passed.
- `python3 -m harness.cli verify-manifest`: passed, 13 files.
- `python3 -m harness.cli verify-inward-manifest`: passed, 9 files.
- `python3 scripts/build_docs_html.py --check`: passed, 8 pages.
- Built wheel and sdist: `twine check`, structural inspection, and fresh-install smoke passed.
- `git diff --check`: clean.

Skip counts depend on the available local sandbox and live-provider configuration. Treat the commands and outcomes as the contract, not a permanently fixed test count.

Downstream propagation was verified during the 2026-08-04 MDT closeout:

- Harnessie Verify exact-commit CI passed all four Ubuntu jobs, including the previously skipped unsafe-trigger guard; `v0.1.1` and `v0` resolve to release commit `7d22949`.
- A clean consumer fetch of `snapsynapse/harnessie-verify-action@v0` installed Harnessie 0.8.0.
- The Homebrew formula upgraded an installed 0.7.1 to 0.8.0 from source, then passed strict online audit, formula test, linkage, and installed-metadata checks.
- Local and public formula bytes matched, and ecosystem status reported both downstream pins as `match`.

## Current cross-repo state

- `snapsynapse/harnessie-verify-action`: the clean local checkout and remote `main` are at `2aa3859`. Release v0.1.2 is Latest, stable `v0` resolves to the same commit, and the default core pin remains 1.0.0 pending the gated 1.1.0 update. The observed non-blocking residual is GitHub's Node 20 deprecation warning for `actions/checkout@v4`; that dependency update is owned by the action repository.
- `snapsynapse/homebrew-tap`: the clean local checkout and remote `main` are at `53b8b61`, and public bytes match local. The public formula installs Harnessie 1.0.0 from the immutable PyPI sdist with SHA-256 `40c2daa307d71a4687321205fac8fc1a24b6778c4412fb1f20cb2b20f89bd787`, declares the audited `libyaml` dependency plus a rust build dependency for the rpds-py resource, and has no open pull request.
- `snapsynapse/harnessie-engine-wrappers`: v0.1.0 is released from `ad3d759`. CI passed its real macOS-14 containment probe and its Ubuntu unsupported-platform refusal; release archives, wheel, and `SHA256SUMS` are attached.
- This repo dogfoods `snapsynapse/harnessie-verify-action@v0` in `.github/workflows/verify-pr-claims.yml`. A live verdict still depends on the repository verifier endpoint/model variables and API-key secret.
- GitHub `main`, tag `v1.1.0`, the GitHub Release, and PyPI carry the core 1.1.0 release. Exact-commit wheel, sdist, structural inspection, `twine check`, and fresh-install checks passed before publication. The assistant-guide DNS anchor and hosted re-verification remain the explicit post-publication trust step.

## Handoff disposition

The detailed inventory and relevance assessment is in `audits/handoff-relevance-2026-07-21.md`. In short:

- The delivered 0.3 through 0.5 rotation packets, site-refresh packet and assets, consolidated session log, and retired position sweep were removed after the audit. Tests, evals, decisions, the tracked audit, and git history preserve the durable evidence.
- `handoffs/HANDOFF-protocol-resistant-mechanisms.md` remains design input, not an executable handoff.
- `handoffs/skills-inventory-preliminary.md` remains a private standing research task and needs a fresh inventory before any adoption decision.
- `handoffs/scrub-list.txt` remains an active pre-commit control.

## Recommended work order

1. Publish and verify Harnessie 1.1.0 on GitHub and PyPI from the exact tagged commit.
2. Test that public package in Harnessie Verify, release the updated action, and move stable `v0` only after CI passes.
3. Update Homebrew from the immutable PyPI 1.1.0 sdist, then pass strict online audit, from-source upgrade, formula test, and linkage checks before pushing.
4. Rotate `_assistant-guide.harnessie.com` to the 1.1.0 guide hash, confirm public DNS, run the hosted GuideCheck verifier, and update public trust copy only if the new bytes re-earn the level.
5. Keep the six v1 authoring contracts frozen. Additive schema changes require explicit defaults and compatibility fixtures; breaking changes require a new major schema version and migration path.
6. Treat `PLUGIN_CONTRACT.md` as the complete v1 plugin trust decision. Do not add local-file discovery, automatic loading, configuration namespaces, or an untrusted execution mode without a separately versioned design.
7. Keep multi-orchestrator handoffs deferred unless a documented real job proves a single orchestrator insufficient. Structured memory frontmatter and macOS temporary-write parity remain post-1.0 candidates pending evidence.

## Operator-attended or external checks

- Configure the dogfood verifier repository variables and secret if live PR verdicts are desired.
- Live provider scorecards remain explicit opt-in operations via `HARNESSIE_LIVE=1`.
- Rotate the GuideCheck DNS anchor and run hosted verification only after the 1.1.0 guide is live. Until then, 1.0.0 is the last independently anchored guide receipt.

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
