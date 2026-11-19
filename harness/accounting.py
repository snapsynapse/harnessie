"""Accounting integrity: finite amounts and cumulative replay on resume."""

from __future__ import annotations

import json
import math

from .audit import verify_chain_lines


class AccountingError(ValueError):
    """Accounting that cannot be trusted: nonfinite, negative or malformed
    numbers, or recorded usage the harness cannot reconstruct. `remedy`, when
    set, is the operator action that resolves the refusal."""

    def __init__(self, message: str, remedy: str = "") -> None:
        super().__init__(message)
        self.remedy = remedy


def unknown_usage_remedy(tier: str | None) -> str:
    """Operator remedy for a metered turn whose usage the provider did not
    report. Shared by the loop stop and the resume refusal."""
    # A fallback ("mid~alt1") inherits `unmetered` from its tier, so the
    # remedy names the tier the operator edits.
    named = (f"tier {tier.split('~', 1)[0]!r}" if tier
             else "the tier that stopped the run")
    return (
        f"if {named} is genuinely unbilled (a local or self-hosted endpoint), "
        "set `unmetered: true` on it in config/models.yaml (its cost rates "
        "must be 0) and start a new run; otherwise make the provider report "
        "token usage. This run cannot be resumed: its spend is unknowable.")


def finite_amount(value, what: str, integer: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        raise AccountingError(f"{what} must be {'an integer' if integer else 'a number'}")
    if integer:
        finite = True   # Python integers are exact at any size
    else:
        try:
            finite = math.isfinite(value)
        except OverflowError:   # an integer beyond the float range
            finite = False
    if not finite or value < 0:
        raise AccountingError(f"{what} must be finite and non-negative")


_CHARGE_FIELDS = ("usd", "tokens", "usage_known", "unmetered", "spent_usd",
                  "spent_tokens")


def _reject_constant(name: str):
    raise AccountingError(f"nonfinite number {name} in the run journal")


def replay_accounting(lines: list[str]) -> tuple[float, int]:
    """Cumulative spend from a run journal's budget_charge records.

    Fails closed (AccountingError) on a broken hash chain, any malformed or
    nonfinite record, a recorded cumulative total that disagrees with the
    sum of recorded charges, metered usage that was never reported, or model
    turns with no accounting records at all (a journal predating them).
    """
    chain = verify_chain_lines(lines)
    if not chain["ok"]:
        raise AccountingError(
            f"run journal hash chain is broken at lines {chain['breaks']}")
    spent_usd, spent_tokens = 0.0, 0
    charges = turns = 0
    for line in lines:
        event = json.loads(line, parse_constant=_reject_constant)
        kind = event.get("kind")
        if kind == "model_turn":
            turns += 1
        if kind != "budget_charge":
            continue
        charges += 1
        if any(name not in event for name in _CHARGE_FIELDS):
            raise AccountingError("budget_charge record is missing fields")
        finite_amount(event["usd"], "recorded usd")
        finite_amount(event["tokens"], "recorded tokens", integer=True)
        finite_amount(event["spent_usd"], "recorded spent_usd")
        finite_amount(event["spent_tokens"], "recorded spent_tokens", integer=True)
        if not isinstance(event["usage_known"], bool) or not isinstance(
                event["unmetered"], bool):
            raise AccountingError("budget_charge flags must be booleans")
        if not event["usage_known"] and not event["unmetered"]:
            tier = event.get("tier")
            raise AccountingError(
                "run journal records metered usage the provider did not report",
                remedy=unknown_usage_remedy(tier if isinstance(tier, str) else None))
        spent_usd += event["usd"]
        spent_tokens += event["tokens"]
        if (event["spent_tokens"] != spent_tokens
                or not math.isclose(event["spent_usd"], spent_usd,
                                    rel_tol=1e-9, abs_tol=1e-12)):
            raise AccountingError(
                "budget_charge cumulative totals disagree with recorded charges")
    if turns and not charges:
        raise AccountingError(
            "run journal has model turns but no accounting records")
    return spent_usd, spent_tokens
