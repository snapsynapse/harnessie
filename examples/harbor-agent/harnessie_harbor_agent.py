"""Harnessie as a Harbor external agent, running on the host.

Harbor's `BaseAgent` is for agents whose loop runs outside the task
environment and acts on it through `BaseEnvironment`. That is Harnessie's
shape: the orchestration, policy and audit stay on the host, and the only
things that cross into the sandbox are allowlisted commands and file
uploads. The model is reached through whatever endpoint the caller names,
which under OpenEnv is the capture proxy, so the run is recorded on the
wire as well as in Harnessie's own hash-chained log.

What Harbor gets back: the task's artifacts in the sandbox, Harnessie's
events.jsonl under the agent log directory, a `trajectory.json` in ATIF
(`capabilities.atif`), token counts on the `AgentContext`, and a
`harnessie-result.json` with the loop's stop condition and trace metrics.

Run one task:

    PYTHONPATH=examples/harbor-agent HARNESSIE_HARBOR_BASE_URL=http://127.0.0.1:8100 \\
      HARNESSIE_HARBOR_API_KEY=<capture session id> \\
      harbor run -p <tasks> -a harnessie_harbor_agent:HarnessieAgent \\
      -m qwen3.8:latest -e docker -o runs/harbor-jobs

Kwargs (`--agent-kwarg key=value`): `max_steps` (default 17, the cap the
multi-harness article used), `workdir` (default `/app`), `exec_timeout_sec`
(default 300), `base_url`, `api_key_env`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.agents.capabilities import AgentCapabilities
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from harness import __version__ as HARNESSIE_VERSION
from harness.atif import AtifExportError, write_trajectory
from harness.events import EventLog
from harness.identity import harness_identity
from harness.loop import AgentLoop
from harness.models import build_model
from harness.models.base import ModelSpec
from harness.roles import RoleDef
from harness.tools.registry import ToolRegistry
from harness.trace_eval import analyze_trace, load_events

from harbor_tools import (
    CancellableModel,
    SandboxBridge,
    register_remote_tools,
    resolve_endpoint,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKER_PROMPT = REPO_ROOT / "agents" / "workers" / "implementer.md"
FALLBACK_PROMPT = (
    "# Role: Implementer (worker)\n\nYou execute one scoped task inside a "
    "workspace using the tools you are given. Ground yourself by listing and "
    "reading files before acting. Work in small checkable steps. When the task "
    "is done, call task_complete with a report naming what changed and the "
    "evidence it works. If the task is impossible as written, say so in "
    "task_complete instead of improvising a different task.")


class HarnessieAgent(BaseAgent):
    capabilities = AgentCapabilities(atif=True)

    @staticmethod
    def name() -> str:
        return "harnessie"

    def version(self) -> str:
        return HARNESSIE_VERSION

    def __init__(self, logs_dir: Path, model_name: str | None = None, *,
                 max_steps: int | str = 17, workdir: str = "/app",
                 exec_timeout_sec: int | str = 300, base_url: str | None = None,
                 api_key_env: str | None = None, **kwargs: Any) -> None:
        super().__init__(logs_dir=logs_dir, model_name=model_name, **kwargs)
        self.max_steps = int(max_steps)
        self.workdir = workdir
        self.exec_timeout_sec = int(exec_timeout_sec)
        self.base_url, self.api_key_env = resolve_endpoint(base_url, api_key_env)

    async def setup(self, environment: BaseEnvironment) -> None:
        # Host-side agent: nothing to install in the sandbox.
        return None

    def _model_spec(self) -> ModelSpec:
        return ModelSpec(name="harbor", provider="openai-compat",
                         model_id=self.model_name or "default",
                         base_url=self.base_url, api_key_env=self.api_key_env,
                         max_tokens=4096)

    def _system_prompt(self) -> str:
        prompt = WORKER_PROMPT.read_text(encoding="utf-8") if WORKER_PROMPT.is_file() \
            else FALLBACK_PROMPT
        role = RoleDef(name="implementer", kind="worker", prompt=prompt)
        return role.system_prompt(extra_context=(
            f"The workspace is the task environment's `{self.workdir}` directory, "
            "reached only through your tools; paths are relative to it and there "
            "is no local filesystem. Shell commands run inside that environment. "
            "Follow the task's own submission protocol exactly, then call "
            "task_complete."))

    async def run(self, instruction: str, environment: BaseEnvironment,
                  context: AgentContext) -> None:
        loop = asyncio.get_running_loop()
        run_dir = self.logs_dir / "harnessie"
        events = EventLog(run_dir, echo=False)
        bridge = SandboxBridge(environment=environment, loop=loop,
                               workdir=self.workdir, timeout_sec=self.exec_timeout_sec)
        registry = ToolRegistry()
        register_remote_tools(registry, bridge)
        session = self.session_id or run_dir.parent.name
        # The instruction is the user step of the exported trajectory; the
        # events log keeps it so the trajectory is built from the record, not
        # from memory.
        events.emit("workflow_start", name="harbor-task", run_id=session,
                    goal=instruction,
                    workflow_sha256=hashlib.sha256(instruction.encode()).hexdigest())
        identity = harness_identity(
            REPO_ROOT if (REPO_ROOT / "INWARD_MANIFEST.yaml").is_file() else None,
            registry)
        events.emit("harness_identity", **identity)
        spec = self._model_spec()
        model = CancellableModel(build_model(spec))
        agent_loop = AgentLoop(role="worker", model=model, registry=registry,
                               events=events, max_steps=self.max_steps,
                               agent_name="implementer")
        task = (f"{instruction.strip()}\n\nThe task's own verifier runs after you "
                "finish; leave every required artifact in the workspace.")
        worker = asyncio.ensure_future(
            asyncio.to_thread(agent_loop.run, self._system_prompt(), task, "medium"))
        result = None
        cancelled = False
        try:
            result = await asyncio.shield(worker)
        except asyncio.CancelledError:
            # Harbor's agent timeout. Tell the loop to stop at its next model
            # call so it finishes through loop_finished and the log stays
            # exportable, then re-raise so Harbor records the timeout.
            cancelled = True
            model.cancel()
            try:
                result = await asyncio.wait_for(asyncio.shield(worker),
                                                timeout=self.exec_timeout_sec + 30)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                result = None
        finally:
            events.emit("harbor_agent_done",
                        stop=(result.stop if result is not None else "cancelled"),
                        host_cancelled=cancelled)
            events.close()
            self._finalize(run_dir, context, result, cancelled, bridge, spec, identity)
        if cancelled:
            raise asyncio.CancelledError

    def _finalize(self, run_dir: Path, context: AgentContext, result: Any,
                  cancelled: bool, bridge: SandboxBridge, spec: ModelSpec,
                  identity: dict[str, str]) -> None:
        trace = load_events(run_dir / "events.jsonl")
        metrics = analyze_trace(trace)
        turns = [e for e in trace if e.get("kind") == "model_turn"]
        context.n_input_tokens = sum(int(e.get("input_tokens") or 0) for e in turns)
        context.n_output_tokens = sum(int(e.get("output_tokens") or 0) for e in turns)
        stop = result.stop if result is not None else "cancelled"
        steps = result.steps if result is not None else len(turns)
        context.metadata = {
            "harness": "harnessie", "stop": stop, "steps": steps,
            "host_cancelled": cancelled,
            "tool_contract_breaks": metrics["tool_contract_breaks"],
            "tool_results": metrics["tool_results"],
            "sandbox_calls": len(bridge.calls), **identity,
        }
        (self.logs_dir / "harnessie-result.json").write_text(json.dumps({
            "stop": stop, "steps": steps, "host_cancelled": cancelled,
            "report": (result.report[:4000] if result is not None else ""),
            "metrics": metrics, "model": spec.model_id, "endpoint": spec.base_url,
            "identity": identity,
        }, indent=2) + "\n", encoding="utf-8")
        try:
            write_trajectory(run_dir, self.logs_dir / "trajectory.json", force=True)
        except AtifExportError as exc:
            (self.logs_dir / "trajectory-refused.txt").write_text(
                f"{exc}\n", encoding="utf-8")


__all__ = ["HarnessieAgent"]
