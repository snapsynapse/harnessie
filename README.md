# Harnessie

A brain-agnostic multi-agent harness: orchestrator, swappable workers, independent verifiers, verification gates between every phase, consent-based orchestration, per-agent file ownership, adversarial decision records with human-only arbitration, self-maintaining project memory with stamped provenance and dated expiry, cost routing as declared config, and a tamper-evident audit log that records operator and agent actions in one composite timeline.

Harnessie is built to be the safest and easiest first AI harness for people. "Safest" is not a slogan here; it is a set of checkable properties: guarantees live in code, not prompts ([GOVERNANCE.md](GOVERNANCE.md)); every control that cannot be enforced fails closed instead of running unenforced; nothing ships on an agent's say-so (independent fresh-context verifiers gate every side-effecting phase); an OS sandbox confines shell work; a seven-layer prompt-injection defense with a written threat model ([SECURITY.md](SECURITY.md)) covers the rest; and a hash-chained audit log records every agent and operator action in one tamper-evident timeline. If you find a way to break any of these claims, that is a bug report we want. "Easiest" means the person running it does not need to be a developer: runs carry declared token and dollar ceilings, every halt is a named condition with one plain operator action, and disagreement between agents becomes a human decision, never a silent merge.

The operating thesis: the harness structure carries the quality floor, the model carries the ceiling. Run it with Claude Fable 5 as the orchestrator and it exploits effort dials, long autonomous turns, and verifier subagents. Swap the workers (or everything) for Haiku, GLM, Qwen, or any OpenAI-compatible local endpoint by editing one YAML file, and the gates, jails, budgets, and retry ladders keep output honest.

Beneath that thesis sit five engineering habits, each proven separately in the author's other tools and standards before it landed here as code: deterministic checks run before any model judgment (the gate order in [docs/GUIDE.md](docs/GUIDE.md)); evaluation comes before implementation — a governance mechanic without a red-then-green scenario pair does not merge ([EVALS.md](EVALS.md)); remembered facts carry verified and verify-by dates and expire visibly, never silently ([GOVERNANCE.md](GOVERNANCE.md)); every agent and operator action lands in one hash-chained, tamper-evident timeline ([docs/threat-model.md](docs/threat-model.md)); and any control that cannot be enforced fails closed rather than running unenforced ([SECURITY.md](SECURITY.md)). The same habits produced the standards Harnessie adopts — [Turnfile](https://turnfile.work/), [AIDR](https://aidr.work/), [Graceful Boundaries](https://gracefulboundaries.dev/) — which is why they fit together.

## Quick start

```bash
pip install -e ".[dev]"
python3 -m pytest -q                 # mock brain, no network
python3 -m harness.cli eval          # deterministic eval scorecard
python3 -m harness.cli verify-manifest
export ANTHROPIC_API_KEY=sk-ant-...  # or point tiers at a local endpoint
python3 -m harness.cli run workflows/build-and-verify.yaml --goal "a CLI todo app with tests"
python3 -m harness.cli report <run_id>
python3 -m harness.cli audit <run_id>   # verify the hash chain + governance timeline
```

Installed CLI usage can scaffold a fresh project layout:
```bash
harnessie init my-harnessie-project
```

Worked end-to-end example with sample data: [examples/policy-compliance/README.md](examples/policy-compliance/README.md).

## Documentation

