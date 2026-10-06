# Harbor agent acceptance, 2026-10-05

First real Harbor trials of `examples/harbor-agent/`: Harnessie as a Harbor external agent, running on the host, acting on the task sandbox through `BaseEnvironment`, driving a local open-weight model through OpenEnv's capture proxy. Three trials on Harbor's Docker backend. Evidence per trial is in `harbor-agent-acceptance-2026-10-05/` (ATIF trajectory, Harnessie result and event log, reward file, reconciliation against the proxy), with home-directory and temp paths scrubbed.

## Setup

- Harbor 0.24.0 and openenv 0.7.0 in the scratch `oe` virtualenv (Python 3.12.15). Harnessie from the working tree that became the 4b commit, 1.4.1 in metadata.
- Model: `qwen3.8:latest` (27.3B Q4_K_M) on local Ollama 0.35.1, reached only through `python -m openenv.core.harness.capture.server` on 127.0.0.1:8100. One capture session minted per trial and handed to the agent as `HARNESSIE_HARBOR_API_KEY`. Capture level `logprobs`, rollout type `eval` (Ollama returns no token ids).
- Backend: Harbor `docker` via Colima 0.10.3 (Docker Engine 29.5.2, Compose 5.5.1), jobs directory under `$HOME`.
- Invocation: `harbor run -a harnessie_harbor_agent:HarnessieAgent -m qwen3.8:latest -e docker`, with `PYTHONPATH` naming the example directory. OpenEnv 0.7.0's `openenv harbor rollout --harness module:Class` was not used: its seam table only resolves named harnesses and raises `KeyError` for an import path, despite the documentation. Reconciliation against the proxy's rollout was therefore done by hand, as for the ATIF export acceptance.

## Trials

| Trial | Task | Verifier | Harnessie stop | Steps | Proxy turns | Reward | Wall time |
|---|---|---|---|---|---|---|---|
| hello-world | Harbor's `hello-world` | Harbor's own `tests/test.sh` (pytest) | `complete` | 3 | 3 | 1.0 | 1 min 10 s |
| calc-add-mean (timeout) | `examples/harbor-verifier/tasks/calc-add-mean` | `HarnessieVerifier` | cancelled by Harbor after 300 s | 3 recorded before cancel | 3 | 1.0 | 5 min 12 s |
| calc-add-mean | same | `HarnessieVerifier` | `complete` | 9 | 9 | 1.0 | 3 min 10 s |

Both completed trials: ATIF `trajectory.json` accepted by Harbor's trajectory validator; agent step count equals the proxy's captured turn count, one root, no forks; `tool_contract_breaks` 0. Harbor's `AgentContext` received prompt and completion token totals (hello-world: 4,081 in, 177 out) and a metadata block with the stop condition and metrics.

The second calc trial is the one where Harnessie sat on both sides of a Harbor trial: `HarnessieAgent` produced the work in the sandbox and `HarnessieVerifier` graded it on the host. Its event log shows one policy refusal, `run_shell` of `cd ...` refused as `command_not_allowlisted`, after which the model used an allowlisted form and finished. That is a deliberate denial, not a vocabulary break, and the metric separated the two correctly.

## The timeout trial

Our task's `[agent] timeout_sec` was 300 s. The local 27B model needed longer than that for its fourth call, and Harbor cancelled the agent with `AgentTimeoutError`. Two things followed. First, the verifier still scored the sandbox 1.0, because `calc.py` had been written correctly on the second step; Harbor records the trial as errored with a reward, both true. Second, the first version of the agent had no cancellation path, so the loop thread was orphaned and no `trajectory.json` or result file was written. The agent now wraps the model in `CancellableModel`: on Harbor's cancel the next model call returns an error turn, the loop finishes through `loop_finished` with `model_error`, the log closes, and the result and trajectory are still written (the trajectory records the stop condition). The task's timeout is now 1,200 s, which is what a consumer-hardware model needs. The timed-out trial's event log and result are retained under `calc-add-mean-timeout/` as the evidence for that change.

## What the trials establish

- Harnessie can be a Harbor agent without changes to either project. Role grants, the shell allowlist, the argument jail and the refusal grammar applied unchanged; only where a call lands changed, which is the point.
- A Harbor trial of Harnessie yields the two records an external capture can be checked against: Harnessie's hash-chained `events.jsonl` and an ATIF trajectory derived from it. Call counts agreed with the proxy on both completed trials. Token-level agreement needs a token-returning engine (vLLM or SGLang), which Ollama is not.
- The harness identity (version, inward manifest digest, tool set digest) travels inside the trajectory's `agent.extra`, so a Harbor result names the harness that produced it. The tool set digest differs from the builtin registry's because the remote tool surface is its own: same policy, different `fn`, and the digest covers names, schemas, effects and grants, not implementations.

## Limits

- Two tasks, one backend, one local model. This is a contract and plumbing result, not evidence about any brain.
- Eval-level capture only; `n_trainable_tokens` is 0 on every rollout.
- The agent's confinement for tool effects is the Harbor environment. Harnessie's own OS sandbox is not engaged because nothing executes on the host; the host process still runs with the operator's authority, as any Harbor external agent does.
- `openenv harbor rollout` cannot currently load this agent by import path; the recorded trials used `harbor run` with the proxy started standalone.

## Reproduce

Literal
```bash
PYTHONPATH=examples/harbor-agent:examples/harbor-verifier HARNESSIE_HARBOR_BASE_URL=http://127.0.0.1:8100 HARNESSIE_HARBOR_API_KEY=<capture session id> harbor run -p examples/harbor-verifier/tasks -a harnessie_harbor_agent:HarnessieAgent -m qwen3.8:latest -e docker --verifier harnessie_verifier:HarnessieVerifier --verifier-kwarg python=.venv/bin/python -o runs/harbor-jobs
```

Dated observations under the versions above; a different Harbor, OpenEnv, backend, model or Harnessie version requires a new run.
