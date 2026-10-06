# Harnessie as a Harbor external agent

Harbor (https://harborframework.com/) runs agents against containerised tasks. It has two agent shapes: installed agents, which Harbor installs and runs inside the task container, and external agents, whose loop runs in the Harbor process and acts on the container through `BaseEnvironment`. Harnessie is the second kind here. The orchestration, the registry policy and the hash-chained audit log stay on the host; only allowlisted commands and file uploads cross into the sandbox.

Why not an installed agent: inside the task container Harnessie has no admitted OS sandbox backend and fails closed, the same open question as a Harnessie Docker image. Running host side sidesteps it, and the Harbor environment becomes the confinement for every tool effect.

## Layout

```
examples/harbor-agent/
  harbor_tools.py             SandboxBridge, path jail, and the remote read_file, list_files,
                              write_file, run_shell, task_complete tools; no Harbor import
  harnessie_harbor_agent.py   HarnessieAgent(BaseAgent): the thin wrapper Harbor loads
```

`harbor_tools.py` keeps the builtin worker policy unchanged: the same shell allowlist (`ls`, `cat`, `grep`, `python3`, `pytest`, `git`), the same argument jail, the same refusal grammar, the same role grants. What changes is where a call lands: `run_shell`, `read_file` and `list_files` go through `BaseEnvironment.exec` with the task directory as working directory, and `write_file` goes through `BaseEnvironment.upload_file`. Harnessie's loop is synchronous and Harbor's environment is asyncio, so the loop runs in a worker thread and each tool hands its coroutine back to Harbor's event loop.

## What a trial produces

Under the trial's `agent/` directory:

- `harnessie/events.jsonl`: Harnessie's hash-chained log for the run, including a `workflow_start` carrying the task instruction and a `harness_identity` event.
- `trajectory.json`: the same log exported as ATIF-v1.7 (`harnessie atif`), so Harbor's viewer shows it and OpenEnv's capture can be reconciled against it. The agent declares `AgentCapabilities(atif=True)`.
- `harnessie-result.json`: the loop's stop condition, step count, final report, trace metrics (including `tool_contract_breaks` and `tool_calls_per_completed_task`) and the harness identity.

`AgentContext` receives input and output token totals and a `metadata` block with the stop condition and metrics.

## Running it

The agent needs a model endpoint. Under OpenEnv that is the capture proxy, which records every call on the wire; without OpenEnv, point it straight at any OpenAI-compatible server.

Literal
```bash
PYTHONPATH=examples/harbor-agent HARNESSIE_HARBOR_BASE_URL=http://127.0.0.1:8100 HARNESSIE_HARBOR_API_KEY=<capture session id> harbor run -p <task or dataset dir> -a harnessie_harbor_agent:HarnessieAgent -m qwen3.8:latest -e docker -o runs/harbor-jobs
```

Kwargs via `--agent-kwarg key=value`: `max_steps` (default 17, the cap the multi-harness article used), `workdir` (default `/app`), `exec_timeout_sec` (default 300), `base_url`, `api_key_env`. The key's value is never read by this code; Harnessie's adapter reads the named environment variable at call time.

The agent also accepts `OPENAI_BASE_URL` and `OPENAI_API_KEY`, which is what a generic OpenEnv seam would set. OpenEnv 0.7.0's `openenv harbor rollout --harness module:Class` does not resolve an import path (its seam table only knows its named harnesses), so the recorded trials start the capture proxy standalone, mint a session, and run `harbor run` directly; reconciliation against the proxy's rollout is then done by hand, as for the ATIF acceptance.

## Testing without Harbor

`tests/test_harbor_agent_example.py` drives the remote tools against a fake environment on a real asyncio loop in a background thread, checks the jail, the allowlist and the role grants, and runs a full `AgentLoop` with a scripted brain through them, then exports and checks the ATIF trajectory. `HarnessieAgent` itself imports Harbor and is only loaded where Harbor is installed.

## Host cancellation

Harbor enforces `[agent] timeout_sec` by cancelling the agent coroutine. `AgentLoop` has no cancellation hook, so the model is wrapped in `CancellableModel`: on cancel, the next model call returns an error turn without touching the endpoint, the loop finishes `model_error` through `loop_finished`, the log closes, and the result and trajectory are still written. Harbor records the timeout; Harnessie records how the loop ended. Give a local model a realistic timeout: the first live trial lost a correct run to a 300 s cap.

## What this does and does not establish

Three Harbor trials on the Docker backend are recorded in `audits/harbor-agent-acceptance-2026-10-05.md`: Harbor's `hello-world` (3 steps, reward 1.0), and the `calc-add-mean` task with `HarnessieVerifier` as the verifier, so Harnessie sat on both sides (9 steps, reward 1.0, one policy refusal recovered from), plus the 300 s timeout trial that motivated the cancellation path. Both completed trials produced Harbor-valid ATIF whose step count matched the capture proxy's turn count.

It establishes that Harnessie can be a Harbor agent without changing either project, that its policy enforcement survives the move to a remote sandbox, and that a Harbor trial of it yields an ATIF trajectory and a hash-chained log that an independent capture can be checked against. One backend, two tasks, one local model; nothing here is evidence about a brain's quality.
