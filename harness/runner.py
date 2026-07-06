"""WorkflowRunner: executes a workflows/*.yaml definition phase by phase.

A workflow is a declared sequence of phases. Each phase names a role prompt,
a task template, a task_class (which the Router maps to model tier + effort),
optional deterministic checks, and an optional verifier agent. Worker phases
run inside the VerificationGate; nothing advances on an unverified result.

Phase results are journaled (state.py); re-running a crashed run skips
completed phases. Prior phase reports are available to later phases via
{phase_name} placeholders in task templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .events import EventLog
from .loop import AgentLoop, LoopResult
from .memory import ProjectMemory, ProofStore
from .models import build_model
from .models.base import ModelSpec
from .roles import RoleLibrary
from .routing import Budget, Route, Router
from .state import RunState, new_run_id
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import Check, GateResult, VerificationGate


def load_models_config(path: Path) -> tuple[dict[str, ModelSpec], dict, dict]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiers = {
        name: ModelSpec(name=name, **{k: v for k, v in spec.items()})
        for name, spec in cfg.get("tiers", {}).items()
    }
    return tiers, cfg.get("routing", {}), cfg.get("budget", {})


@dataclass
class PhaseOutcome:
    phase: str
    status: str          # "passed" | "needs_human" | "skipped_resume"
    report: str


class WorkflowRunner:
    def __init__(self, project_root: Path, models_config: Path | None = None,
                 run_id: str | None = None, echo: bool = True) -> None:
        self.root = project_root.resolve()
        tiers, routing_table, budget_cfg = load_models_config(
            models_config or self.root / "config" / "models.yaml")
        self.router = Router(tiers=tiers, table=routing_table)
        self.budget = Budget(**budget_cfg)
        self.run_id = run_id or new_run_id()
        self.run_dir = self.root / "runs" / self.run_id
        self.events = EventLog(self.run_dir, echo=echo)
        self.state = RunState.open(self.run_dir)
        self.memory = ProjectMemory(self.root / "memory")
        self.proofs = ProofStore(self.run_dir)
        self.roles = RoleLibrary.load(self.root / "agents")
        self.registry = ToolRegistry()
        register_builtin(self.registry, workspace=self.root / "workspace")
        (self.root / "workspace").mkdir(exist_ok=True)
        self._models: dict[str, object] = {}   # tier name -> ModelInterface cache

    # -- model plumbing ------------------------------------------------------

    def _loop_for(self, role_kind: str, route: Route, max_steps: int = 40,
                  deny_tools: frozenset[str] = frozenset(),
                  allow_network: bool = False) -> AgentLoop:
        spec = self.router.spec_for(route)
        if spec.name not in self._models:
            self._models[spec.name] = build_model(spec)
        return AgentLoop(role=role_kind, model=self._models[spec.name],
                         registry=self.registry, events=self.events,
                         budget=self.budget, max_steps=max_steps,
                         deny_tools=deny_tools, allow_network=allow_network)

    def _run_role(self, agent_name: str, task: str, route: Route,
                  extra_context: str = "", max_steps: int = 40,
                  deny_tools: frozenset[str] = frozenset(),
                  allow_network: bool = False) -> LoopResult:
        role = self.roles.get(agent_name)
        loop = self._loop_for(role.kind, route, max_steps=max_steps,
                              deny_tools=deny_tools, allow_network=allow_network)
        # Memory index goes to orchestrator phases only; workers and verifiers
        # get exactly what their task packet names (context hygiene).
        memory_index = (self.memory.context_block()
                        if role.kind == "orchestrator" else "")
        system = role.system_prompt(memory_index=memory_index,
                                    extra_context=extra_context)
        self.events.emit("role_start", agent=agent_name, role_kind=role.kind,
                         route=vars(route))
        return loop.run(system, task, effort=route.effort)

    # -- workflow execution --------------------------------------------------

    def run_workflow(self, workflow_path: Path, goal: str = "") -> list[PhaseOutcome]:
        wf = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        self.events.emit("workflow_start", name=wf.get("name"), run_id=self.run_id,
                         goal=goal)
        outcomes: list[PhaseOutcome] = []
        reports: dict[str, str] = {"goal": goal}

        for phase in wf.get("phases", []):
            name = phase["name"]
            if self.state.has(f"phase:{name}"):
                prior = self.state.result(f"phase:{name}")
                # Resume skips ONLY verified successes. A journaled needs_human
                # phase re-runs; silently skipping it would let later phases
                # build on unverified work, the exact thing the gate halts for.
                if prior.get("status") == "passed":
                    reports[name] = prior.get("report", "")
                    outcomes.append(PhaseOutcome(name, "skipped_resume",
                                                 reports[name]))
                    continue

            # Placeholder substitution by literal replace, not str.format —
            # phase reports routinely contain braces (JSON, code) that would
            # blow up format parsing.
            task = phase["task"]
            for key, value in reports.items():
                task = task.replace("{" + key + "}", str(value))
            task_class = phase.get("task_class", "default")
            route = self.router.route(task_class)
            checks = [Check(**c) for c in phase.get("verify", {}).get("checks", [])]
            verifier_name = phase.get("verify", {}).get("verifier")
            agent_name = phase.get("agent", "orchestrator")
            max_steps = int(phase.get("max_steps", 40))
            deny_tools = frozenset(phase.get("deny_tools", []))
            allow_network = bool(phase.get("allow_network", False))

            if self.roles.get(agent_name).kind == "orchestrator":
                # Orchestrator phases (planning/integration) are not gated by a
                # verifier — their output is a plan consumed by gated phases —
                # but they are still journaled and budgeted.
                result = self._run_role(agent_name, task, route, max_steps=max_steps,
                                        deny_tools=deny_tools, allow_network=allow_network)
                outcome = PhaseOutcome(
                    name, "passed" if result.ok else "needs_human", result.report)
            else:
                gate = VerificationGate(
                    workspace=self.root / "workspace", proofs=self.proofs,
                    events=self.events,
                    max_attempts=int(phase.get("verify", {}).get("max_attempts", 3)))
                gres: GateResult = gate.run(
                    task=task,
                    attempt_fn=lambda t, r: self._run_role(agent_name, t, r,
                                                           max_steps=max_steps,
                                                           deny_tools=deny_tools,
                                                           allow_network=allow_network),
                    verify_fn=(
                        (lambda worker_report: self._run_role(
                            verifier_name,
                            self._verifier_task(task, phase, worker_report),
                            self.router.route(
                                phase.get("verify", {}).get("task_class", "verify")),
                            max_steps=20))    # verifier stays network-denied
                        if verifier_name else None),
                    checks=checks,
                    route=route,
                    allow_network=allow_network)
                outcome = PhaseOutcome(name, gres.status, gres.final_report)

            self.state.record(f"phase:{name}",
                              {"status": outcome.status, "report": outcome.report})
            reports[name] = outcome.report
            outcomes.append(outcome)
            self.events.emit("phase_done", phase=name, status=outcome.status,
                             spent_usd=round(self.budget.spent_usd, 4))
            if outcome.status == "needs_human":
                break   # fail closed: later phases would build on unverified work

        self.events.emit("workflow_done", run_id=self.run_id,
                         statuses={o.phase: o.status for o in outcomes},
                         spent_usd=round(self.budget.spent_usd, 4),
                         proofs=self.proofs.listing())
        return outcomes

    @staticmethod
    def _verifier_task(task: str, phase: dict, worker_report: str) -> str:
        criteria = phase.get("verify", {}).get("criteria", "")
        return (
            "Verify completed work against its acceptance criteria.\n\n"
            f"## Original task\n{task}\n\n"
            f"## Acceptance criteria\n{criteria or '(derive from the task)'}\n\n"
            f"## Worker's final report (claims, unverified)\n{worker_report}\n\n"
            "Inspect the actual artifacts in the workspace with your tools. "
            "Treat the report as claims to test, not facts. Then call "
            "task_complete with your JSON verdict.")
