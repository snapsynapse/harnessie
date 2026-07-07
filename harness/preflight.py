"""Pre-run cost preview and the ceiling-less-live-run refusal.

The 0.6 safety promise for a first-time operator: a run that can spend real
money never starts silently. Before `run`/`resume` execute, the harness states
whether the configured brains are live (real providers) or mock (zero-dollar),
shows the budget ceilings and a worst-case dollar figure, and refuses to start
a live run when no ceiling is set. A mock run is always free and never refused.

Everything here is pure over the already-parsed config pieces so it is trivially
testable and never itself performs I/O or a provider call.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models.base import ModelSpec

# Providers that can bill real money. Anything not in the zero-cost set is
# treated as live, so a new provider fails safe (assumed billable) rather than
# slipping past the ceiling check.
ZERO_COST_PROVIDERS = frozenset({"mock"})


@dataclass(frozen=True)
class CostPreview:
    live: bool                 # any configured tier can bill real money
    has_ceiling: bool          # an explicit budget section set positive ceilings
    max_usd: float
    max_tokens: int
    priciest_tier: str         # tier name with the highest output rate
    priciest_out_rate: float   # USD per Mtok out for that tier
    token_implied_usd: float   # token ceiling spent entirely at that rate

    @property
    def refuse_reason(self) -> str | None:
        """Non-None means: do not start. Only live, ceiling-less runs refuse."""
        if self.live and not self.has_ceiling:
            return (
                "refusing to start a live run with no budget ceiling set.\n"
                "a run with real providers must declare a spend ceiling first.\n"
                "add a budget section to config/models.yaml, for example:\n"
                "  budget:\n"
                "    max_usd: 5.0\n"
                "    max_tokens: 1000000"
            )
        return None


def build_preview(tiers: dict[str, ModelSpec], budget_cfg: dict) -> CostPreview:
    """Compute the preview from parsed tiers and the raw budget section.

    `budget_cfg` is the config's `budget:` mapping, empty when absent. An empty
    mapping means no ceiling was set; a present one is already validated
    positive at load time, so its truthiness is the has_ceiling signal.
    """
    live = any(spec.provider not in ZERO_COST_PROVIDERS for spec in tiers.values())
    has_ceiling = bool(budget_cfg)
    max_usd = float(budget_cfg.get("max_usd", 0.0) or 0.0)
    max_tokens = int(budget_cfg.get("max_tokens", 0) or 0)

    priciest_tier, priciest_out_rate = "", 0.0
    for name, spec in tiers.items():
        if spec.cost_per_mtok_out > priciest_out_rate:
            priciest_tier, priciest_out_rate = name, spec.cost_per_mtok_out

    token_implied_usd = max_tokens * priciest_out_rate / 1_000_000
    return CostPreview(
        live=live,
        has_ceiling=has_ceiling,
        max_usd=max_usd,
        max_tokens=max_tokens,
        priciest_tier=priciest_tier,
        priciest_out_rate=priciest_out_rate,
        token_implied_usd=token_implied_usd,
    )


def format_preview(preview: CostPreview) -> str:
    """Human-readable preview block printed before a run starts."""
    lines = ["Pre-run cost preview"]
    if not preview.live:
        lines.append("  provider mode: MOCK (zero-dollar, nothing is billed)")
        return "\n".join(lines)

    lines.append("  provider mode: LIVE (real providers can bill money)")
    if not preview.has_ceiling:
        lines.append("  budget ceilings: NONE SET")
        return "\n".join(lines)

    lines.append(
        f"  budget ceilings: ${preview.max_usd:.4f} max, "
        f"{preview.max_tokens:,} tokens max"
    )
    if preview.priciest_out_rate > 0:
        # Which ceiling binds first is the useful signal: if the token budget
        # spent at the priciest output rate would exceed the USD cap, dollars
        # bind; otherwise tokens do.
        binds = "USD cap" if preview.token_implied_usd >= preview.max_usd \
            else "token cap"
        lines.append(
            f"  worst case: {preview.max_tokens:,} tokens at the priciest tier "
            f"({preview.priciest_tier} @ ${preview.priciest_out_rate:.2f}/Mtok out) "
            f"implies up to ${preview.token_implied_usd:.2f}; "
            f"spend is capped at ${preview.max_usd:.2f} ({binds} binds first)"
        )
    else:
        lines.append(
            f"  worst case: capped at ${preview.max_usd:.2f} "
            "(no per-tier output rates configured)"
        )
    return "\n".join(lines)


__all__ = ["CostPreview", "build_preview", "format_preview", "ZERO_COST_PROVIDERS"]
