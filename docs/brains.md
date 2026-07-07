# Brains run under Harnessie

Brain-agnostic is a testable claim, not a slogan. This page is the receipt: the models that have actually produced work under the harness, each linked to the on-disk record that proves it, plus the set you can swap to by editing one file.

Scope: the table below tracks models run under the harness at runtime, each backed by a decision record. The models that built Harnessie's own code are a separate and honest story, credited under [Built with](#built-with) at the end.

## Proven under the harness

Each of these formed an independent position in an adversarial contested phase, recorded verbatim with its model and provider in a hash-chained decision record. Different task classes route to different tiers, so a single contest draws genuinely different brains, which is what earns a record its `independent-positions` claim.

| Model | Provider | Role on record | Provenance |
|---|---|---|---|
| `claude-fable-5` | Anthropic | Frontier orchestrator; position author and record assembler | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `qwen3.6:35b-mlx` | Alibaba | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `gemma4:31b-mlx` | Google | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `gpt-oss:20b` | OpenAI | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `gpt-oss:120b-cloud` | OpenAI | Contested-phase participant inside `workflows/contested-decision.yaml` runs (Ollama Cloud via the openai-compat adapter); flipped oppose to recommend across the two rounds | [AIDR-0003](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md), [AIDR-0004](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) |
| `glm-4.7:cloud` | Z.ai | Contested-phase participant inside `workflows/contested-decision.yaml` runs (Ollama Cloud via the openai-compat adapter); its one malformed objection reply was recorded fail-closed as dissent and arbitrated as correct protocol behavior | [AIDR-0003](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md), [AIDR-0004](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) |
| `deepseek-v4-pro:cloud` | DeepSeek | Contested-phase participant (isolated cloud inference); round one's sharpest oppose, flipped by the redraft | [AIDR-0003](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md), [AIDR-0004](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) |
| `kimi-k2.5:cloud` | Moonshot | Contested-phase participant (isolated cloud inference) | [AIDR-0003](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md), [AIDR-0004](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) |
| `minimax-m2.1:cloud` | MiniMax | Contested-phase participant (isolated cloud inference) | [AIDR-0003](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0003-adopt-0-7-sovereignty-routing-and-containment.md), [AIDR-0004](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0004-adopt-redrafted-0-7-sovereignty-spec.md) |
| `glm-5:cloud` | Z.ai | Contested-phase participant inside `workflows/contested-decision*.yaml` runs; argued the winning round-one position and authored the round-two objection that caught a peer's fabricated citations | [AIDR-0005](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0005-escalation-headroom-option-a-plus-invariant.md) |
| `minimax-m3:cloud` | MiniMax | Contested-phase participant inside the three-brain panel (first position under the harness); named exactly what it could and could not verify read-only | [AIDR-0005](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0005-escalation-headroom-option-a-plus-invariant.md) |

Eight providers and eleven models across nine families, from frontier closed models through half-trillion-parameter cloud open-weights down to 20B local open-weights, all producing arbitrated positions under the same harness. AIDR-0003 and AIDR-0004 are the richest records so far: a six-model panel split 3-3 on the 0.7 sovereignty design, arbitration sent it back for redraft, and the same panel returned unanimous on the revision. AIDR-0005 repeated the pattern at design-detail scale with a three-brain panel, and its objection round did real adversarial work: one participant's fabricated line-number citations were caught by another and discounted in arbitration. Dissent that changed the spec, preserved verbatim. The decision the operator made in each case was a human's; every position is preserved, including the ones that did not win.

## Configured and swappable

