# Terminal agent sessions

This is the operator recipe for terminal sessions in the Harnessie checkout. It covers interactive coding agents, direct Ollama conversation, and a separately configured governed Harnessie workflow.

Validation status: the operator reported opening all four terminal sessions and the four review reports are saved under `audits/`. CLI argument syntax was checked against installed help. Authentication, resume selection, and window automation have not received systematic end-to-end testing. These separate sessions have no automatic shared mailbox or enforced cross-runtime ownership lanes.

## Start in the current terminal

Use one command below. Each command fixes the working root at this repository and keeps approvals enabled. The Codex, Claude, and Antigravity commands also load `SESSION_OPENING_PROMPT.txt` as the first interactive turn. The agent should process that prompt before receiving the specific session goal.

### Codex

Literal
```bash
codex -C /Users/snap/Git/harnessie --sandbox workspace-write --ask-for-approval on-request "$(< /Users/snap/Git/harnessie/SESSION_OPENING_PROMPT.txt)"
```

To continue the latest Codex terminal session rooted here:

Literal
```bash
cd /Users/snap/Git/harnessie && codex resume --last
```

### Claude Code

Literal
```bash
cd /Users/snap/Git/harnessie && claude --permission-mode manual --name harnessie-next "$(< /Users/snap/Git/harnessie/SESSION_OPENING_PROMPT.txt)"
```

To continue the latest Claude session in this checkout:

Literal
```bash
cd /Users/snap/Git/harnessie && claude --continue
```

### Google Antigravity CLI

Literal
```bash
cd /Users/snap/Git/harnessie && agy --sandbox --prompt-interactive "$(< /Users/snap/Git/harnessie/SESSION_OPENING_PROMPT.txt)"
```

To continue the latest Antigravity conversation:

Literal
```bash
cd /Users/snap/Git/harnessie && agy --sandbox --continue
```

If `agy` is not installed, install the supported Antigravity CLI from Google's official installer, then open a new shell so the updated path takes effect:

Literal
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

Do not substitute the retired Gemini CLI for this surface.

### Ollama directly

Ollama can be used directly without Codex. There are two distinct direct paths.

#### Direct model conversation

Use `ollama run` for an interactive conversation with one model. This surface does not give the model Harnessie's workflow, repository tools, ownership controls, verification gates, or audit trail.

The current general-purpose local models are:

Qwen 3.8, the newest installed local Qwen generalist:

Literal
```bash
ollama run qwen3.8:latest
```

Gemma 4 31B MLX, the newest installed local Gemma generalist:

Literal
```bash
ollama run gemma4:31b-mlx
```

GPT-OSS 20B, the installed local OpenAI open-weight generalist:

Literal
```bash
ollama run gpt-oss:20b
```

No general-purpose local DeepSeek model is currently installed. `deepseek-ocr:latest` is an OCR model and should not be substituted for a coding or reasoning session.

The current general-purpose `:cloud` routes are external provider calls mediated by Ollama. They are not local or offline. Treat prompts, repository content, usage, availability, and possible charges according to the serving provider's current terms.

Qwen coding route:

Literal
```bash
ollama run qwen3-coder:480b-cloud
```

DeepSeek routes, newest first:

Literal
```bash
ollama run deepseek-v4-pro:cloud
```

Literal
```bash
ollama run deepseek-v3.2:cloud
```

GPT-OSS 120B cloud route:

Literal
```bash
ollama run gpt-oss:120b-cloud
```

Other current equivalent cloud generalists:

Literal
```bash
ollama run glm-5.2:cloud
```

Literal
```bash
ollama run minimax-m3:cloud
```

Literal
```bash
ollama run kimi-k2.5:cloud
```

Older installed cloud tags remain available for reproducibility, but new sessions should normally start with the newest installed tag in the same family. Guardian, embedding, OCR, and image-generation models are specialized models, not substitutes for a general coding session.

#### Harnessie directly through Ollama

Harnessie connects to Ollama's OpenAI-compatible endpoint without Codex. For local inference, set `tiers.local.model_id` to a genuinely local tag such as `qwen3.8:latest`, `gemma4:31b-mlx`, or `gpt-oss:20b` and retain the following fields. This is a YAML fragment for that tier, not a shell command:

Literal
```yaml
provider: openai-compat
base_url: http://localhost:11434/v1
api_key_env: ""
```

Set `supports_effort` to the selected model's actual capability. Keep it `false` unless that tag is known to accept the effort parameter. For a fully Ollama-backed workflow, route every task class used by that workflow to the `local` tier. Changing `tiers.local.model_id` alone affects only phases already routed to `local`; the shipped routing currently sends `mechanical` there.

