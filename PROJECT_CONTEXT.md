# PROJECT_CONTEXT.md — Harnessie

Context for content, docs, and communication skills working on this project.

## What it is

Harnessie is a brain-agnostic multi-agent harness — an orchestrator, swappable workers,
and independent verifiers with a verification gate between every side-effecting phase.
It positions itself as "the safest and easiest first AI harness for people," where
"safest" is a set of checkable, falsifiable properties (guarantees in code not prompts,
fail-closed controls, independent fresh-context verifiers, an OS sandbox, a seven-layer
prompt-injection defense, and a hash-chained tamper-evident audit log) and "easiest"
means the operator does not need to be a developer (declared token/dollar ceilings,
named halt conditions each with one plain operator action, disagreement surfaced as a
human decision rather than a silent merge).

Shipped as the `harnessie` Python package (Apache-2.0, current 0.7.1). The verifier also
ships standalone as a GitHub Action (Harnessie Verify) for gating PRs.

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

## Current status (2026-07-12)

Active and healthy. v0.7.1 live on PyPI, the Homebrew tap, and the GitHub Marketplace;
docs site live; GuideCheck Level 4 confirmed. Public-facing doc pages under `docs/` are
generated from markdown via `scripts/build_docs_html.py` (edit markdown, rebuild, commit
both). AIDR-0008 is the one open decision awaiting arbitration. See NEXT.md for the
live session handoff and CHANGELOG.md for release history.