Declared in [config/models.yaml](https://github.com/snapsynapse/harnessie/blob/main/config/models.yaml). Point any task class at any tier; the gates, jails, budgets, and audit stay identical. API keys come from environment variables, never the file.

| Tier | Model | Provider |
|---|---|---|
| frontier | `claude-fable-5` | Anthropic |
| mid | `claude-sonnet-5` | Anthropic |
| cheap | `claude-haiku-4-5-20251001` | Anthropic |
| local | `qwen3.6:35b-mlx` (also runs `gemma4:31b-mlx`, `gemma4:latest`, `gpt-oss:20b`) | any OpenAI-compatible endpoint |

Any OpenAI-compatible endpoint works with no code change: vLLM, Ollama, llama.cpp, Together, OpenRouter, Fireworks, DeepSeek, Mistral, xAI, and others. Swapping a provider is a `model_id` and `base_url` edit.

## Built with

Development provenance, distinct from the runtime table above: these models built, reviewed, and fact-checked Harnessie during construction rather than running under it, so they are not each backed by a single decision record. The trail is in the git history, [source-verification.json](https://github.com/snapsynapse/harnessie/blob/main/source-verification.json), and the session handoffs.

- Claude Fable 5 (Anthropic): the primary implementation and review model across the 0.1 to 0.4 line, and the frontier orchestrator in config.
- Claude Opus 4.8 (Anthropic): also a recorded significant development co-author in the git history.
- Claude Sonnet 5 (Anthropic): was used for several smaller cleanup tasks, especially those leveraging pre-existing skills.
- GPT-5.5 (OpenAI, via Codex): the secondary implementation and review model, cycling and verifying independently in alternating sessions.
- Gemini 3.5 Flash (Google): reviewed the 0.4.0 patch, verified the trust-bundle manifest and [live scorecard](https://github.com/snapsynapse/harnessie/blob/main/harness/live_scorecard.py) skip policies, and ran the live scorecard against a local OpenAI-compatible endpoint.
- Perplexity Sonar Pro (Perplexity): research and independent source verification at the outset; the trail is [source-verification.json](https://github.com/snapsynapse/harnessie/blob/main/source-verification.json), where twenty prior-art sources were checked and several confirmed via sonar-pro.

Four providers building, reviewing, and fact-checking the harness itself is the thesis applied to its own construction.

## Coverage we would like to add

The claim gets stronger as it spans more of the capability curve and more independent providers. The proven table already covers a frontier closed model (`claude-fable-5`) plus three ~20-35B local open-weights families (Qwen, Google, OpenAI). The gaps below are the honest missing coverage, each closable by running the named model through a contested phase so it earns a record. Model names are Ollama pull identifiers as of the 2026-07-06 library scan; verify tags at pull time, and note that any tag reading `cloud` runs on Ollama Cloud rather than fully on-box.

More of the capability curve:

- The small-model floor, where structured tool-calling breaks first and the harness's tool contract is under the most stress. Everything proven so far is 20B or larger; nothing below that has been run. Strong candidates: `granite4.1` (3B, 8B, 30B; IBM, tuned for disciplined function-calling), `functiongemma` (270M; a sub-1B model whose entire job is function-calling), `nemotron-3-nano` (4B; tools + thinking), or `phi4-mini` (3.8B; tools). If the registry's contract survives a 270M brain, it survives anything.
- A coding-specialist worker, directly relevant to the harnessie-worker role. Candidates: `qwen3-coder` (30B; tools) or `devstral` (24B; Mistral's agentic code-editing model, built for exactly this job).

More independent providers:

- A frontier closed model from another provider with a runtime receipt. GPT-5.5 already built the harness (see Built with) but has not yet run under it; a frontier non-Anthropic brain producing an arbitrated position (a GPT-5-class model, Google Gemini, or Grok) would put a second frontier provider in the proven table, not only in the build.
- Meta Llama (open weights): the most widely deployed open family, currently unrepresented. Candidates: `llama3.3` (70B; tools) or `llama3.1` (8B/70B; tools).
- Mistral: a European provider adding architectural and geographic diversity. Candidates: `magistral` (24B; tools + thinking) or `mistral-small3.2` (24B; vision + tools).
- DeepSeek: a distinct strong-reasoning provider, already namechecked in the config comments. Candidates: `deepseek-r1` (7B-70B local; tools + thinking) or `deepseek-v3.2` (cloud).

## How a brain becomes "proven"

Run it in a contested-decision workflow so it forms an independent position:

```bash
python3 -m harness.cli run workflows/contested-decision.yaml --goal "<a real decision>"
```

Route one of the `positions` at a tier pointed at the new model. When the panel resolves, the model and provider are written verbatim into `runs/<id>/decisions/DR-<phase>.md`. Promote that record into `decisions/` and add a row above. Configured is a claim; proven is a record.