- [docs/quickstart.md](docs/quickstart.md): the gentlest path for someone who has never cloned a repo or written YAML, assuming no git or shell fluency, with a glossary and an honest Windows/WSL2 page.
- [docs/getting-started.md](docs/getting-started.md): the five-minute path from install to a green run and reading the evidence.
- [docs/GUIDE.md](docs/GUIDE.md): the complete user guide, concepts through extension, including workflow authoring, brain configuration, ownership, governance, and the halt-recovery table.
- [docs/brains.md](docs/brains.md): the brain-agnostic receipt, the models actually run under the harness with a link to the record that proves each.
- [assistant-guide.txt](assistant-guide.txt): a bounded, human-verifiable guide (GuideCheck Level 3 profile) for an assistant reviewing a Harnessie checkout before you authorize a run; served at [harnessie.com/.well-known/assistant-guide.txt](https://harnessie.com/.well-known/assistant-guide.txt) with a sidecar manifest for provenance.

The engineering references below (ARCHITECTURE, GOVERNANCE, SECURITY, ROADMAP) sit at the repo root; the user-facing guides live under `docs/`.

## Layout

```text
harness/            the runtime: models/ tools/ loop verify routing memory state roles quarantine
                    sandbox ownership adversarial audit runner cli events
agents/             role prompts (markdown): orchestrator.md, workers/, verifiers/
workflows/          declared phase sequences (YAML) with per-phase gates, task classes, and
                    adversarial contested phases (mode: adversarial)
config/models.yaml  model tiers, routing table, budgets: the ONLY file to edit to swap brains
OWNERSHIP.yaml      ownership lanes + first-writer auto-claims; operator-owned, agents cannot reach it
decisions/          the repo's own AIDR decision records (AIDR-0001 = v0.2 direction,
                    AIDR-0002 = v0.3 direction; both human-arbitrated 2026-07-06
                    with independent positions from four providers)
memory/             project memory: MEMORY.md index + facts/ (stamped provenance, verify_by
                    expiry) + archive/ (expired facts; nothing deletes) — maintained by
                    workflows/memory-triage.yaml under approval gates
examples/           worked end-to-end example (policy-compliance) with sample data
runs/               per-run journal.jsonl (resume ledger) + events.jsonl (hash-chained audit)
                    + proofs/ + decisions/ (contested-phase records) (gitignored)
evals/              deterministic scorecards over mock-brain golden/risky/recovery scenarios
docs/MANIFEST.yaml  trust-bundle integrity manifest for machine-readable public artifacts
tests/              the done-tests for every subsystem
docs/               reserved for the canonical web page (GitHub Pages publish source once public)
*.md at root        ARCHITECTURE, GOVERNANCE, SECURITY, ROADMAP, IMPLEMENTATION_PLAN, PROMPTS, EVALS, NEXT,
                    session-url-log, plus INTENT (9-section standard), CHANGELOG, README,
                    LICENSE (Apache-2.0) + NOTICE; source-verification.json is the build provenance data
```

Dogfooding this repo under Claude Code uses a local `.claude/` (subagent defs, a `/run-workflow` command, a pytest hook). Per repo convention `.claude/` is gitignored, so it does not ship; the canonical role prompts it wraps live in `agents/`, and the CLI is the primary interface.

## Requirements

Python 3.11+ and PyYAML (installed by `pip install -e .`). The stdlib-only model adapters need no vendor SDK. The OS sandbox uses native macOS `sandbox-exec` when it can actually apply a Seatbelt profile; on Linux it uses bubblewrap, firejail, or docker (in that order of preference). Every backend is admitted only after a startup smoke test proves it can confine here; a present-but-unusable backend, and any platform with none (Windows), fails closed so shell-using workflows are blocked rather than run unconfined (see [SECURITY.md](SECURITY.md)).

Live provider scorecards are opt-in and never part of the default no-network suite. With credentials and a local endpoint configured, run:
```bash
HARNESSIE_LIVE=1 \
HARNESSIE_OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1 \
python3 -m harness.cli eval --live
```
Without `HARNESSIE_LIVE=1` or provider configuration, the live scorecard reports explicit `SKIP` rows and exits cleanly.

## Design in one breath

Goal enters, orchestrator (frontier, high effort) decomposes it into task packets with acceptance criteria and out-of-scope fences; task packets are offers, and workers consent (or decline with a counter-proposal) before side-effecting tools unlock; workers (cheap tiers) execute inside a jailed workspace with allowlisted tools, owning the files they create and never each other's; every worker phase exits through a gate that runs deterministic checks first, then an independent fresh-context verifier that never sees the worker's reasoning and fails closed; contested decisions fan out to an adversarial panel whose positions, objections, and dissent land in a decision record only a human may arbitrate; failures reformulate the task with evidence and escalate effort-then-tier before halting for a human; everything is journaled, budgeted, resumable, hash-chain audited, and leaves proof artifacts on disk.

For long runs, approval-gated tools can be authorized by a small headless policy file:
```yaml
allow:
  - tool: expire_fact
    phase: triage
deny:
  - tool: deploy
```
Run with `--approval-policy approvals.yaml`, or use `--approve-interactive` to prompt on a TTY. Independent phases can fan out by sharing a `parallel:` label; each runs under `workspace/.phases/<phase>` and gates independently before later phases see its report.

Optional extra review can use local OpenAI-compatible endpoints such as Ollama or CLI fan-out across agents. That is useful evidence, especially for patches touching orchestration, but it does not replace the deterministic suite: `pytest`, `harnessie eval`, manifest verification, and scrub/audit checks remain the proof surface.

Full rationale and the verified source-to-decision map: [ARCHITECTURE.md](ARCHITECTURE.md). Governance layer (consent, ownership, contest, audit): [GOVERNANCE.md](GOVERNANCE.md). Prompt-injection and secret-handling model: [SECURITY.md](SECURITY.md). The "safest" claim as a falsifiable table, each row citing enforcing code and its test, versus prevailing harness patterns: [docs/threat-model.md](docs/threat-model.md). What comes next and platform support: [ROADMAP.md](ROADMAP.md).

## What governs a run

A run's behavior is not in one file; each decision has one owner. To predict or change what a run will do, edit the owner, not the prompt:

| Decision | Governed by |
|---|---|
| Which model runs each task class, and how to swap brains | `config/models.yaml` (tiers + routing table) |
| Token and dollar ceilings, effort per task class | `config/models.yaml` (budget + routing) |
| Which phases run, in what order, with which gates and verifiers | the workflow YAML in `workflows/` |
| Which files each agent may write | `OWNERSHIP.yaml` (lanes + first-writer claims) |
| What each role may do (tools, shell allowlist, approval) | the tool registry (`harness/tools/builtin.py`) + role prompts in `agents/` |

## When a run halts

Silence is never success: every run ends in a named stop condition, and each maps to one operator action. Resuming is `harnessie run <same workflow> --goal ...` with the same run id: resume re-runs only phases that did not pass, so fixing the cause and re-running is safe.

| Stop condition | What it means | What to do |
|---|---|---|
| `complete` / phase `passed` | task done, gate satisfied | nothing; the next phase proceeds |
| `declined` | the worker declined the offered task packet | read the counter-proposal in the report; revise the packet or accept the objection, then re-run |
| `needs_human` | a gate's checks or verifier failed after the retry ladder exhausted | read the proof artifacts under `runs/<id>/proofs/` and the report; fix the task or the acceptance criteria; re-run |
| `needs_arbitration` | a contested phase produced dissent | open `runs/<id>/decisions/DR-<phase>.md`, record your arbitration decision in it, then re-run (resume keys on that record) |
| `stuck` | the model repeated an identical failing or refused call | inspect the refusal (`harnessie audit <id>`); fix the tool grant, allowlist, or task; re-run |
| `budget` | the run hit its token or dollar ceiling | raise the ceiling in `config/models.yaml` or narrow the goal; re-run |
| `max_steps` | the loop hit its step ceiling without completing | raise `max_steps` for the phase or simplify the task |
| `model_error` | the provider errored twice in a row | check the endpoint and API key; re-run |
| `no_action` | the model produced no tool call even after a nudge | usually a role-prompt or model-fit issue; check the role prompt in `agents/` |

## Built on open standards

Harnessie's governance mechanics are code-enforced imports of two open, vendor-neutral standards, and the design philosophy beneath both:

- [Turnfile](https://turnfile.work/): consent-based coordination, ownership lanes, authority order, and bounded rebuttal became the task-packet offer contract, `OWNERSHIP.yaml`, and the objection rounds in contested phases.
- [AIDR](https://aidr.work/): the decision-record lifecycle, preserved dissent, human-only arbitration, and structurally earned claims became the contested-phase records in `decisions/` and `runs/<id>/decisions/`. This repo dogfoods AIDR for its own direction decisions.
- [The Aggregated Intelligence tenets](https://paice.foundation/papers/aggregated-intelligence-tenets.html): intelligence lives in the arrangement, not the node; disagreement is the engine, not the exhaust; independence before influence; consensus is evidence, never authority; authority is human because accountability is human. The full tenet-to-mechanism mapping is [GOVERNANCE.md](GOVERNANCE.md) §7.

These are lesson imports, not conformance claims: Harnessie asserts no Turnfile or AIDR conformance. If the harness makes you ask why its rules work, those standards are the answer.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the eval-first change discipline, and how consequential decisions are recorded. Bug and feature templates live under [.github/](.github/).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE) (copyright Snap Synapse LLC; trademark and PAICE.work PBC spec/code carveouts).
