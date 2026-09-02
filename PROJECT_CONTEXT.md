# PROJECT_CONTEXT.md — Harnessie

Context for content, docs, and communication skills working on this project.

## What it is

Harnessie is a brain-agnostic multi-agent harness — an orchestrator, swappable workers,
and independent verifiers with a verification gate between every side-effecting phase.
It positions itself as "the safest and easiest first AI harness for people," where
"safest" is a set of checkable, falsifiable properties (guarantees in code not prompts,
fail-closed controls, independent fresh-context verifiers, an OS sandbox, an eight-layer
prompt-injection defense, and a hash-chained tamper-evident audit log) and "easiest"
means the operator does not need to be a developer (declared token/dollar ceilings,
named halt conditions each with one plain operator action, disagreement surfaced as a
human decision rather than a silent merge).

Shipped as the `harnessie` Python package (Apache-2.0, stable 1.1.0). The verifier also
ships standalone as a GitHub Action (Harnessie Verify) for gating PRs. Current source
contains unreleased evidence-bound and structured-verdict work intended for the next
minor release; public copy must not attribute those additions to the 1.1.0 artifacts.

## Audience

- Operators / non-developers who want a safe first AI harness they can run with declared
  budgets and plain-language halts.
- Developers extending the harness or authoring workflows, brains, and role prompts.
- Reviewers and assistants vetting a Harnessie checkout before authorizing a run
  (served `assistant-guide.txt`, GuideCheck-verified).

## Style and tone

- Technical, precise, claim-and-evidence oriented: assertions are tied to enforcing code
  and its tests; "safest" is framed as a falsifiable table, not a slogan.
- Markdown conventions (enforced in-repo): plain headings, bare `https` URLs, no em
  dashes. Prose is dense and declarative; comments state constraints, not narration.
- Governance-forward voice: consent, ownership, contest, and audit are first-class.
  Decisions are recorded (AIDR) with preserved dissent and human-only arbitration.

## Key URLs

- Site: https://harnessie.com/ (GitHub Pages, served from `docs/`)
- Repo: https://github.com/snapsynapse/harnessie
- Assistant guide: https://harnessie.com/.well-known/assistant-guide.txt
- Marketplace action: https://github.com/marketplace/actions/harnessie-verify
- Adopted standards: https://turnfile.work/ , https://aidr.work/ ,
  https://gracefulboundaries.dev/ , https://paice.foundation/
- Package: PyPI `harnessie`; Homebrew `snapsynapse/tap/harnessie`

## Ownership

Copyright Snap Synapse LLC (author Sam Rogers, subscriptions@snapsynapse.com), with
trademark and PAICE.work PBC spec/code carveouts recorded in NOTICE.

## Current status (2026-09-01)

Active and healthy. v1.1.0 is the stable core release on PyPI, GitHub, and
Homebrew. The separately owned Verify Action v0.1.3 and stable `v0` tag pin the
same tested core release. Current `main` adds OpenAI Responses support,
evidence bundles, structured claim verdicts, Ringer regression fixtures, and
event-trace metrics; those changes are not yet a published release. The docs site is
live, and the dated 2026-08-05 Siteline scan scored it A, 97/100. Public-facing doc pages under `docs/` are generated
from markdown via `scripts/build_docs_html.py` (edit markdown, rebuild, commit both).
AIDR-0008 is arbitrated and executed in the independent engine-wrappers release train.
See NEXT.md for current source and release state and CHANGELOG.md for shipped history.

The current adoption wedge is verification of agent-produced changes. Ringer is the
first named composition surface because its task checks already consume process exit
codes. Harnessie supplies the independent, evidence-bound gate; the full orchestration
harness remains the growth path when governance requirements expand.

The three 1.0 slices are shipped: six stable v1 authoring schemas,
side-effect-free validation, runtime startup enforcement, cross-document checks, a
written compatibility and deprecation policy, and per-agent read-only sandbox overlays
that enforce ownership for child processes. Installed tool extensions now use one
explicit versioned entry-point mechanism with an operator-trusted in-process boundary,
registry-mediated calls, immutable provenance, and exact resume receipts. Untrusted
plugins remain unsupported.

Harnessie's Golden Rule is now a public and executable product surface: read together,
write only what you own. The read-only `harnessie ownership` command explains the exact
ledger decision, and the zero-model collision example proves a second agent cannot
overwrite the first agent's artifact through the built-in write path.

The 1.1.0 assistant guide re-earned hosted GuideCheck Level 4 on 2026-08-21 UTC with zero blocking findings. Its served bytes, sidecar, independently controlled DNS TXT, and repository-file anchor match SHA-256 `f7d45f62f2941f5541d1342be0fc037c1ef7fc3e06f44ad39cf94a5b50e5080d`.
