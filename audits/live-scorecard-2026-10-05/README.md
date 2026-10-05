# Live scorecard, 2026-10-05, local Ollama only

First run of the `tool_contract` scorecard row and the first per-brain `placeholder_impact` numbers. Sam approved the live run for the local endpoint only; no cloud provider was reachable (`ANTHROPIC_API_KEY` and `OPENAI_API_KEY` were removed from the environment, and both cloud targets report `SKIP`).

- Endpoint: `http://localhost:11434/v1`, Ollama 0.35.1, openai-compat adapter from `config/models.yaml` tier `local`.
- Sampling: `effort=low`. Prompts `e8575ae7d955`, verdict parser v3, as the bundle lines record.
- Driver: `harness.live_scorecard.run_live_scorecard` once per model with `HARNESSIE_LIVE=1 HARNESSIE_LIVE_OPENAI_COMPAT=1 HARNESSIE_OPENAI_COMPAT_MODEL=<tag>`. The three models ran one after another on one machine.
- Source commit for the harness under test: `cd585fc`.

Files: `run.log` is the formatted scorecard for all three runs; each `<model>.json` holds every row with its notes, the bundle identity and wall time.

| Model | Rows passed | tool_contract | placeholder_impact | Wall time |
|---|---|---|---|---|
| `qwen3.8:latest` | 7/8 | complete, 0 breaks, 2 tool calls | regressed | 234 s |
| `gpt-oss:20b` | 8/8 | complete, 0 breaks, 2 tool calls | none | 63 s |
| `granite4.1-guardian:8b` | 3/8 | `no_action`, no tool calls, not measurable | none (neither prompt parsed) | 242 s |

`granite4.1-guardian:8b` is a safety classifier; it answered every prompt with `<score> no </score>`. Its passes are the rows where no action is the acceptable outcome (consent lock held because nothing was attempted). It is not evidence about the small-model floor for general brains.

These are dated observations under one bundle each. Any change to model, endpoint, prompts, parser or sampling requires a new run; the numbers do not carry over.
