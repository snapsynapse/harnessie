# Next session handoff

## Current state

Harnessie 0.8.0 is shipped on PyPI and GitHub, and its downstream release train is complete. Harnessie Verify v0.1.1 and stable `snapsynapse/harnessie-verify-action@v0` pin Harnessie 0.8.0; the public Homebrew formula also installs 0.8.0. `python3 scripts/ecosystem_status.py` reports both downstream pins matching core.

The next public milestone is 1.0.0, extensibility earned. Its admission bar remains strict: stable configuration and workflow schemas with a deprecation policy, plugin dispatch that cannot bypass the registry, and per-lane sandbox profiles must preserve every shipped fail-closed guarantee.

The pre-1.0 correctness packet is complete on the current development head. Anthropic and OpenAI-compatible adapters now turn invalid JSON, malformed envelopes, invalid tool calls, and invalid usage counters into non-echoing provider error turns. Adversarial rebuttal agents now receive each peer position in full and exclude their own position by value, removing the truncation that previously produced a spurious objection.

`decisions/AIDR-0008` was arbitrated on 2026-07-16 and executed on 2026-07-21 as [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers). The fresh-authored Apache-2.0 v0.1.0 seed contains a macOS Seatbelt reference wrapper, shared credential deny policy, and a deny/allow/symlink admission probe. Its macOS-14 CI probe passed, unsupported and unavailable backends fail closed, and the consent boundary remains intact: other developers' work enters only through their own consenting contribution.

All four 0.8 mechanics are shipped. Opt-in parallel `writes` declarations refuse invalid or overlapping groups before dispatch; declared ownership lanes remain enforced inside isolated parallel workspaces; opt-in phase/workflow `blast_radius` ceilings atomically roll back writes beyond declared artifact-volume bounds; `INWARD_MANIFEST.yaml` pins shipped prompts, YAML configs, and static ownership policy; and a new `phase_type` contract executes in a staged clone until the operator promotes the verified output with `approve-maiden`.

The 0.8 release includes the completed hardening pass. One composed gate runs the source checks, generated-doc verification, structural wheel/sdist inspection, SPDX metadata checks, private-surface scrubbing, `twine check`, and a fresh-venv smoke over the installed CLI. It found and fixed an empty-eval false pass, a stale assistant-guide registry URL, and a package `__version__` drift that the release suite now prevents.

The public first-harness gate is green. A fresh live Siteline 2.3.0 scan on 2026-08-05 UTC scored the deployed site A, 97/100, with Level 4 machine enablement at 16/18. The scan fetched the truthful `agents.json`, local CLI manifest, machine-readable changelog, RFC 9116 security contact, sitemap, and task routes while the declarations continued to deny a hosted API, hosted service, or MCP server. Siteline did not retain the fresh response in its public result store; the request ID, response hash, provenance, score, and that retrieval residual are preserved in [the tracked release-gate audit](audits/siteline-live-result-2026-08-05.json).

Cross-repo authority, dependency direction, and release propagation are defined in `ECOSYSTEM.md` and `ecosystem.yaml`. `python3 scripts/ecosystem_status.py` provides the offline local status view; use its optional `--github` mode only for non-authoritative release and pull-request observations.

## Verified baseline

Verified on the current development head on 2026-08-09: the composed release gate passed with 377 tests, one environment-dependent skip, 47/47 evals, both manifests, ecosystem and generated-doc validation, isolated wheel and sdist inspection, `twine check`, and a fresh-install smoke.

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

- `snapsynapse/harnessie-verify-action`: the clean local checkout and remote `main` are at `7d22949`. Release v0.1.1 is Latest, stable `v0` resolves to the same commit, and the default core pin is 0.8.0. The observed non-blocking residual is GitHub's Node 20 deprecation warning for `actions/checkout@v4`; that dependency update is owned by the action repository.
- `snapsynapse/homebrew-tap`: the clean local checkout and remote `main` are at `2d64648`. The public formula installs Harnessie 0.8.0 from the immutable PyPI sdist with SHA-256 `c9caffef61a8b1f9569cee36ede59f59c3dc8c66a47e500ecc090d445111f5e7`, declares the audited `libyaml` dependency, and has no open pull request.
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

1. Refine the first acceptance-complete 1.0 slice: inventory every user-authored configuration and workflow surface, define versioned strict schemas, specify compatibility and deprecation behavior, add validation that does not start a run, and preserve current 0.8 inputs as explicit fixtures.
2. Reconcile `IMPLEMENTATION_PLAN.md` with that contract and clean the stale pre-public exceptions in `INTENT.md` during the planning slice so the roadmap, implementation order, and project status agree.
3. Close per-lane confinement before general plugin admission. An interpreter or plugin must not write outside its assigned lane merely because the path remains inside the workspace; unsupported profiles fail closed.
4. Define the plugin trust boundary before coding its loader. Trusted installed extensions may run in process while their tool invocations remain registry-mediated; untrusted extension code requires out-of-process confinement. Choose one extension mechanism rather than leaving Python package entry points and discovered `tools/*.py` ambiguous.
5. Keep multi-orchestrator handoffs deferred unless a documented real job proves a single orchestrator insufficient; it is not an unconditional 1.0 gate. Keep engine-wrapper contributions consent-based and probe-gated.
6. The smaller remaining core backlog is structured memory frontmatter and macOS sandbox parity for non-workspace temporary writes.

## Operator-attended or external checks

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
