# Handoff relevance audit, 2026-07-21

Scope: all files under `handoffs/`, the current tracked handoff in `NEXT.md`, the untracked 2026-07-07 code review, and release coupling with `harnessie-verify-action` and `snapsynapse/homebrew-tap`.

## Outcome

Most handoffs are historical evidence, not current instructions. GitHub `main` added one decisive forward item missing from the local checkout at the start of this audit: AIDR-0008 was arbitrated and authorized a separate probe-gated wrapper repository with an original minimal seed. That repository and the first Harnessie 0.8 write-safety slice now exist. The remaining 0.8 mechanics, smaller runtime hardening findings, and review of one Homebrew discovery PR remain current.

## File-by-file disposition

| Artifact | Disposition | Evidence and next action |
|---|---|---|
| `NEXT.md` | Active, refreshed | Rewritten to describe GitHub `main` at `eb07488`, the arbitrated AIDR-0008 work, 0.7.1, the 0.8 milestone, current cross-repo state, and current verification. |
| `handoffs/HANDOFF-CLAUDE.md` | Historical | Its v0.5 verification scope shipped. Current tests and evals supersede its expected counts. Retain only as rotation evidence. |
| `handoffs/HANDOFF-CODEX.md` | Historical | Its 0.4, 0.5, and 0.6 rungs shipped. Its operator-gate warnings remain useful history but are no longer the current work packet. |
| `handoffs/HANDOFF-GEMINI.md` | Historical | The 0.4 review lane shipped. No remaining execution item. |
| `handoffs/CHANGES.md` | Delivered design packet | The split hero, proof strip, video, animated pipeline, and generated-doc side rail are present in the live source. |
| `handoffs/Screenshot 2026-07-07 at 11.29.47 AM.png` | Historical source asset | Companion design evidence. No current execution item. |
| `handoffs/flowchart-ai.jpeg` | Historical source asset | Companion design evidence. No current execution item. |
| `handoffs/codex-session-notes.md` | Historical log | Retain append-only as rotation provenance. Do not use as current state. |
| `handoffs/v0.3.2-inventory.md` | Historical implementation packet | Its refusal and identifier work shipped. Retain as rationale for exclusions that later code may still depend on. |
| `handoffs/position-sweep/` | Retired | AIDR-0001 and AIDR-0002 now contain Arbitration, and the tenets are ratified. Do not resume the old sweep. |
| `handoffs/HANDOFF-protocol-resistant-mechanisms.md` | Relevant design input, not executable | The concession and real-stakes questions remain open, but the file depends on a source transcript and an unconfirmed Harnessie/Turnfile scope boundary. Route through a new decision or roadmap proposal before implementation. |
| `handoffs/skills-inventory-preliminary.md` | Relevant standing research, stale inventory | The assessment bar remains sound. Refresh sources and candidates before adopting anything; do not treat the 2026-07-06 shortlist as current. |
| `handoffs/scrub-list.txt` | Active control | Run its staged-diff check before every public commit. |
| `ROADMAP-PRIVATE.md` | Active private plan, pruned | The shipped 0.7 license and implementation block was obsolete and has been removed; AIDR-0008 now records the approved separate-repository execution boundary. |
| `audits/code-review-2026-07-07.md` | Mixed, untracked | Its P0 provenance, boundary wiring, and sovereign escalation findings were fixed before 0.7 shipped. Its parallel ownership, sandbox parity, provider-shape handling, memory-frontmatter, and release-claim drift findings remain relevant. |

## Cross-repo findings

### harnessie-verify-action

The local checkout was fast-forwarded from `c101caf` to remote `main` at `3a2f1bb`. The extra commit adds repository guidance files and does not change the action runtime or release. The action remains v0.1.0, its default `harnessie-version` remains 0.7.1, and Harnessie consumes the stable major tag `@v0`.

Completed this session: inspected the remote housekeeping diff and fast-forwarded the clean local checkout. No Harnessie source change was required.

### snapsynapse/homebrew-tap

The live formula is current at Harnessie 0.7.1 and uses the PyPI sdist with SHA-256 `a584cfbda10eeb4e6993077d5a766644a248204cde68caff23988db7382ba4c7`. Draft PR [#1](https://github.com/snapsynapse/homebrew-tap/pull/1) adds Harnessie to the README formula list and install example without changing the formula.

Completed this session: the README change passed `ruby -c Formula/harnessie.rb` and `git diff --check`, then was committed and pushed for review. Merging the draft remains an operator action.

### GitHub source of truth

GitHub `main` is `eb07488`, two commits ahead of the checkout used for the first audit pass. Commit `228fb47` arbitrates AIDR-0008; commit `eb07488` adds repository guidance. The latest CI and Pages runs for `eb07488` succeeded. GitHub reports no open pull requests or issues, and v0.7.1 remains the latest release.

The tracked GitHub `NEXT.md` still said AIDR-0008 was open even though the decision record was arbitrated. This audit treats the decision record as authoritative and corrects `NEXT.md` accordingly.

The approved work now ships in [snapsynapse/harnessie-engine-wrappers](https://github.com/snapsynapse/harnessie-engine-wrappers) v0.1.0. Commit `ad3d759` passed a real macOS-14 deny/allow/symlink containment probe and an Ubuntu fail-closed unsupported-platform check. Release archives, wheel, and `SHA256SUMS` are attached.

## Current implementation priorities

### Separate repository delivered under AIDR-0008

The fresh-authored Apache-2.0 seed provides the minimal macOS Seatbelt reference wrapper, shared credential deny policy, and admission probe. The first adversarial run exposed a crucial false-positive shape: a denied read alone can look successful when `sandbox-exec` itself fails under an outer sandbox. The shipped admission contract therefore requires denied direct and symlink reads plus a successful allowed control. Contributor outreach may now follow; another developer's work still lands only through their own consenting contribution.

### First slice: parallel write ownership and 0.8 conflict refusal

Implemented on `agent/handoff-and-write-safety`. Opt-in `writes` declarations use exact files and directory subtrees; partial opt-in, ambiguous input, portable case/Unicode aliases, and overlaps refuse before workspace creation or dispatch. Parallel registries receive an isolated ownership view that enforces declared operator, agent, and collaborative lanes without sharing first-writer claims across physically separate phase workspaces.

Acceptance evidence proves:

- Overlapping declared write paths refuse the whole group before any phase starts.
- Operator-owned paths remain denied inside a parallel phase.
- Disjoint declared paths still execute concurrently.
- Refusal is recorded and downstream phases do not run.

### Subsequent 0.8 slices

1. Blast-radius ceilings with atomic stop semantics and per-phase/per-run counters.
2. Inward manifest for role prompts and shipped configs, with record-or-refuse policy on divergence.
3. Maiden-voyage propose-only execution with explicit operator approval before write behavior unlocks.

### Smaller hardening backlog

- Convert malformed JSON and unexpected response shapes from both provider adapters into sanitized `model_error` turns instead of exceptions.
- Serialize memory frontmatter structurally and validate dates/multiline scalar inputs.
- Align macOS temporary-path behavior with the documented workspace-only write claim, or narrow the public claim and test the actual boundary.
- Add a single release gate that composes pytest, eval, manifest verification, generated-doc checks, provenance consistency, and public-surface scrubbing.

## Gates and non-actions

- Do not copy or adapt third-party wrapper code while implementing AIDR-0008. Author the seed fresh, then invite consenting contributions.
- Do not resume the retired position sweep.
- Do not use historical expected test counts as release assertions.
- Do not stage private `handoffs/` or `ROADMAP-PRIVATE.md` content.
