"""Routing policy: which brain, at what effort, for which task.

The cost-control thesis of the harness: the orchestrator and final verifier
are worth frontier tokens; most execution is not. Routing is explicit config
(config/models.yaml `routing:` section), not vibes, and every routing decision
is logged so drift is visible.

Escalation ladder (applied by VerificationGate on repeated failure):
    tier N, same effort
      -> tier N, effort+1, task reformulated with failure evidence
        -> tier N+1 (more capable model)
          -> human

Budgets are hard ceilings. A run that exceeds its token/USD budget stops and
reports rather than silently burning money.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .models.base import EFFORT_LEVELS, ModelSpec

# tiers ordered cheap -> capable; escalation walks right
TIER_ORDER = ("local", "cheap", "mid", "frontier")


@dataclass
class Route:
    tier: str
    effort: str

    def escalate(self) -> "Route | None":
        """Next rung on the ladder: bump effort first, then tier. None when
        there is nothing above (hand to human)."""
        e_idx = EFFORT_LEVELS.index(self.effort)
        if e_idx < len(EFFORT_LEVELS) - 1:
            return Route(self.tier, EFFORT_LEVELS[e_idx + 1])
        t_idx = TIER_ORDER.index(self.tier)
        if t_idx < len(TIER_ORDER) - 1:
            return Route(TIER_ORDER[t_idx + 1], "medium")
        return None


@dataclass
class Budget:
    max_usd: float = 10.0
    max_tokens: int = 2_000_000
    spent_usd: float = 0.0
    spent_tokens: int = 0
    _lock: object = field(default_factory=threading.Lock, repr=False)
    _parent: "Budget | None" = field(default=None, repr=False)

    def charge(self, spec: ModelSpec, tokens_in: int, tokens_out: int) -> None:
        with self._lock:
            self.spent_tokens += tokens_in + tokens_out
            self.spent_usd += (tokens_in * spec.cost_per_mtok_in
                               + tokens_out * spec.cost_per_mtok_out) / 1_000_000
        if self._parent is not None:
            self._parent.charge(spec, tokens_in, tokens_out)

    def add_spend(self, spent_usd: float, spent_tokens: int) -> None:
        with self._lock:
            self.spent_usd += spent_usd
            self.spent_tokens += spent_tokens
        if self._parent is not None:
            self._parent.add_spend(spent_usd, spent_tokens)

    def child(self) -> "Budget":
        """Headroom-scoped view for one parallel phase.

        The child's ceiling is what the run has left at creation time, and
        every charge flows through to the parent, so sibling phases see each
        other's spend mid-group. Overshoot is bounded to the model turns
        already in flight when the ceiling is crossed, not (N-1)x the run
        ceiling as with an independently seeded copy.
        """
        with self._lock:
            return Budget(max_usd=max(self.max_usd - self.spent_usd, 0.0),
                          max_tokens=max(self.max_tokens - self.spent_tokens, 0),
                          _parent=self)

    @property
    def exhausted(self) -> bool:
        if self._parent is not None and self._parent.exhausted:
            return True
        return self.spent_usd >= self.max_usd or self.spent_tokens >= self.max_tokens


@dataclass
class Router:
    """Maps (role, task_class) -> Route using the routing table from config.

    task_class comes from the workflow definition (each step declares its
    class), not from model self-assessment — a cheap model asked to grade its
    own task difficulty will underestimate it.
    """

    tiers: dict[str, ModelSpec]                 # tier name -> model spec
    table: dict[str, dict] = field(default_factory=dict)  # task_class -> {tier, effort}
    default: Route = field(default_factory=lambda: Route("mid", "medium"))

    def route(self, task_class: str) -> Route:
        row = self.table.get(task_class)
        if not row:
            return self.default
        return Route(tier=row.get("tier", self.default.tier),
                     effort=row.get("effort", self.default.effort))

    def spec_for(self, route: Route) -> ModelSpec:
        spec = self.tiers.get(route.tier)
        if spec is None:
            raise ValueError(
                f"route tier {route.tier!r} is not configured "
                f"(configured: {sorted(self.tiers)})")
        return spec
