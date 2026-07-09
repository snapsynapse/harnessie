# Harnessie user guide

The complete guide to running, configuring, and extending Harnessie. If you are new, read [Getting started](getting-started.md) first; it gets you to a green run in five minutes. This guide is the reference behind it.

## Contents

- [What Harnessie is](#what-harnessie-is)
- [Core concepts](#core-concepts)
- [Installation and requirements](#installation-and-requirements)
- [The CLI](#the-cli)
- [What governs a run](#what-governs-a-run)
- [Writing a workflow](#writing-a-workflow)
- [Configuring brains](#configuring-brains)
- [Cascade routing and the sovereign tier](#cascade-routing-and-the-sovereign-tier)
- [The containment boundary](#the-containment-boundary)
- [Ownership lanes](#ownership-lanes)
- [Governance: consent, contests, and arbitration](#governance-consent-contests-and-arbitration)
- [When a run halts](#when-a-run-halts)
- [Security model](#security-model)
- [Extending the harness](#extending-the-harness)
- [Evaluation](#evaluation)
- [FAQ](#faq)

## What Harnessie is

Harnessie is a brain-agnostic multi-agent harness for getting reliable work out of language models. A goal enters. An orchestrator (a capable model at high effort) decomposes it into task packets with acceptance criteria and out-of-scope fences. Workers (cheaper models) execute those packets inside a jailed workspace with allowlisted tools, owning the files they create. Every worker phase exits through a gate that runs deterministic checks first, then an independent fresh-context verifier that never sees the worker's reasoning and fails closed. Contested decisions fan out to an adversarial panel whose positions and objections land in a decision record only a human may arbitrate. Everything is journaled, budgeted, resumable, and hash-chain audited.

The operating thesis: the harness structure carries the quality floor, the model carries the ceiling. The gates, jails, budgets, ownership rules, and retry ladders keep output honest no matter which model you run underneath them. That is what "brain-agnostic" means here, and it is a testable claim, not a slogan: a model earns its place in a tier by passing a scorecard.

## Core concepts

Roles. There are three role kinds. The orchestrator decomposes and integrates. Workers execute task packets and own their files. Verifiers judge a phase's output in fresh context and can only fail it closed. Each role is a prompt file in `agents/` plus machine-owned boundary text the harness appends so no prompt can opt out of policy.

Phases. A workflow is an ordered list of phases. Each phase runs one role against one task and, for worker phases, exits through a gate. Prior phases' reports are available to later phases through `{phase_name}` placeholders in the task template.

Task packets and consent. A task packet is an offer, not a command. Before any side-effecting tool unlocks, a worker must call `accept_task`, or it can `decline_task` with a reason and an optional counter-proposal. Declining is a first-class, non-punished outcome.

Gates. A gate runs the phase's deterministic checks (shell commands that must exit 0), then an independent verifier in fresh context. The verifier never sees the worker's reasoning, only the task and the artifacts. If either fails, the phase does not pass.

Routing and budget. Task classes map to model tiers and effort levels in config. The orchestrator does not pick its own model; routing is config, not model self-assessment. A run has a token and dollar budget; hitting it stops the run cleanly.

Memory. Project memory is a set of dated, provenance-stamped facts under `memory/`, maintained under approval gates. Nothing is deleted; expired facts move to an archive.

Audit. Every run writes a hash-chained event log. `harnessie audit` re-verifies the chain and renders one composite timeline of agent and operator actions.

## Installation and requirements

Python 3.11 or newer and PyYAML. Install from PyPI:

```bash
pip install harnessie   # or: pipx install harnessie / uv tool install harnessie
                        # or: brew install snapsynapse/tap/harnessie
```

Developing on the harness itself (or wanting the test suite), install from source:

```bash
git clone https://github.com/snapsynapse/harnessie.git
cd harnessie
pip install -e ".[dev]"
```

The model adapters are standard-library only and need no vendor SDK. Shell-using workflows require an OS sandbox: macOS uses native `sandbox-exec` (Seatbelt); Linux uses bubblewrap, firejail, or docker in that order of preference. Every backend is admitted only after a startup smoke test proves it can confine on your host. On any platform with no usable backend (Windows, or a host where the smoke test fails), shell-using workflows fail closed rather than run unconfined. See [Security model](#security-model).

## The CLI

All commands are subcommands of `python3 -m harness.cli` (or `harnessie` once installed). The `--root` flag sets the project root; it defaults to the current directory.

| Command | What it does |
|---|---|
| `run <workflow> --goal "..."` | Run a workflow from a goal. Prints a pre-run cost preview first (LIVE vs MOCK, ceilings, worst case) and refuses a live run with no budget ceiling; ends with a plain-language summary and the run id. |
| `resume <run_id> <workflow> --goal "..."` | Resume a run from its journal. Re-runs only phases that did not pass. |
| `report <run_id>` | Plain-language run summary: outcome, per-phase status, and on a halt the one named next action. `--raw` appends the raw journal, events, and proof listing. |
| `audit <run_id>` | Verify the hash chain and render the governance timeline. Exit 0 clean, 1 broken chain, 2 run not found. |
| `eval [suite]` | Run the deterministic eval scorecards (optionally one suite YAML). |
| `eval --live` | Run opt-in live provider scorecards; skipped visibly unless `HARNESSIE_LIVE=1` and provider configuration are present. |
| `verify-manifest [manifest]` | Verify the trust-bundle manifest. Defaults to `docs/MANIFEST.yaml`. |
| `init [path]` | Scaffold a minimal project layout, then run the guided readiness check: Python version, sandbox backend detection, API-key guidance, and a zero-dollar mock run that must be green. `--no-verify` skips the guided check for scripted scaffolding. |

## What governs a run

A run's behavior is not in one file. Each decision has exactly one owner. To predict or change what a run does, edit the owner, not the prompt.

| Decision | Governed by |
|---|---|
| Which model runs each task class, and how to swap brains | `config/models.yaml` (tiers, fallbacks, routing table) |
| Token and dollar ceilings, effort per task class | `config/models.yaml` (budget plus routing) |
| Containment-aware escalation policy and reserved work classes | `config/cascade.yaml` (opt-in per phase) |
| PII stripping, secret egress halting, rehydration grants | `config/boundary.yaml` (off by default) |
| Which phases run, in what order, with which gates and verifiers | the workflow YAML in `workflows/` |
| Which files each agent may write | `OWNERSHIP.yaml` (lanes plus first-writer claims) |
| What each role may do (tools, shell allowlist, approval) | the tool registry (`harness/tools/builtin.py`) plus role prompts in `agents/` |

## Writing a workflow

A workflow is a YAML file with a name, a description, and an ordered list of phases. Here is the built-in `build-and-verify` workflow, annotated.

```yaml
name: build-and-verify
description: Plan a code change, implement it, and gate it on tests plus a verifier.
phases:
  - name: plan
    agent: orchestrator
    task_class: plan          # -> routes to the frontier tier at high effort
    max_steps: 15
    task: |
      Goal from operator: {goal}
      Produce an implementation plan: subtasks with acceptance criteria,
      inputs, and out-of-scope fences. Inspect first; do not write files.
  - name: implement
    agent: implementer
    task_class: implement
    max_steps: 40
    task: |
      Implement the following plan in the workspace:
      {plan}
    verify:
      max_attempts: 3
      checks:
        - name: tests
          command: pytest -q      # deterministic gate: must exit 0
      verifier: code-verifier     # independent, fresh-context judge
      task_class: verify
      criteria: |
        Every criterion in the plan is met. Tests are meaningful and pass.
        Nothing outside the plan's scope was modified.
  - name: integrate
    agent: orchestrator
    task_class: integrate
    task: |
      Original goal: {goal}
      The implement phase finished with: {implement}
      Write the final operator summary with evidence and follow-ups.
```

Phase fields:

- `name`: the phase id, and the placeholder later phases use to read its report.
- `agent`: the role to run. `orchestrator`, or a worker or verifier defined under `agents/`.
- `task_class`: the routing key. Looked up in `config/models.yaml` to pick tier and effort.
- `task`: the task template. `{goal}` is the operator's goal; `{phase_name}` is a prior phase's report.
- `max_steps`: the loop's step ceiling for this phase.
- `verify`: the gate (worker phases). `checks` are shell commands that must exit 0; `verifier` names an independent judge in `agents/verifiers/`; `max_attempts` bounds the reformulate-and-retry loop; `criteria` is what the verifier judges against.
- `deny_tools`: tools removed from this phase, narrowing the blast radius of untrusted content.
- `allow_network`: opt this phase's sandboxed shell into network access (off by default).
- `inject_memory_status`: prepend a deterministic memory-and-prior-run digest to the task.
- `approve_tools`: operator-recorded pre-approval for approval-gated tools, scoped to this phase.
- `parallel`: phases with the same label and placed consecutively run concurrently in separate workspaces under `workspace/.phases/<phase>`.

Prior-phase reports are treated as untrusted model output: before substitution they pass through the same quarantine filter that scans tool results, so injection attempts inside a report are fenced as data rather than followed. The operator's `goal` is never fenced.

Adversarial phases. A phase with `mode: adversarial` runs a panel instead of a single worker. Each `positions` entry is an agent on a task class (choose different task classes to get genuinely different brains, which is what earns the record its independent-positions claim). After `rebuttal_rounds` of objections, `arbitration: convergence` passes only on unanimous agreement with zero open objections; anything else halts as `needs_arbitration` with a decision record. See [Governance](#governance-consent-contests-and-arbitration).

Approval policy. Approval-gated tools deny closed unless authorized. A workflow may use `approve_tools` for phase-local recorded pre-approval, or an operator can pass `--approval-policy approvals.yaml` with `allow` and `deny` lists. Each rule names a `tool` and may name a `phase`; explicit deny wins. `--approve-interactive` prompts on a TTY when no policy rule matches.

Verification options. Start with the offline deterministic path: `pytest`, `harnessie eval`, and `harnessie verify-manifest`. When a local OpenAI-compatible endpoint such as Ollama is already running, `HARNESSIE_LIVE=1 HARNESSIE_OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1 harnessie eval --live` gives a live-local scorecard without external provider calls. External provider scorecards are attended operations. CLI fan-out, local model review, or a separate model-family review can strengthen a change, but it is review evidence; the merge proof remains the repo's tests, evals, manifests, and audit records.

## Configuring brains

`config/models.yaml` is the only file you edit to swap models. It has three sections.

Tiers name model endpoints, ordered cheap to capable (`local`, `cheap`, `mid`, `frontier`). Each tier declares a provider, a model id, the environment variable holding its key (never the key itself), token limits, whether it supports an effort dial, and cost-per-million-token rates for budgeting.

```yaml
tiers:
  frontier:
    provider: anthropic
    model_id: claude-fable-5
    api_key_env: ANTHROPIC_API_KEY
    supports_effort: true
  local:
    provider: openai-compat
    model_id: qwen3.6:35b-mlx
    base_url: http://localhost:11434/v1
    api_key_env: ""          # local endpoints usually need no key
```

Routing maps each task class to a tier and effort. Workflow phases declare a `task_class`; the router resolves it here. This keeps model choice a policy decision, not something a model asserts about itself.

```yaml
routing:
  plan:      { tier: frontier, effort: high }
  implement: { tier: mid,      effort: medium }
  verify:    { tier: mid,      effort: high }
  default:   { tier: mid,      effort: medium }
```

Budget sets the run-wide ceilings:

```yaml
budget:
  max_usd: 10.0
  max_tokens: 2000000
```

To run everything on a local open-source model, point the task classes you use at the `local` tier and leave `ANTHROPIC_API_KEY` unset. To swap one provider for another, change the tier's `provider`, `model_id`, and `base_url`. Nothing else in the harness changes.

The escalation ladder walks the tier order. When a phase fails its gate, the harness first reformulates the task with the verifier's evidence, then raises effort, then raises tier, before halting for a human. That ladder is why a cheap worker can carry bulk execution safely: a capable verifier and an automatic escalation stand behind it.

## Cascade routing and the sovereign tier

The default ladder above is the whole story unless a phase opts in to a cascade policy. Cascade policies (introduced in 0.7) are declared, containment-aware routing: instead of a fixed `task_class`, a phase names a policy in `config/cascade.yaml` that decides how it climbs. Phases that do not opt in route exactly as before, byte for byte, so this is additive.

A policy declares a tier ladder, which failure reasons climb it, a maximum climb, and what happens when the ladder is exhausted:

```yaml
# config/cascade.yaml
policies:
  cheap-first:
    ladder: [local, mid, frontier]
    escalate_on: [gate_fail, schema_fail]   # what climbs the ladder
    max_climb: 2
    on_exhaust: defer                        # reduce_scope | defer, never silent
  contained-local:
    ladder: [local, sovereign]               # unexposed tiers only
    data_classes: [freeform_sensitive]
    contained: true                          # may never name an exposed tier
reserved:
  - arbitration                              # never reaches any model, at any tier
```

A phase opts in with `cascade: cheap-first` instead of `task_class:`. Three behaviors are worth understanding:

- Sideways before up. A provider refusal or an availability failure (rate limit, overload, error) moves to the tier's next configured `fallbacks:` entry — the same tier, a different provider — never upward. Up-tiering on a refusal would move a contained task onto a more exposed brain, so the harness refuses to. Configure fallbacks under a tier in `config/models.yaml`:

  ```yaml
  tiers:
    mid:
      provider: anthropic
      model_id: claude-sonnet-5
      fallbacks:
        - model_id: some-alternate            # inherits mid's other fields
        - model_id: another
          base_url: https://other-provider/v1
  ```

- Escalation headroom. A climb the policy would allow is refused before dispatch if the remaining budget cannot cover the target tier's worst-case first turn. An escalation can never be the thing that busts your ceiling; when headroom runs out the phase hands to you instead.

- Contained ladders and the sovereign tier. A policy marked `contained: true` may only name unexposed tiers (`local` and `sovereign`). The `sovereign` tier is a fifth slot for any OpenAI-compatible controlled endpoint you operate — self-hosted vLLM, a TEE-hosted deployment, a private cluster — declared like any tier in `config/models.yaml`. It is deliberately off the default escalation walk: nothing auto-escalates into or past a controlled endpoint. Reach it only by naming it in a routing row or a cascade ladder. Work classes listed under `reserved:` never reach any model at all and halt with a named operator action; `arbitration` ships reserved by default.

Every attempt writes a `routing_trace` event (tier, effort, fallback index, model, provider, outcome), so `harnessie audit` shows exactly where each phase ran and why it moved.

## The containment boundary

The containment boundary (0.7) keeps sensitive data from leaving the harness. It is off by default; enable it in `config/boundary.yaml`:

```yaml
# config/boundary.yaml
enabled: true
include_contextual: false        # keyword-anchored kinds (routing #, DOB, bank acct)
rehydration_grants: config/rehydration-grants.yaml
```

With it on, the harness makes a specific, bounded claim — a per-data-class coverage table, not "we catch everything":

- Structured PII (emails, phone numbers, SSNs, and a multilingual set of national IDs) is stripped to stable placeholders like `[EMAIL_1]` before any content reaches a model — at the goal, at every phase task, and at every tool result. The model only ever sees placeholders, and no run artifact (events, journal, reports, workspace) carries a raw value. The filter is regex over text with no model in its path, so it cannot be talked into leaking.
- Secrets (credential-shaped strings) are stricter: they are never placed in the map and never rehydrated, and a secret reaching an egress payload halts the run immediately (`secret_egress`), reporting the kind label only, never the value. There is no warn mode.
- Unstructured free-text PII is explicitly not caught by the filter — a regex cannot reliably find a sensitive fact written in prose. This is covered instead by contained routing: give the phase a `contained: true` cascade policy and a data class, and the task never egresses past your `local`/`sovereign` tiers. The two halves cover each other: the filter handles what patterns catch, routing handles what they cannot.

The placeholder map (placeholder to original value) is the one place real values live, and it is written outside the run tree, at `.boundary/<run_id>.json` with owner-only permissions. Rehydration — turning placeholders back into values — happens only at the operator boundary, and only for tools you explicitly grant in `rehydration_grants` (the same allow/deny grammar as approval policy, deny-all by default). On resume the map reloads; if it is missing or corrupt, rehydration is disabled fail-closed and the run tells you, rather than guessing.

The boundary was adapted with provenance from PAICE.work PBC production PII code, released under Apache-2.0 (see [NOTICE](../NOTICE)), and adopted through Harnessie's own contested-decision process (`decisions/AIDR-0003` and `AIDR-0004`).

## Ownership lanes

`OWNERSHIP.yaml` at the project root declares who may write what. It sits outside the workspace jail and no agent can reach it. Three lane kinds:

- Operator lanes are locked to every agent. No agent may write a path in an operator lane, full stop.
- Agent lanes assign glob patterns to a named agent. Only that agent may write matching paths; another agent's write is refused with a `request_change` remedy.
- Collaborative lanes are shared: any agent may write matching paths, and no one exclusively claims them.

Paths not covered by any lane use first-writer-owns: the first agent to write a file claims it, and later cross-agent writes are refused. Claims and denials are logged as events and show up in the audit timeline. An agent that needs a file it does not own calls `request_change` to record the need rather than overwriting.

## Governance: consent, contests, and arbitration

Harnessie treats agent work as governed, not merely executed. Three mechanisms carry that.

Consent. A task packet is an offer. Before side-effecting tools unlock, the worker calls `accept_task`, or `decline_task` with a reason and an optional counter-proposal. A decline ends the phase cleanly and is never punished with a bigger model; escalation is for capability failures, not disagreement. A side-effecting call before acceptance is refused at dispatch with a structured refusal the model can read.

Contested decisions. Some questions are decisions, not artifacts. An adversarial phase runs two or more agents on different brains, each forming an independent position from the workspace evidence, then objecting to each other's. If they converge (unanimous recommendation, zero open objections) the phase passes. Otherwise it halts as `needs_arbitration` and writes an AIDR-style decision record to `runs/<id>/decisions/DR-<phase>.md` capturing each position, the objections, and the dissent.

Arbitration. Only a human arbitrates a contested decision. You open the decision record, write your arbitration into it, and re-run; the run resumes from that record rather than re-running the contest (which would overwrite the recorded dissent). The record carries structurally earned claims: for example, `independent-positions` is earned only when the positions genuinely came from different providers.

Everything above emits events into the hash-chained log. `harnessie audit <run_id>` renders them as one timeline: consents granted and declined, ownership claims and denials, structured refusals, change requests, injection flags, gate verdicts, approval grants and denials, operator arbitration, memory facts saved and expired, and decision records with their earned claims. See [GOVERNANCE.md](../GOVERNANCE.md) for the full model.

## When a run halts

Every run ends in a named stop condition, and each maps to one operator action. Resuming is `harnessie resume <run_id> <workflow> --goal ...`; resume re-runs only phases that did not pass, so fixing the cause and re-running is safe.

| Stop condition | What it means | What to do |
|---|---|---|
| `complete` / phase `passed` | task done, gate satisfied | nothing; the next phase proceeds |
| `declined` | the worker declined the offered task packet | read the counter-proposal in the report; revise the packet or accept the objection, then re-run |
| `needs_human` | a gate's checks or verifier failed after the retry ladder exhausted | read the proofs under `runs/<id>/proofs/` and the report; fix the task or the acceptance criteria; re-run |
| `needs_arbitration` | a contested phase produced dissent | open `runs/<id>/decisions/DR-<phase>.md`, record your decision, then re-run (resume keys on that record) |
| `stuck` | the model repeated an identical failing or refused call | inspect the refusal via `harnessie audit <id>`; fix the tool grant, allowlist, or task; re-run |
| `budget` | the run hit its token or dollar ceiling | raise the ceiling in `config/models.yaml` or narrow the goal; re-run |
| `max_steps` | the loop hit its step ceiling without completing | raise `max_steps` for the phase or simplify the task |
| `model_error` | the provider errored twice in a row | check the endpoint and API key; re-run |
| `no_action` | the model produced no tool call even after a nudge | usually a role-prompt or model-fit issue; check the role prompt in `agents/` |
| `secret_egress` | the containment boundary caught a secret in an egress payload (the goal or a tool result) | remove the credential from the input or source it from an environment variable; the boundary reports the kind, never the value; re-run |

## Security model

Harnessie's guarantees live in code at the tool and registry layer, so no role prompt can opt out of them. The layers, in brief:

- Role permissions. The registry enforces which role may call which tool at dispatch time. A model never sees a tool its role cannot use, and a disallowed call is refused, not executed.
- Consent lock. Side-effecting tools stay locked until the worker accepts the task.
- Workspace jail. File tools resolve and confine paths to the workspace subtree; a path escape is refused.
- OS sandbox. Every child command (shell and gate checks) runs in an OS confinement that denies writes outside the workspace and denies network by default. macOS uses Seatbelt; Linux uses bubblewrap, firejail, or docker. No usable backend means shell fails closed.
- Quarantine. Tool results and inter-phase reports are scanned for injection patterns and invisible or bidirectional characters; flagged content is stripped of invisibles and fenced as data-not-instructions before a model sees it.
- Secret handling. Child processes run under a scrubbed environment, so provider keys are never inherited. Shell output is redacted for credential-shaped strings, and writing credential-shaped content into the workspace is refused. Secret detection reports kind labels, never the value.
- Containment boundary (opt-in). When enabled in `config/boundary.yaml`, structured PII is stripped to placeholders before any egress and a secret in an egress payload halts the run; unstructured sensitive data is kept on your controlled tiers by contained routing. See [The containment boundary](#the-containment-boundary).
- Structured refusals. Every denial returns a machine-readable refusal (`error`, `boundary`, `detail`, `why`) and emits an audit event, so refusals are actionable data for the model and legible entries for the operator.

The full threat model, the honest limits of each layer, and the per-platform backend table are in [SECURITY.md](../SECURITY.md).

## Extending the harness

Adding a tool. Tools are registered with a name, a JSON-schema signature, an effects class (`read`, `write`, or `execute`), the roles allowed to call it, and whether it requires approval. Registration is in `harness/tools/builtin.py`. The effects class and role grant are enforced at dispatch, so a new tool cannot bypass policy. The built-in grants are a useful template:

| Tool | Roles | Effects |
|---|---|---|
| `read_file`, `list_files`, `task_complete` | orchestrator, worker, verifier | read |
| `run_shell` | worker, verifier | execute |
| `write_file`, `accept_task`, `decline_task`, `save_fact`, `expire_fact`, `request_change` | worker | write or read |

Adding a role. A role is a markdown prompt file plus its kind. Orchestrators live at `agents/orchestrator.md`, workers under `agents/workers/<name>.md`, verifiers under `agents/verifiers/<name>.md`. The harness appends machine-owned boundary text per kind, so the prompt file defines the role's job while policy stays in the harness. Reference the role by file name as a phase's `agent`.

Adding a workflow. Write a new YAML file under `workflows/` following the schema in [Writing a workflow](#writing-a-workflow). Nothing about the harness needs to change; workflows are declared, not coded.

## Evaluation

Harnessie ships deterministic eval scorecards that run against a mock brain with no network, so behavior is reproducible. `harnessie eval` runs the default suites; pass a suite YAML to run one. Scenarios come in three shapes: golden cases that must pass, risky cases that must fail closed, and recovery cases that must route through the declared ladder. The governance suite scores consent, ownership, contest, and audit behavior specifically, so those guarantees are measured rather than assumed. `harnessie eval --live` is the separate, operator-opted-in provider scorecard; it skips visibly without `HARNESSIE_LIVE=1` and provider configuration. See [EVALS.md](../EVALS.md) for the scenario schema and how to add cases.

## FAQ

Do I need an API key to try it? No. The test suite and `harnessie eval` run against a mock brain offline. You only need a key (or a local endpoint) to run a real workflow.

Can I run it fully offline on open-source models? Yes. Point the task classes you use at the `local` tier in `config/models.yaml` and use any OpenAI-compatible server (Ollama, vLLM, llama.cpp). Leave the key env unset.

Does it run on Linux? Yes, with a sandbox backend present (bubblewrap preferred, then firejail, then docker). Without a usable backend, shell-using workflows fail closed by design. Windows should use WSL2, which presents as Linux.

What happens if a worker goes off the rails? The gate is the backstop: deterministic checks plus an independent verifier that fails closed, then an automatic reformulate-effort-tier ladder, then a human halt. Ownership lanes and the sandbox bound what a single worker can touch in the meantime.

Where is my run's data? Under `runs/<run_id>/`: `journal.jsonl` (the resume ledger), `events.jsonl` (the hash-chained audit log), `proofs/` (check outputs), and `decisions/` (contested-phase records). This directory is gitignored.

How do I make an agent stop overwriting another agent's files? Declare lanes in `OWNERSHIP.yaml`, or rely on first-writer-owns. Cross-agent writes are refused with a `request_change` remedy.

## See also

- [Getting started](getting-started.md): the five-minute path.
- [ARCHITECTURE.md](../ARCHITECTURE.md): the design rationale and source-to-decision map.
- [GOVERNANCE.md](../GOVERNANCE.md): consent, ownership, contests, and audit in full.
- [SECURITY.md](../SECURITY.md): the threat model and sandbox backends.
- [ROADMAP.md](../ROADMAP.md): what is next and platform support.
