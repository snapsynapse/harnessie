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

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import yaml

from .adversarial import (PositionRecord, assemble_record, converged,
                          lint_record, parse_objection_response, parse_stance)
from .approval import ApprovalPolicy, tty_approval
from .cascade import (CascadePolicy, SIDEWAYS_REASONS, load_cascade_config,
                      validate_against_tiers)
from .events import EventLog
from .loop import AgentLoop, LoopResult
from .memory import ProjectMemory, ProofStore
from .models import build_model
from .models.base import EFFORT_LEVELS, ModelSpec
from .ownership import OwnershipLedger
from .quarantine import guard_result
from .roles import RoleLibrary
from .routing import Budget, Route, Router, TIER_ORDER
from .state import RunState, new_run_id
from .tools.builtin import register_builtin
from .tools.registry import ToolRegistry
from .verify import Check, GateResult, VerificationGate


def _escalation_reason(verdict) -> str:
    """Mechanical map from a failing gate verdict to a cascade reason.
    Refusals and availability failures move sideways (same tier, different
    provider), never automatically up — up-tiering on refusal is a
    containment leak, and a provider outage says nothing about task
    difficulty. Everything else is a gate failure."""
    if "loop stopped: refusal" in verdict.reasons:
        return "refusal"
    if "loop stopped: model_error" in verdict.reasons:
        return "availability"
    return "gate_fail"


def _climb_cost_estimate(spec: ModelSpec) -> float:
    """Worst-case dollars for one maximal model turn at a tier: max_tokens
    charged at both the input and output rate. The estimate behind the
    escalation-headroom refusal. Estimate shape is under contested decision
    (runs/20260707-115427-MCNRMR DR-decide: single-turn floor vs
    max_steps-scaled); this is the single-turn floor pending arbitration.
    Zero-cost tiers estimate zero and always clear the check."""
    return spec.max_tokens * (spec.cost_per_mtok_in
                              + spec.cost_per_mtok_out) / 1_000_000


def load_models_config(
    path: Path,
) -> tuple[dict[str, ModelSpec], dict, dict, dict[str, list[ModelSpec]]]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiers: dict[str, ModelSpec] = {}
    fallbacks: dict[str, list[ModelSpec]] = {}
    for name, spec in cfg.get("tiers", {}).items():
        spec = dict(spec)
        alt_rows = spec.pop("fallbacks", None) or []
        tiers[name] = ModelSpec(name=name, **spec)
        # A fallback inherits every field of its tier's primary and overrides
        # what it names (usually just model_id, sometimes base_url/provider):
        # a sideways move is the same tier contract on a different brain.
        fallbacks[name] = [
            ModelSpec(**{**spec, **dict(row), "name": f"{name}~alt{i + 1}"})
            for i, row in enumerate(alt_rows)
        ]
    routing = cfg.get("routing", {})
    _validate_models_config(path, tiers, routing, cfg.get("budget", {}))
    return tiers, routing, cfg.get("budget", {}), fallbacks


def _validate_models_config(
    path: Path,
    tiers: dict[str, ModelSpec],
    routing: dict,
    budget_cfg: dict,
) -> None:
    if not tiers:
        raise ValueError(f"{path}: at least one model tier is required")
    bad_tiers = set(tiers) - set(TIER_ORDER)
    if bad_tiers:
        raise ValueError(f"{path}: unknown tier names: {sorted(bad_tiers)}")
    for task_class, row in routing.items():
        tier = row.get("tier")
        effort = row.get("effort")
        if tier not in tiers:
            raise ValueError(
                f"{path}: routing.{task_class}.tier={tier!r} is not configured")
        if effort not in EFFORT_LEVELS:
            raise ValueError(
                f"{path}: routing.{task_class}.effort={effort!r} is invalid")
    if budget_cfg and (budget_cfg.get("max_usd", 0) <= 0
                       or budget_cfg.get("max_tokens", 0) <= 0):
        raise ValueError(f"{path}: budget ceilings must be positive")


@dataclass
class PhaseOutcome:
    phase: str
    status: str  # "passed" | "needs_human" | "needs_arbitration" | "skipped_resume"
    report: str
    spent_usd: float = 0.0
    spent_tokens: int = 0

HALT_STATUSES = ("needs_human", "needs_arbitration")


