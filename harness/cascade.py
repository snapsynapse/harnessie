"""Cascade routing policy: declared, containment-aware escalation.

The 0.7 sovereignty layer (ROADMAP 0.7.0, adopted via decisions/AIDR-0004).
A workflow phase may reference a named cascade policy instead of a fixed
task_class tier. A policy declares its tier ladder, which failure reasons
climb it, a maximum climb, and what happens on exhaustion (reduce scope or
defer — never silent). A contained policy's ladder never leaves the
unexposed tier set, so data the boundary cannot classify never egresses to
an exposed provider: containment by never-egress, not by filtering.

Work classes named under ``reserved:`` never reach any model at any tier —
the human-only Arbitration rule generalized and enforced as config.

Phases that do not opt in are untouched: the default Route.escalate()
ladder behaves byte-identically to 0.6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Failure reasons that may climb a ladder. Availability failures and provider
# refusals deliberately do NOT appear here as climb triggers in contained
# ladders' spirit: up-tiering on refusal is a containment leak; those move
# sideways (same tier, different provider) — see ROADMAP 0.7.0.
ESCALATION_REASONS = ("gate_fail", "schema_fail", "refusal", "tool_contract")

# Reasons that move sideways (same tier, different provider via the tier's
# configured fallbacks) before any ladder is consulted. Availability never
# climbs a ladder at all; a refusal may climb only when a policy names it in
# escalate_on, and a contained policy may never do so.
SIDEWAYS_REASONS = ("refusal", "availability")

ON_EXHAUST = ("reduce_scope", "defer")

# Tiers that never leave operator control: on-box inference and any
# controlled OpenAI-compatible endpoint admitted to the sovereign slot.
CONTAINED_TIERS = ("local", "sovereign")


@dataclass(frozen=True)
class ClimbDecision:
    action: str            # "climb" | "hold" | "exhausted"
    tier: str | None       # target tier when action == "climb"
    reason: str            # plain-language why, for routing_trace


@dataclass(frozen=True)
class CascadePolicy:
    name: str
    ladder: tuple[str, ...]
    escalate_on: tuple[str, ...] = ("gate_fail",)
    max_climb: int = -1                    # -1: ladder length bounds it
    on_exhaust: str = "defer"
    data_classes: tuple[str, ...] = ()
    contained: bool = False

    def __post_init__(self) -> None:
        if not self.ladder:
            raise ValueError(f"cascade policy {self.name!r}: ladder is empty")
        if len(set(self.ladder)) != len(self.ladder):
            raise ValueError(
                f"cascade policy {self.name!r}: ladder repeats a tier")
        if not self.escalate_on:
            raise ValueError(
                f"cascade policy {self.name!r}: escalate_on is empty")
        unknown = [r for r in self.escalate_on if r not in ESCALATION_REASONS]
        if unknown:
            raise ValueError(
                f"cascade policy {self.name!r}: unknown escalate_on "
                f"{unknown} (known: {list(ESCALATION_REASONS)})")
        if self.on_exhaust not in ON_EXHAUST:
            raise ValueError(
                f"cascade policy {self.name!r}: on_exhaust "
                f"{self.on_exhaust!r} (known: {list(ON_EXHAUST)}); "
                "exhaustion is never silent")
        max_valid = len(self.ladder) - 1
        if self.max_climb < -1 or self.max_climb > max_valid:
            raise ValueError(
                f"cascade policy {self.name!r}: max_climb {self.max_climb} "
                f"out of range (ladder allows at most {max_valid})")
        if self.contained:
            exposed = [t for t in self.ladder if t not in CONTAINED_TIERS]
            if exposed:
                raise ValueError(
                    f"cascade policy {self.name!r}: contained ladder names "
                    f"exposed tier(s) {exposed}; contained ladders may only "
                    f"use {list(CONTAINED_TIERS)}")
            if "refusal" in self.escalate_on:
                raise ValueError(
                    f"cascade policy {self.name!r}: a contained policy may "
                    "not climb on refusal (up-tiering on refusal is a "
                    "containment leak); refusals move sideways or hold")

    @property
    def climb_ceiling(self) -> int:
        return len(self.ladder) - 1 if self.max_climb == -1 else self.max_climb

    def next_tier(self, current_tier: str, climbs_used: int,
                  reason: str) -> ClimbDecision:
        """One escalation decision. Fails closed: a tier the policy does not
        know is a config/runtime mismatch, not a guess."""
        if current_tier not in self.ladder:
            raise ValueError(
                f"cascade policy {self.name!r}: current tier "
                f"{current_tier!r} is not on ladder {list(self.ladder)}")
        if reason not in self.escalate_on:
            return ClimbDecision(
                "hold", None,
                f"{reason} does not climb this ladder "
                f"(climbs on: {', '.join(self.escalate_on)})")
        idx = self.ladder.index(current_tier)
        if idx >= len(self.ladder) - 1:
            return ClimbDecision(
                "exhausted", None,
                f"top of ladder at {current_tier!r}; on_exhaust: "
                f"{self.on_exhaust}")
        if climbs_used >= self.climb_ceiling:
            return ClimbDecision(
                "exhausted", None,
                f"max_climb {self.climb_ceiling} reached; on_exhaust: "
                f"{self.on_exhaust}")
        return ClimbDecision(
            "climb", self.ladder[idx + 1],
            f"{reason} escalates {current_tier} -> {self.ladder[idx + 1]}")


@dataclass
class CascadeConfig:
    policies: dict[str, CascadePolicy] = field(default_factory=dict)
    reserved: tuple[str, ...] = ()

    def policy(self, name: str) -> CascadePolicy:
        try:
            return self.policies[name]
        except KeyError:
            raise ValueError(
                f"unknown cascade policy {name!r} "
                f"(configured: {sorted(self.policies)})") from None

    def is_reserved(self, work_class: str) -> bool:
        return work_class in self.reserved


_POLICY_KEYS = {"ladder", "escalate_on", "max_climb", "on_exhaust",
                "data_classes", "contained"}


def load_cascade_config(path: Path | str) -> CascadeConfig:
    """Load config/cascade.yaml. A missing file is an empty config (the
    feature is opt-in); a malformed one fails closed with the field named."""
    path = Path(path)
    if not path.exists():
        return CascadeConfig()
    import yaml
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    unknown_top = set(raw) - {"policies", "reserved"}
    if unknown_top:
        raise ValueError(
            f"{path}: unknown top-level key(s) {sorted(unknown_top)}")

    reserved = raw.get("reserved") or []
    if not isinstance(reserved, list) or not all(isinstance(r, str) for r in reserved):
        raise ValueError(f"{path}: reserved must be a list of work-class names")

    policies: dict[str, CascadePolicy] = {}
    for name, body in (raw.get("policies") or {}).items():
        if not isinstance(body, dict):
            raise ValueError(f"{path}: policy {name!r} must be a mapping")
        unknown = set(body) - _POLICY_KEYS
        if unknown:
            raise ValueError(
                f"{path}: policy {name!r} has unknown key(s) "
                f"{sorted(unknown)} (known: {sorted(_POLICY_KEYS)})")
        if "ladder" not in body:
            raise ValueError(f"{path}: policy {name!r} is missing ladder")
        policies[name] = CascadePolicy(
            name=name,
            ladder=tuple(body["ladder"]),
            escalate_on=tuple(body.get("escalate_on", ("gate_fail",))),
            max_climb=int(body.get("max_climb", -1)),
            on_exhaust=str(body.get("on_exhaust", "defer")),
            data_classes=tuple(body.get("data_classes", ())),
            contained=bool(body.get("contained", False)),
        )
    return CascadeConfig(policies=policies, reserved=tuple(reserved))


def validate_against_tiers(config: CascadeConfig,
                           tiers: dict[str, object]) -> None:
    """Every ladder tier must be a configured brain. Run at startup so a
    policy naming an absent tier refuses the run before any work starts."""
    for policy in config.policies.values():
        missing = [t for t in policy.ladder if t not in tiers]
        if missing:
            raise ValueError(
                f"cascade policy {policy.name!r} names unconfigured "
                f"tier(s) {missing} (configured: {sorted(tiers)})")
