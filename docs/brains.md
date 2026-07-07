# Brains run under Harnessie

Brain-agnostic is a testable claim, not a slogan. This page is the receipt: the models that have actually produced work under the harness, each linked to the on-disk record that proves it, plus the set you can swap to by editing one file.

Scope: this tracks models run under the harness at runtime. It does not track the development tooling used to write Harnessie's own code (that collaboration spans models too, but it is not the claim being made here).

## Proven under the harness

Each of these formed an independent position in an adversarial contested phase, recorded verbatim with its model and provider in a hash-chained decision record. Different task classes route to different tiers, so a single contest draws genuinely different brains, which is what earns a record its `independent-positions` claim.

| Model | Provider | Role on record | Provenance |
|---|---|---|---|
| `claude-fable-5` | Anthropic | Frontier orchestrator; position author and record assembler | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `qwen3.6:35b-mlx` | Alibaba | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `gemma4:31b-mlx` | Google | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |
| `gpt-oss:20b` | OpenAI | Contested-phase participant (isolated local inference) | [AIDR-0001](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0001-adopt-v0-2-governance-layer.md), [AIDR-0002](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0002-v0-3-tenets-and-triage.md) |

Four providers, four model families, from a frontier closed model down to 20B-parameter local open-weights models, all producing arbitrated positions under the same harness. The decision the operator made in each case was a human's; every position is preserved, including the ones that did not win.

## Configured and swappable

Declared in [config/models.yaml](https://github.com/snapsynapse/harnessie/blob/main/config/models.yaml). Point any task class at any tier; the gates, jails, budgets, and audit stay identical. API keys come from environment variables, never the file.

| Tier | Model | Provider |
|---|---|---|
| frontier | `claude-fable-5` | Anthropic |
| mid | `claude-sonnet-5` | Anthropic |
| cheap | `claude-haiku-4-5-20251001` | Anthropic |
| local | `qwen3.6:35b-mlx` (also runs `gemma4:31b-mlx`, `gemma4:latest`, `gpt-oss:20b`) | any OpenAI-compatible endpoint |

Any OpenAI-compatible endpoint works with no code change: vLLM, Ollama, llama.cpp, Together, OpenRouter, Fireworks, DeepSeek, Mistral, xAI, and others. Swapping a provider is a `model_id` and `base_url` edit.

## Coverage we would like to add

The claim gets stronger as it spans more of the capability curve and more independent providers. Open gaps worth closing, each by running the model through a contested phase so it earns a record:

- A second frontier closed model from a different provider (Google Gemini, or a GPT-5-class or Grok model). Today the only frontier-tier proven brain is Anthropic; a frontier peer proves brain-agnostic at the top of the curve, not only that small local models can participate.
- Meta Llama (open weights): the most widely deployed open family, currently unrepresented.
- Mistral (Mistral Large or a Mixtral): a European provider, added architectural and geographic diversity.
- DeepSeek (V3 or R1): a distinct strong-reasoning provider, already namechecked in the config comments.

## How a brain becomes "proven"

Run it in a contested-decision workflow so it forms an independent position:

```bash
python3 -m harness.cli run workflows/contested-decision.yaml --goal "<a real decision>"
```

Route one of the `positions` at a tier pointed at the new model. When the panel resolves, the model and provider are written verbatim into `runs/<id>/decisions/DR-<phase>.md`. Promote that record into `decisions/` and add a row above. Configured is a claim; proven is a record.
