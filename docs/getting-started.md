# Getting started with Harnessie

This is the five-minute path: install, prove the harness works offline, point it at a model, run a real job, and read the record it leaves behind. The full reference is [GUIDE.md](GUIDE.md).

New to this? You are welcome here. A harness is the structure you put around an AI model so it can do real work while you stay in control: it sets what the AI may do, checks the work before moving on, and writes down what happened. Harnessie is built to be a safe first one. This guide uses a terminal, but every command below is safe to run, and nothing reaches the network until you choose to add a key. If you have never used a terminal or cloned a repository, start with the gentler [quickstart.md](quickstart.md), which assumes no git or shell fluency and includes a glossary and a Windows/WSL2 page.

In more technical terms: Harnessie is a brain-agnostic multi-agent harness. An orchestrator decomposes a goal into task packets, cheap workers execute them inside a jailed workspace, and an independent verifier gates every phase before the next one starts. The structure carries the quality floor; the model carries the ceiling. You swap models by editing one YAML file.

## 1. Install

Requires Python 3.11 or newer. The only runtime dependency is PyYAML; the model adapters are standard-library, so no vendor SDK is needed.

```bash
git clone https://github.com/snapsynapse/harnessie.git
cd harnessie
pip install -e ".[dev]"
```

## 2. Prove it works offline

The test suite and the eval scorecard both run against a deterministic mock brain with no network. Run them first; if they pass, the harness is sound on your machine before any API key is involved.

```bash
python3 -m pytest -q            # unit + integration suite, mock brain
python3 -m harness.cli eval     # deterministic eval scorecard
python3 -m harness.cli verify-manifest
```

You should see the suite pass and the eval print one `PASS` line per scenario. Nothing here calls a provider or touches the network.

## 3. Point it at a brain

Models live in `config/models.yaml` as named tiers. Out of the box the `frontier`, `mid`, and `cheap` tiers are Anthropic models and read their key from an environment variable; the `local` tier is any OpenAI-compatible endpoint (Ollama, vLLM, llama.cpp, and similar).

Pick one:

```bash
export ANTHROPIC_API_KEY=...    # use the Anthropic tiers
```

Or run entirely local by leaving the key unset and routing task classes at the `local` tier in `config/models.yaml` (it already points at `http://localhost:11434/v1`). You never put a key in the file; the file names the environment variable, the harness reads it at run time.

To smoke-test real providers before a workflow, opt in explicitly:
```bash
HARNESSIE_LIVE=1 \
HARNESSIE_OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1 \
python3 -m harness.cli eval --live
```
Without the flag and provider configuration, live rows are shown as skipped.

## 4. Run a workflow

The simplest built-in workflow plans a code change, implements it, and gates it on tests plus an independent verifier.

```bash
python3 -m harness.cli run workflows/build-and-verify.yaml \
  --goal "a CLI todo app with tests"
```

Every run gets an id. The command prints it, and the run's artifacts land under `runs/<run_id>/`.

For a worked, data-backed example (assessing a policy against a list of obligations, with a verifier that catches fabricated citations) see [examples/policy-compliance/README.md](../examples/policy-compliance/README.md).

## 5. Read the evidence

A run never just says "done". It leaves a journal, a hash-chained event log, and proof artifacts. Two commands read them back:

```bash
python3 -m harness.cli report <run_id>   # phases, results, proofs
python3 -m harness.cli audit  <run_id>   # verify the hash chain + governance timeline
```

`report` shows what each phase did and where its proofs are. `audit` re-verifies the event log end to end (exit 0 clean, exit 1 if the chain was tampered with) and renders one composite timeline of agent and operator actions: consents, ownership claims and denials, structured refusals, gate verdicts, and any decision records.

## 6. When a run stops

Silence is never success. Every run ends in a named stop condition, and each maps to one operator action. The common ones:

- `complete`: the goal was met and every gate passed. Nothing to do.
- `needs_human`: a gate failed after the retry ladder was exhausted. Read the proofs under `runs/<id>/proofs/`, fix the task or the acceptance criteria, and re-run.
- `needs_arbitration`: a contested decision produced dissent. Open `runs/<id>/decisions/DR-<phase>.md`, record your decision in it, and re-run.
- `budget` or `max_steps`: the run hit a ceiling. Raise it in `config/models.yaml` or the phase, or narrow the goal.

Re-running is safe: resume re-runs only the phases that did not pass. The full table is in [GUIDE.md](GUIDE.md#when-a-run-halts).

## 7. Start your own project

To scaffold a fresh project layout (config, workflows, agents, ownership) rather than working inside this repo:

```bash
harnessie init my-project
```

## Where to next

- [GUIDE.md](GUIDE.md): the complete user guide, concepts to extension.
- [ARCHITECTURE.md](../ARCHITECTURE.md): why the harness is shaped this way, with the source-to-decision map.
- [GOVERNANCE.md](../GOVERNANCE.md): consent, ownership, contested decisions, and the audit model.
- [SECURITY.md](../SECURITY.md): the prompt-injection and secret-handling model, and the sandbox backends.