class WorkflowRunner:
    def __init__(self, project_root: Path, models_config: Path | None = None,
                 run_id: str | None = None, echo: bool = True,
                 approval_policy: Path | None = None,
                 interactive_approvals: bool = False) -> None:
        self.root = project_root.resolve()
        tiers, routing_table, budget_cfg, fallbacks = load_models_config(
            models_config or self.root / "config" / "models.yaml")
        self.router = Router(tiers=tiers, table=routing_table,
                             fallbacks=fallbacks)
        # Cascade policies (0.7, adopted via decisions/AIDR-0004): opt-in per
        # phase; a policy naming an unconfigured tier refuses at startup.
        self.cascade = load_cascade_config(self.root / "config" / "cascade.yaml")
        validate_against_tiers(self.cascade, tiers)
        self.budget = Budget(**budget_cfg)
        self.run_id = run_id or new_run_id()
        self.run_dir = self.root / "runs" / self.run_id
        self.events = EventLog(self.run_dir, echo=echo)
        self.state = RunState.open(self.run_dir)
        self.memory = ProjectMemory(self.root / "memory")
        self.proofs = ProofStore(self.run_dir)
        self.roles = RoleLibrary.load(self.root / "agents")
        self.registry = ToolRegistry()
        self.approval_policy = (ApprovalPolicy.load(approval_policy)
                                if approval_policy else None)
        self.interactive_approvals = interactive_approvals
        # The ownership ledger lives at the project root — outside the
        # workspace jail — so no agent can edit its own permissions.
        self.ledger = OwnershipLedger.load(self.root / "OWNERSHIP.yaml")
        register_builtin(self.registry, workspace=self.root / "workspace",
                         ledger=self.ledger, events=self.events,
                         memory=self.memory,
                         provenance=f"run {self.run_id}")
        (self.root / "workspace").mkdir(exist_ok=True)
        self._models: dict[str, object] = {}   # tier name -> ModelInterface cache

    # -- model plumbing ------------------------------------------------------

    def _loop_for(self, role_kind: str, route: Route, max_steps: int = 40,
                  deny_tools: frozenset[str] = frozenset(),
                  allow_network: bool = False, agent_name: str = "",
                  consent_required: bool = False,
                  registry: ToolRegistry | None = None,
                  budget: Budget | None = None) -> AgentLoop:
        spec = self.router.spec_for(route)
        if spec.name not in self._models:
            self._models[spec.name] = build_model(spec)
        return AgentLoop(role=role_kind, model=self._models[spec.name],
                         registry=registry or self.registry, events=self.events,
                         budget=budget or self.budget, max_steps=max_steps,
                         deny_tools=deny_tools, allow_network=allow_network,
                         agent_name=agent_name, consent_required=consent_required)

    def _run_role(self, agent_name: str, task: str, route: Route,
                  extra_context: str = "", max_steps: int = 40,
                  deny_tools: frozenset[str] = frozenset(),
                  allow_network: bool = False,
                  consent_required: bool = False,
                  registry: ToolRegistry | None = None,
                  budget: Budget | None = None) -> LoopResult:
        role = self.roles.get(agent_name)
        loop = self._loop_for(role.kind, route, max_steps=max_steps,
                              deny_tools=deny_tools, allow_network=allow_network,
                              agent_name=agent_name,
                              consent_required=consent_required,
                              registry=registry,
                              budget=budget)
        # Memory index goes to orchestrator phases only; workers and verifiers
        # get exactly what their task packet names (context hygiene).
        memory_index = (self.memory.context_block()
                        if role.kind == "orchestrator" else "")
        system = role.system_prompt(memory_index=memory_index,
                                    extra_context=extra_context)
        self.events.emit("role_start", agent=agent_name, role_kind=role.kind,
                         route={"tier": route.tier, "effort": route.effort})
        result = loop.run(system, task, effort=route.effort)
        spec = self.router.spec_for(route)
        self.events.emit("routing_trace", agent=agent_name, tier=route.tier,
                         effort=route.effort, alt=route.alt,
                         model=spec.model_id, provider=spec.provider,
                         outcome=result.stop)
        return result

    # -- workflow execution --------------------------------------------------

    def run_workflow(self, workflow_path: Path, goal: str = "") -> list[PhaseOutcome]:
        wf = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        try:
            workflow_ref = str(workflow_path.resolve().relative_to(self.root))
        except ValueError:
            workflow_ref = str(workflow_path)
        self.events.emit("workflow_start", name=wf.get("name"), run_id=self.run_id,
                         goal=goal, workflow=workflow_ref)
        outcomes: list[PhaseOutcome] = []
        reports: dict[str, str] = {"goal": goal}

        phases = wf.get("phases", [])
        handled_parallel: set[str] = set()
        for idx, phase in enumerate(phases):
            name = phase["name"]
            if name in handled_parallel:
                continue
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

            if phase.get("parallel"):
                group = []
                label = phase.get("parallel")
                for candidate in phases[idx:]:
                    if candidate.get("parallel") != label:
                        break
                    group.append(candidate)
                handled_parallel.update(p["name"] for p in group)
                group_outcomes = self._run_parallel_group(group, reports)
                for outcome in group_outcomes:
                    self.state.record(
                        f"phase:{outcome.phase}",
                        {"status": outcome.status, "report": outcome.report})
                    reports[outcome.phase] = outcome.report
                    outcomes.append(outcome)
                if any(o.status in HALT_STATUSES for o in group_outcomes):
                    break
                continue

            # Placeholder substitution by literal replace, not str.format —
            # phase reports routinely contain braces (JSON, code) that would
            # blow up format parsing.
            phase_start_usd = self.budget.spent_usd
            phase_start_tokens = self.budget.spent_tokens
            self.events.emit("phase_start", phase=name,
                             spent_usd=round(phase_start_usd, 4),
                             spent_tokens=phase_start_tokens)
            task = phase["task"]
            for key, value in reports.items():
                text = str(value)
                if key != "goal":
                    # Prior-phase reports are prior-model output: untrusted
                    # ingress, exactly like a read_file result. Fence flagged
                    # content as data-not-instructions before it lands in this
                    # phase's task. The goal is the operator's own instruction
                    # and is never fenced.
                    text, flags = guard_result(text, source=f"phase:{key}")
                    if flags:
                        self.events.emit("injection_flag", phase=name,
                                         source=f"phase:{key}", flags=flags)
                task = task.replace("{" + key + "}", text)
            if phase.get("inject_memory_status"):
                # Harness-prepared digest: memory and prior-run state live
                # outside the workspace jail, so the harness injects a
                # deterministic snapshot instead of widening any read surface.
                task = task.rstrip() + "\n\n" + self._memory_status_block()

            if phase.get("mode") == "adversarial":
                outcome = self._run_adversarial_phase(name, phase, task)
                self._stamp_phase_cost(outcome, phase_start_usd,
                                       phase_start_tokens)
                self.state.record(f"phase:{name}",
                                  {"status": outcome.status, "report": outcome.report})
                reports[name] = outcome.report
                outcomes.append(outcome)
                self.events.emit("phase_done", phase=name, status=outcome.status,
                                 spent_usd=round(self.budget.spent_usd, 4),
                                 spent_tokens=self.budget.spent_tokens,
                                 phase_spent_usd=outcome.spent_usd,
                                 phase_spent_tokens=outcome.spent_tokens)
                if outcome.status in HALT_STATUSES:
                    break
                continue

            task_class = phase.get("task_class", "default")
            route, escalate_fn, cascade_refusal = self._resolve_cascade(
                phase, self.router.route(task_class))
            if cascade_refusal:
                outcome = PhaseOutcome(name, "needs_human", cascade_refusal)
                self.state.record(f"phase:{name}",
                                  {"status": outcome.status,
                                   "report": outcome.report})
                reports[name] = outcome.report
                outcomes.append(outcome)
                self.events.emit("phase_done", phase=name,
                                 status=outcome.status,
                                 spent_usd=round(self.budget.spent_usd, 4),
                                 spent_tokens=self.budget.spent_tokens)
                break   # fail closed: an unroutable phase halts the run
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
                # Consent is the default for worker phases (task packets are
                # offers, not commands); a phase opts out explicitly for the
                # degenerate single-agent case.
                consent_required = bool(phase.get("consent", True))
                gate = VerificationGate(
                    workspace=self.root / "workspace", proofs=self.proofs,
                    events=self.events,
                    max_attempts=int(phase.get("verify", {}).get("max_attempts", 3)))
                # approve_tools is the operator's RECORDED pre-approval,
                # scoped to this phase: granted through the workflow file the
                # operator owns, journaled as approval events, and restored to
                # default-deny the moment the phase ends.
                prev_handler = self.registry.approval_handler
                self.registry.approval_handler = self._approval_handler_for(
                    name, frozenset(phase.get("approve_tools", [])))
                try:
                    gres: GateResult = gate.run(
                        task=task,
                        attempt_fn=lambda t, r: self._run_role(agent_name, t, r,
                                                               max_steps=max_steps,
                                                               deny_tools=deny_tools,
                                                               allow_network=allow_network,
                                                               consent_required=consent_required),
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
                        allow_network=allow_network,
                        harness_checks=self._harness_checks(phase),
                        escalate_fn=escalate_fn)
                finally:
                    self.registry.approval_handler = prev_handler
                outcome = PhaseOutcome(name, gres.status, gres.final_report)

            self._stamp_phase_cost(outcome, phase_start_usd, phase_start_tokens)
            self.state.record(f"phase:{name}",
                              {"status": outcome.status, "report": outcome.report})
            reports[name] = outcome.report
            outcomes.append(outcome)
            self.events.emit("phase_done", phase=name, status=outcome.status,
                             spent_usd=round(self.budget.spent_usd, 4),
                             spent_tokens=self.budget.spent_tokens,
                             phase_spent_usd=outcome.spent_usd,
                             phase_spent_tokens=outcome.spent_tokens)
            if outcome.status in HALT_STATUSES:
                break   # fail closed: later phases would build on unverified work

        self.events.emit("workflow_done", run_id=self.run_id,
                         statuses={o.phase: o.status for o in outcomes},
                         spent_usd=round(self.budget.spent_usd, 4),
                         proofs=self.proofs.listing())
        return outcomes

    def _run_parallel_group(
        self,
        phases: list[dict],
        reports: dict[str, str],
    ) -> list[PhaseOutcome]:
        snapshot = dict(reports)
        self.events.emit("parallel_group_start",
                         group=phases[0].get("parallel"),
                         phases=[p["name"] for p in phases])
        with ThreadPoolExecutor(max_workers=len(phases)) as pool:
            futures = [
                pool.submit(self._run_parallel_phase, phase, snapshot)
                for phase in phases
            ]
            outcomes = [future.result() for future in futures]
        self.events.emit("parallel_group_done",
                         group=phases[0].get("parallel"),
                         statuses={o.phase: o.status for o in outcomes})
        return outcomes

    def _run_parallel_phase(
        self,
        phase: dict,
        reports: dict[str, str],
    ) -> PhaseOutcome:
        name = phase["name"]
        if phase.get("mode") == "adversarial":
            return PhaseOutcome(
                name, "needs_human",
                "adversarial phases cannot run inside a parallel worker group")
        if self.state.has(f"phase:{name}"):
            prior = self.state.result(f"phase:{name}")
            if prior.get("status") == "passed":
                return PhaseOutcome(name, "skipped_resume",
                                    prior.get("report", ""))
        phase_budget = self.budget.child()
        if phase_budget.exhausted:
            return PhaseOutcome(
                name, "needs_human",
                "run budget exhausted before this parallel phase started; "
                "raise the ceiling in config/models.yaml (budget:) and resume "
                "the run")
        workspace = self.root / "workspace" / ".phases" / name
        workspace.mkdir(parents=True, exist_ok=True)
        registry = ToolRegistry()
        register_builtin(registry, workspace=workspace,
                         ledger=None, events=self.events,
                         memory=self.memory,
                         provenance=f"run {self.run_id}, phase {name}")
        task = self._render_task(phase, reports)
        outcome = self._execute_standard_phase(
            phase, task, workspace=workspace, registry=registry,
            budget=phase_budget)
        outcome.spent_usd = round(phase_budget.spent_usd, 6)
        outcome.spent_tokens = phase_budget.spent_tokens
        # charges flowed to self.budget live via the child budget; no merge here
        self.events.emit("phase_done", phase=name, status=outcome.status,
                         parallel=phase.get("parallel"),
                         workspace=str(workspace),
                         spent_usd=round(self.budget.spent_usd, 4),
                         spent_tokens=self.budget.spent_tokens,
                         phase_spent_usd=outcome.spent_usd,
                         phase_spent_tokens=outcome.spent_tokens)
        return outcome

    def _render_task(self, phase: dict, reports: dict[str, str]) -> str:
        name = phase["name"]
        task = phase["task"]
        for key, value in reports.items():
            text = str(value)
            if key != "goal":
                text, flags = guard_result(text, source=f"phase:{key}")
                if flags:
                    self.events.emit("injection_flag", phase=name,
                                     source=f"phase:{key}", flags=flags)
            task = task.replace("{" + key + "}", text)
        if phase.get("inject_memory_status"):
            task = task.rstrip() + "\n\n" + self._memory_status_block()
        return task

    def _execute_standard_phase(
        self,
        phase: dict,
        task: str,
        workspace: Path,
        registry: ToolRegistry,
        budget: Budget | None = None,
    ) -> PhaseOutcome:
        name = phase["name"]
        task_class = phase.get("task_class", "default")
        route, escalate_fn, cascade_refusal = self._resolve_cascade(
            phase, self.router.route(task_class), budget)
        if cascade_refusal:
            return PhaseOutcome(name, "needs_human", cascade_refusal)
        checks = [Check(**c) for c in phase.get("verify", {}).get("checks", [])]
        verifier_name = phase.get("verify", {}).get("verifier")
        agent_name = phase.get("agent", "orchestrator")
        max_steps = int(phase.get("max_steps", 40))
        deny_tools = frozenset(phase.get("deny_tools", []))
        allow_network = bool(phase.get("allow_network", False))

        if self.roles.get(agent_name).kind == "orchestrator":
            result = self._run_role(agent_name, task, route, max_steps=max_steps,
                                    deny_tools=deny_tools,
                                    allow_network=allow_network,
                                    registry=registry,
                                    budget=budget)
            return PhaseOutcome(
                name, "passed" if result.ok else "needs_human", result.report)

        consent_required = bool(phase.get("consent", True))
        gate = VerificationGate(
            workspace=workspace, proofs=self.proofs,
            events=self.events,
            max_attempts=int(phase.get("verify", {}).get("max_attempts", 3)))
        prev_handler = registry.approval_handler
        registry.approval_handler = self._approval_handler_for(
            name, frozenset(phase.get("approve_tools", [])))
        try:
            gres: GateResult = gate.run(
                task=task,
                attempt_fn=lambda t, r: self._run_role(
                    agent_name, t, r, max_steps=max_steps,
                    deny_tools=deny_tools, allow_network=allow_network,
                    consent_required=consent_required, registry=registry,
                    budget=budget),
                verify_fn=(
                    (lambda worker_report: self._run_role(
                        verifier_name,
                        self._verifier_task(task, phase, worker_report),
                        self.router.route(
                            phase.get("verify", {}).get("task_class", "verify")),
                        max_steps=20,
                        registry=registry,
                        budget=budget))
                    if verifier_name else None),
                checks=checks,
                route=route,
                allow_network=allow_network,
                harness_checks=self._harness_checks(phase),
                escalate_fn=escalate_fn)
        finally:
            registry.approval_handler = prev_handler
        return PhaseOutcome(name, gres.status, gres.final_report)

    def _resolve_cascade(self, phase: dict, route: Route,
                         budget: Budget | None = None):
        """Cascade opt-in resolution shared by the sequential and parallel
        dispatch sites. Returns (route, escalate_fn, refusal). refusal is
        None when resolved; otherwise the fail-closed message for a cascade
        reference the config does not know (no model is ever dispatched)."""
        cascade_name = phase.get("cascade")
        if not cascade_name:
            return route, None, None
        try:
            policy = self.cascade.policy(str(cascade_name))
        except ValueError as exc:
            return route, None, (
                f"{exc}; fix the phase's cascade reference in the workflow "
                "or add the policy to config/cascade.yaml, then resume the run")
        return (Route(policy.ladder[0], route.effort),
                self._cascade_escalator(policy, phase["name"],
                                        budget or self.budget), None)

    def _cascade_escalator(self, policy: CascadePolicy, phase_name: str,
                           budget: Budget):
        """Policy-driven gate escalation for a cascade-opted phase.

        Motion order per failing attempt: sideways first (refusal and
        availability move to the tier's next configured fallback, same tier,
        never up), then effort within the tier (the 0.6 motion), then a tier
        climb as the policy's decision — and an approved climb is still
        refused when the remaining run budget cannot cover its worst-case
        first turn. Every tier decision is an event so routing drift stays
        visible."""
        climbs = {"used": 0}

        def escalate(route: Route, verdict) -> Route | None:
            reason = _escalation_reason(verdict)
            if reason in SIDEWAYS_REASONS:
                alts = self.router.fallbacks.get(route.tier, [])
                if route.alt < len(alts):
                    self.events.emit(
                        "cascade_decision", phase=phase_name,
                        policy=policy.name, action="sideways",
                        tier=route.tier,
                        reason=f"{reason} moves sideways to "
                               f"{alts[route.alt].model_id} (fallback "
                               f"{route.alt + 1} of {len(alts)})")
                    return Route(route.tier, route.effort, route.alt + 1)
                if reason == "availability":
                    self.events.emit(
                        "cascade_decision", phase=phase_name,
                        policy=policy.name, action="hold", tier=route.tier,
                        reason="availability failure with no fallback left; "
                               "holding (availability never climbs)")
                    return route
                # refusal with every fallback spent falls through: the policy
                # decides (a contained policy can never name refusal)
            e_idx = EFFORT_LEVELS.index(route.effort)
            if e_idx < len(EFFORT_LEVELS) - 1:
                return Route(route.tier, EFFORT_LEVELS[e_idx + 1], route.alt)
            decision = policy.next_tier(route.tier, climbs["used"], reason)
            if decision.action == "climb":
                target = self.router.spec_for(Route(decision.tier, "medium"))
                estimate = _climb_cost_estimate(target)
                remaining = budget.max_usd - budget.spent_usd
                if estimate > remaining:
                    self.events.emit(
                        "cascade_decision", phase=phase_name,
                        policy=policy.name, action="refused_headroom",
                        tier=decision.tier,
                        reason=f"climb to {decision.tier} needs "
                               f"~${estimate:.4f} and ${remaining:.4f} of "
                               "the run budget remains; refused before "
                               "dispatch")
                    return None         # an escalation never busts the ceiling
                self.events.emit("cascade_decision", phase=phase_name,
                                 policy=policy.name, action="climb",
                                 tier=decision.tier, reason=decision.reason)
                climbs["used"] += 1
                return Route(decision.tier, "medium")
            self.events.emit("cascade_decision", phase=phase_name,
                             policy=policy.name, action=decision.action,
                             tier=decision.tier, reason=decision.reason)
            if decision.action == "hold":
                return route            # retry reformulated on the same rung
            return None                 # exhausted: gate hands to the operator

        return escalate

    def _stamp_phase_cost(
        self,
        outcome: PhaseOutcome,
        start_usd: float,
        start_tokens: int,
    ) -> None:
        outcome.spent_usd = round(self.budget.spent_usd - start_usd, 6)
        outcome.spent_tokens = self.budget.spent_tokens - start_tokens

    # -- governance helpers ----------------------------------------------------

    def _approval_handler_for(self, phase_name: str,
                              approve_tools: frozenset[str]):
        """Per-phase approval handler. Operator actions enter the SAME audit
        stream as agent actions: every grant and every denial is an event."""
        def handler(tool: str, args: dict) -> bool:
            if tool in approve_tools:
                self.events.emit("approval_granted", tool=tool,
                                 phase=phase_name, source="workflow-config")
                return True
            if self.approval_policy is not None:
                decision = self.approval_policy.decide(phase_name, tool, args)
                if decision is not None:
                    kind = "approval_granted" if decision else "approval_denied"
                    self.events.emit(kind, tool=tool, phase=phase_name,
                                     source="policy-file")
                    if self.approval_policy.problems:
                        self.events.emit("approval_policy_invalid",
                                         phase=phase_name,
                                         problems=self.approval_policy.problems)
                    return decision
            if self.interactive_approvals:
                decision = tty_approval(phase_name, tool, args)
                if decision is not None:
                    kind = "approval_granted" if decision else "approval_denied"
                    self.events.emit(kind, tool=tool, phase=phase_name,
                                     source="tty")
                    return decision
            self.events.emit("approval_denied", tool=tool,
                             phase=phase_name, source="default-deny")
            return False
        return handler

    def _harness_checks(self, phase: dict) -> list:
        """Deterministic checks the harness runs itself (no shell, no sandbox
        needed) — currently memory_lint: index/provenance consistency."""
        from .verify import CheckResult
        checks = []
        if phase.get("verify", {}).get("memory_lint"):
            def memory_lint(attempt: int) -> CheckResult:
                problems = self.memory.lint()
                return CheckResult(
                    "memory-lint", not problems,
                    "\n".join(problems) if problems
                    else "memory index and provenance consistent")
            checks.append(memory_lint)
        return checks

    def _memory_status_block(self) -> str:
        """Deterministic memory digest injected into triage-style phases."""
        lines = ["## Memory status (harness-injected)", "", "### Index",
                 self.memory.context_block(), "",
                 "### Stale facts (past verify_by)"]
        stale = self.memory.stale_facts()
        if stale:
            lines += [f"- {f['slug']} (verify_by {f['verify_by']}): {f['title']}"
                      for f in stale]
        else:
            lines.append("(none)")
        lines += ["", "### Recent run outcomes"]
        runs_dir = self.root / "runs"
        listed = 0
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir(), reverse=True):
                if run_dir.name == self.run_id or listed >= 5:
                    continue
                journal = run_dir / "journal.jsonl"
                if not journal.exists():
                    continue
                phases = []
                for line in journal.read_text(encoding="utf-8").splitlines():
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("kind") == "step_done":
                        key = rec.get("step_key", "")
                        status = (rec.get("result") or {}).get("status", "?")
                        phases.append(f"{key.removeprefix('phase:')}={status}")
                lines.append(f"- run {run_dir.name}: "
                             + (", ".join(phases) or "(no phases journaled)"))
                listed += 1
        if listed == 0:
            lines.append("(no prior runs)")
        return "\n".join(lines)

    # -- adversarial contested phases -----------------------------------------

    def _run_adversarial_phase(self, name: str, phase: dict,
                               task: str) -> PhaseOutcome:
        """Positions -> objections -> record -> convergence or human.

        The record lives under runs/<id>/decisions/ — outside the workspace
        jail, unreachable by agents. Arbitration is human-only: on resume this
        method re-lints the record instead of re-running positions (re-running
        would overwrite recorded dissent, which is never done)."""
        decisions_dir = self.run_dir / "decisions"
        record_path = decisions_dir / f"DR-{name}.md"

        if record_path.exists():
            lint = lint_record(record_path.read_text(encoding="utf-8"))
            if "human-arbitrated" in lint["claims"]:
                # The operator's arbitration is itself an audited action in
                # the composite timeline, same stream as agent actions.
                self.events.emit("operator_action", action="arbitration",
                                 phase=name, record=str(record_path))
                self.events.emit("decision_arbitrated", phase=name,
                                 record=str(record_path),
                                 decision=lint["decision"][:300])
                return PhaseOutcome(
                    name, "passed",
                    f"Arbitrated decision: {lint['decision']}\n"
                    f"(record: {record_path}, claims: {lint['claims']})")
            self.events.emit("needs_arbitration", phase=name,
                             record=str(record_path), errors=lint["errors"])
            return PhaseOutcome(
                name, "needs_arbitration",
                f"decision record awaits human arbitration: {record_path}\n"
                "Edit the Arbitration section in your own words, set "
                "status: arbitrated and a decided: date, then resume the run."
                + (f"\nlint errors to fix: {lint['errors']}" if lint["errors"] else ""))

        # Position round: identical brief, isolated contexts, read-only grants.
        deny = self.registry.side_effect_tools()
        specs = phase.get("positions", []) or []
        positions: list[PositionRecord] = []
        routes: list[Route] = []
        seen_labels: dict[str, int] = {}
        for pos_spec in specs:
            agent = pos_spec.get("agent", "implementer")
            n = seen_labels.get(agent, 0) + 1
            seen_labels[agent] = n
            label = agent if n == 1 else f"{agent}-{n}"
            route = self.router.route(
                pos_spec.get("task_class", phase.get("task_class", "default")))
            spec = self.router.spec_for(route)
            pos_task = (
                f"{task}\n\n## Position protocol\n"
                "You are one of several agents forming INDEPENDENT positions on "
                "this question. You have read-only access: inspect, do not build. "
                "You have not been shown the other positions; do not speculate "
                "about them. End your task_complete report with exactly one JSON "
                'object: {"stance": "recommend|oppose|alternative|abstain", '
                '"summary": "<one sentence>"} — your prose argument goes before it.')
            result = self._run_role(agent, pos_task, route,
                                    max_steps=int(phase.get("max_steps", 20)),
                                    deny_tools=deny)
            parsed = parse_stance(result.report) if result.ok else None
            if parsed is None:
                # fail closed: an unparseable stance is dissent, not silence
                stance, summary = "abstain", (
                    f"(stance unparseable; loop stop: {result.stop} — treated "
                    "as dissent, forcing arbitration)")
            else:
                stance, summary = parsed["stance"], parsed["summary"]
            positions.append(PositionRecord(
                label=label, agent=agent, model_id=spec.model_id,
                provider=spec.provider, stance=stance, summary=summary,
                prose=result.report))
            routes.append(route)
            self.events.emit("position_recorded", phase=name, label=label,
                             model=spec.model_id, stance=stance)

        # Objection rounds (bounded): every agent sees the other positions and
        # returns objections or an explicit no-new-objection marker.
        objections: list[dict[str, str]] = []
        forced_dissent = any(p.summary.startswith("(stance unparseable") for p in positions)
        for _ in range(max(1, int(phase.get("rebuttal_rounds", 1)))):
            new_in_round: list[dict[str, str]] = []
            for pos, route in zip(positions, routes):
                others = "\n\n".join(
                    f"### {p.label} — stance: {p.stance}\nsummary: {p.summary}\n"
                    f"{p.prose[:2000]}"
                    for p in positions if p.label is not pos.label)
                standing = "\n".join(f"- {o['by']}: {o['text']}" for o in objections)
                obj_task = (
                    f"{task}\n\n## Objection round\n"
                    f"Your recorded position ({pos.label}): stance {pos.stance} — "
                    f"{pos.summary}\n\n## Other positions\n{others}\n\n"
                    + (f"## Standing objections\n{standing}\n\n" if standing else "")
                    + "Review the other positions for concrete failure modes, "
                    "contradictions, or risks. End your task_complete report with "
                    'exactly one JSON object: {"objections": ["<concrete objection>", '
                    '...], "no_new_objection": true|false}. An empty list with '
                    "no_new_objection true means you stand down.")
                result = self._run_role(pos.agent, obj_task, route,
                                        max_steps=int(phase.get("max_steps", 20)),
                                        deny_tools=deny)
                parsed = parse_objection_response(result.report) if result.ok else None
                if parsed is None:
                    new_in_round.append({
                        "by": pos.label, "to": "the record",
                        "text": f"(unparseable objection response; loop stop: "
                                f"{result.stop} — treated as dissent, fail closed)"})
                else:
                    for objection in parsed["objections"]:
                        new_in_round.append({"by": pos.label, "to": "the record",
                                             "text": objection})
            for o in new_in_round:
                self.events.emit("objection_recorded", phase=name, by=o["by"],
                                 text=o["text"][:200])
            objections.extend(new_in_round)
            if not new_in_round:
                break   # Turnfile convergence: a full quiet round ends the loop

        # Assembly — by the harness, never an agent. Dissent is never deleted.
        record_text = assemble_record(
            record_id=f"DR-{name}", title=f"Contested phase: {name}",
            question=task, context=(
                f"Contested decision raised by workflow phase {name!r} in run "
                f"{self.run_id}. Assembled by the harness from "
                f"{len(positions)} independent position(s)."),
            arbiter=str(phase.get("arbiter", "operator")),
            positions=positions, objections=objections,
            evidence=[f"runs/{self.run_id}/events.jsonl — hash-chained event "
                      "log evidencing isolated position generation"])
        decisions_dir.mkdir(parents=True, exist_ok=True)
        record_path.write_text(record_text, encoding="utf-8")
        lint = lint_record(record_text)
        self.events.emit("decision_assembled", phase=name,
                         record=str(record_path), claims=lint["claims"],
                         errors=lint["errors"])

        mode = phase.get("arbitration", "convergence")
        if (mode == "convergence" and not forced_dissent
                and converged(positions, objections) and not lint["errors"]):
            self.events.emit("decision_converged", phase=name,
                             record=str(record_path))
            summary = "; ".join(f"{p.label}: {p.summary}" for p in positions)
            return PhaseOutcome(
                name, "passed",
                f"Converged without arbitration — all positions recommend. "
                f"{summary}\n(record: {record_path}, claims: {lint['claims']})")

        self.events.emit("needs_arbitration", phase=name,
                         record=str(record_path))
        return PhaseOutcome(
            name, "needs_arbitration",
            f"contested decision awaits human arbitration: {record_path}\n"
            "Edit the Arbitration section in your own words (address every "
            "objection), set status: arbitrated and a decided: date, then "
            "resume the run.")

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
