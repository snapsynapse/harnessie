# Harnessie INTENT

Tier: personal-utility (private). Trajectory: public / portfolio-bound.
Canonical home (registered, private until launch): https://harnessie.com/

This document follows the portfolio Repo Standards INTENT.md section template. Harnessie is not yet a portfolio component; this INTENT is pre-applied so a later promotion is clean.

## 1. What this is

Harnessie is a brain-agnostic multi-agent harness: an orchestrator that decomposes goals, cheap swappable worker models that execute, and independent verifiers that gate every result. It ships as a Python library and CLI with verification gates, cost routing, file-based memory, a resumable run journal, and a layered prompt-injection defense. The model is a configuration seam, not a code dependency.

## 2. Why it exists

Most AI products fail at the harness layer, not the model: unclear tool boundaries, no approval policy, brittle state, no evaluation loop. Harnessie encodes those as first-class primitives so a cheap or open-source model under a strong harness can approach frontier-model results, and a frontier model under the same harness is kept honest. It was built from an operating charter to match or exceed frontier behavior while remaining brain-swappable.

## 3. Design invariants

1. Brain-agnostic seam: swapping the model is a `config/models.yaml` edit, never a harness code change.
2. Guarantees live in code, at the registry, loop, and OS layer, not in prompts a model can ignore.
3. Fail closed everywhere: an unenforceable control is refused, not skipped (an unverifiable verdict, a missing sandbox, a denied approval all halt).
4. Nothing ships on an agent's say-so: every side-effecting phase passes deterministic checks plus an independent fresh-context verifier.
5. Silence is never success: every loop ends in an enumerated stop condition.
6. Routing is config, not model self-assessment; escalation is earned by gate failures, not predicted.
7. Memory is small, scoped, and provenance-bearing.

## 4. Scope boundaries

In scope: the harness runtime (models, tools, loop, verify, routing, memory, state, roles, quarantine, sandbox, runner, CLI), role prompts, workflow definitions, the security layers, and their tests.

Out of scope: being an open standard or spec; a hosted surface or web UI; model training or fine-tuning; secrets management beyond env-var hygiene and the mechanical guards; non-macOS sandbox backends (roadmapped, currently fail closed).

## 5. Conformance philosophy

N/A because harnessie is a tool, not an open standard. It makes no external conformance claims and has no verifier-anywhere model. Internal correctness is asserted by the test suite and the threat model in `SECURITY.md`.

## 6. Admission criteria for changes

N/A as a formal open-spec gate. The working change discipline is: the full test suite stays green; no documented security invariant (`SECURITY.md`) is weakened without a recorded rationale; the affected docs and `CHANGELOG.md` are updated in the same change; shipped configs and workflows still parse (`tests/test_repo_configs.py`).

## 7. Relationships to other PAICE standards

Harnessie is not currently a PAICE portfolio component (private, personal-utility). Its multi-agent structure is modeled on the Safe Agentic Workflow (SAW) patterns. Non-binding future integrations, if promoted: AIDR for decision records, Turnfile for a multi-agent session format, Graceful Boundaries for agent refusal surfaces, GuideCheck if it ever ships an `assistant-guide.txt`. None are adopted today.

## 8. Exceptions to Repo Standards

- Tier is personal-utility (private, not in `portfolio.yaml`), so hosted, open-spec, agent-facing, and commercial matrix rows are N/A. Trajectory is public/portfolio; promotion will trigger those rows via `repo-standards-audit` plus `repo-polish`.
- `.claude/` is gitignored as a full directory per the all-tier rule. Consequence recorded for maintainers: the repo is dogfooded under Claude Code via a local, untracked `.claude/` (worker and verifier subagent wrappers, a `/run-workflow` command, and a PostToolUse pytest hook). The canonical, tracked source for those role prompts is `agents/`; the CLI (`python3 -m harness.cli`) is the primary interface and needs no `.claude/`.
- `INTENT.md` is present although the personal-utility tier does not require it, pre-applied for the public/portfolio trajectory.
- `docs/` is reserved for the canonical web page (https://harnessie.com/). Per the portfolio Repo Standards docs/-publish rule, when Harnessie goes public GitHub Pages will publish from `main` `/docs`, so that directory is kept as the future public served tree and holds only a placeholder today. All internal engineering and planning docs (ARCHITECTURE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN, PROMPTS, session-url-log, source-verification.json) live at the repo root, which stays private and unserved. Pages is not yet enabled.

## 9. Changelog

- 2026-07-06 - Initial INTENT. Repo-standards conformance pass before the first commit: baseline `.gitignore`, `.claude/` untracked per the all-tier rule, `INTENT.md` added. Harness at v0.1.0 (see `CHANGELOG.md`).