Never put a cloud model tag in `local` or `sovereign`: Harnessie currently classifies containment by tier name. A localhost Ollama endpoint can relay externally. Cloud-backed Harnessie experiments need an exposed tier, reviewed routing and fallback configuration, and honest cost accounting; the direct cloud chat commands above do not configure this automatically.

Configuration changes invalidate this checkout's `INWARD_MANIFEST.yaml`, whose divergence policy is `refuse`. Before a governed run, review the intended configuration diff and regenerate its manifest using the repository's `harness.inward_manifest.render_inward_manifest` helper in an explicit configuration-maintenance step. Inspect that manifest diff and verify it. Do not delete the manifest or relax its refusal policy to get a run started. This guide does not modify the current configuration or its pins.

Use the repository virtual environment and source module to exercise this branch, rather than the independently installed Homebrew executable. Confirm that this interpreter exists and resolves the local package, then validate the prepared configuration:

Literal
```bash
cd /Users/snap/Git/harnessie && .venv/bin/python3 -c 'import harness; print(harness.__file__)'
.venv/bin/python3 -m harness.cli validate
.venv/bin/python3 -m harness.cli verify-inward-manifest
```

Only proceed when the package path is this checkout and both checks pass. Review budgets and provider exposure before starting: the runtime prints a cost preview but that printout is not an interactive approval gate.

Replace: GOAL -> the exact outcome for this Harnessie session

Customize
```bash
cd /Users/snap/Git/harnessie && .venv/bin/python3 -m harness.cli run workflows/build-and-verify.yaml --goal "GOAL"
```

The direct Harnessie path supplies the workflow, tools, sandbox, verification, budgets, stop conditions, and audit record. Ollama supplies the configured model endpoint.

### Ollama through Codex, optional

This optional path uses Codex as the outer coding-agent harness and Ollama as its model provider. It is useful when Codex's interactive repository tooling is desired. It is not required for direct Ollama chat or direct Harnessie-to-Ollama workflows. Ollama must already be running and the model must already be present locally. The command supplies the same initial session-opening prompt as hosted Codex.

Replace: MODEL -> an exact model name from `ollama list`, such as a locally installed Qwen, Gemma, or GPT-OSS tag

Customize
```bash
codex -C /Users/snap/Git/harnessie --oss --local-provider ollama --model MODEL --sandbox workspace-write --ask-for-approval on-request "$(< /Users/snap/Git/harnessie/SESSION_OPENING_PROMPT.txt)"
```

Use a genuinely local tag when local-only execution is required. Passing a `:cloud` tag makes an external call even though the request is launched through the local Ollama client.

## Open a separate macOS Terminal window or tab

The simplest terminal-only split is to run one of the commands above in the current shell after opening a new Terminal window or tab with the shell commands below. These commands target Apple's Terminal.app. They do not apply to iTerm2, Warp, Ghostty, or the terminal panel inside the Codex app.

Open Terminal at the Harnessie checkout (window behavior depends on Terminal preferences):

Literal
```bash
open -a Terminal /Users/snap/Git/harnessie
```

For an explicit new tab, use Terminal's Shell > New Tab or Command-T, then run the selected launch command. The previous AppleScript recipe was not verified to create a tab and has been removed.

Then run exactly one agent command from the preceding section in that window or tab. Keeping window creation separate from agent launch avoids shell-quoting the session prompt and makes the selected engine visible before it receives instructions.

## Session-opening prompt

`SESSION_OPENING_PROMPT.txt` is the canonical first turn for Codex, Claude, and Antigravity launches. Their commands above read and submit it automatically. This is the missing step between starting each CLI and giving it the specific session goal.

The prompt establishes the current branch authority and asks the agent to await a specific goal. Launching a selected model authorizes that session's inference; additional provider calls and publication remain separate actions. Direct Ollama chat has no repository-reading tools by default, so provide the actual task brief as text for that surface.

Literal
```bash
cat /Users/snap/Git/harnessie/SESSION_OPENING_PROMPT.txt
```

## Preflight after the agent opens

`NEXT.md` links the branch-specific preparation packet and owns the broader verification queue. For concurrent read-only reviews, nominate one session to run shared checks and share its results rather than launching identical suites four times. Use `.venv/bin/python3` for this checkout's Python checks. Live-provider scorecards remain explicit opt-in operations.

## Engine-wrapper boundary

`harnessie-engine-wrappers` is a separate, probe-gated containment surface. Its current wrapper narrowly denies reads from credential paths. It is not a generic launcher and may correctly prevent Codex, Claude, or Antigravity from reaching credentials they need. Do not insert it into these launch commands unless its local probe passes and the session has a deliberately configured engine credential path compatible with its policy.
