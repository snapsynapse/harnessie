# Harnessie

A brain-agnostic multi-agent harness: orchestrator, swappable workers, independent verifiers, verification gates between every phase, file-based memory with provenance, and cost routing as declared config.

The operating thesis: the harness structure carries the quality floor, the model carries the ceiling. Run it with Claude Fable 5 as the orchestrator and it exploits effort dials, long autonomous turns, and verifier subagents. Swap the workers (or everything) for Haiku, GLM, Qwen, or any OpenAI-compatible local endpoint by editing one YAML file, and the gates, jails, budgets, and retry ladders keep output honest.

## Quick start

```bash
pip install -e ".[dev]"
python3 -m pytest -q                 # mock brain, no network
python3 -m harness.cli eval          # deterministic eval scorecard
export ANTHROPIC_API_KEY=sk-ant-...  # or point tiers at a local endpoint
python3 -m harness.cli run workflows/build-and-verify.yaml --goal "a CLI todo app with tests"
python3 -m harness.cli report <run_id>
```

Installed CLI usage can scaffold a fresh project layout:
```bash
harnessie init my-harnessie-project
```

Worked end-to-end example with sample data: [examples/policy-compliance/README.md](examples/policy-compliance/README.md).

## Layout

```text
harness/            the runtime: models/ tools/ loop verify routing memory state roles quarantine sandbox runner cli events
agents/             role prompts (markdown): orchestrator.md, workers/, verifiers/
workflows/          declared phase sequences (YAML) with per-phase gates and task classes
config/models.yaml  model tiers, routing table, budgets: the ONLY file to edit to swap brains
memory/             project memory: MEMORY.md index + facts/ with provenance frontmatter
examples/           worked end-to-end example (policy-compliance) with sample data
runs/               per-run journal.jsonl (resume ledger) + events.jsonl (audit) + proofs/ (gitignored)
evals/              deterministic scorecards over mock-brain golden/risky/recovery scenarios
tests/              the done-tests for every subsystem
docs/               reserved for the canonical web page (GitHub Pages publish source once public)
*.md at root        ARCHITECTURE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN, PROMPTS, session-url-log,
                    plus INTENT (9-section standard), CHANGELOG, README, LICENSE (MIT);
                    source-verification.json is the build provenance data
```

Dogfooding this repo under Claude Code uses a local `.claude/` (subagent defs, a `/run-workflow` command, a pytest hook). Per repo convention `.claude/` is gitignored, so it does not ship; the canonical role prompts it wraps live in `agents/`, and the CLI is the primary interface.

## Requirements

Python 3.11+ and PyYAML (installed by `pip install -e .`). The stdlib-only model adapters need no vendor SDK. The OS sandbox uses native macOS `sandbox-exec` when it can actually apply a Seatbelt profile; managed hosts that expose the binary but reject `sandbox_apply` are treated as sandbox-unavailable and shell-using workflows fail closed. On other platforms, shell-using workflows fail closed until a Linux backend is wired (see [SECURITY.md](SECURITY.md)).

## Design in one breath

Goal enters, orchestrator (frontier, high effort) decomposes it into task packets with acceptance criteria and out-of-scope fences; workers (cheap tiers) execute inside a jailed workspace with allowlisted tools; every worker phase exits through a gate that runs deterministic checks first, then an independent fresh-context verifier that never sees the worker's reasoning and fails closed; failures reformulate the task with evidence and escalate effort-then-tier before halting for a human; everything is journaled, budgeted, resumable, and leaves proof artifacts on disk.

Full rationale and the verified source-to-decision map: [ARCHITECTURE.md](ARCHITECTURE.md). Prompt-injection and secret-handling model: [SECURITY.md](SECURITY.md). What comes next and platform support: [ROADMAP.md](ROADMAP.md).
