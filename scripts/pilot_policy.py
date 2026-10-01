"""Frozen, offline accounting policy for the Claude Code pilot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.pilot_contract import CLAUDE_MODEL, PilotRefusal


HAIKU_MODEL = "claude-haiku-4-5-20251001"
EXACT_MODEL_POLICY_ID = "exact-model-only/v1"
HAIKU_OVERHEAD_POLICY_ID = "claude-max-haiku-overhead/v1"
HAIKU_CONTEXT_POLICY_ID = "claude-max-haiku-context/v2"
CONTEXT_HAIKU_INPUT_PER_CALL = 96_000
CONTEXT_HAIKU_OUTPUT_PER_CALL = 256
CONTEXT_HAIKU_INPUT_PER_RUN = 256_000
CONTEXT_HAIKU_OUTPUT_PER_RUN = 2_048
CONTEXT_TOTAL_TOKENS_PER_RUN = 800_000


@dataclass(frozen=True)
class PilotPolicy:
    """One of the fixed policies, never a caller-supplied model allowlist."""

    id: str = EXACT_MODEL_POLICY_ID
    permit_unclassified_haiku: bool = False
    haiku_input_with_cache_limit: int = 0
    haiku_output_limit: int = 0

    def __post_init__(self) -> None:
        if (type(self.id) is not str or type(self.permit_unclassified_haiku) is not bool
                or type(self.haiku_input_with_cache_limit) is not int
                or type(self.haiku_output_limit) is not int):
            raise PilotRefusal("invalid_pilot_policy")
        exact = (EXACT_MODEL_POLICY_ID, False, 0, 0)
        overhead = (HAIKU_OVERHEAD_POLICY_ID, True, 4096, 256)
        context = (
            HAIKU_CONTEXT_POLICY_ID,
            True,
            CONTEXT_HAIKU_INPUT_PER_CALL,
            CONTEXT_HAIKU_OUTPUT_PER_CALL,
        )
        values = (self.id, self.permit_unclassified_haiku,
                  self.haiku_input_with_cache_limit, self.haiku_output_limit)
        if values not in {exact, overhead, context}:
            raise PilotRefusal("invalid_pilot_policy")

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "permitted_additional_model_ids": [HAIKU_MODEL] if self.permit_unclassified_haiku else [],
            "additional_model_role": "unclassified" if self.permit_unclassified_haiku else None,
            "bounds": self.bounds,
        }

    @property
    def bounds(self) -> dict[str, int]:
        if not self.permit_unclassified_haiku:
            return {}
        return {
            "haiku_input_with_cache_limit": self.haiku_input_with_cache_limit,
            "haiku_output_limit": self.haiku_output_limit,
        }

    def evaluate(self, requested_model: str, raw_usage: dict[str, Any],
                 normalized_usage: dict[str, dict[str, int | None]]) -> "PolicyDecision":
        models = set(raw_usage)
        for model in models:
            usage = normalized_usage.get(model)
            if not isinstance(usage, dict) or any(
                    type(usage.get(field)) is not int or usage[field] < 0
                    for field in ("input_tokens", "output_tokens",
                                  "cache_creation_input_tokens", "cache_read_input_tokens")):
                return PolicyDecision("refused_usage", "additional_model_usage_incomplete")
        if models == {requested_model}:
            if self.permit_unclassified_haiku:
                metadata = raw_usage.get(CLAUDE_MODEL)
                if not isinstance(metadata, dict) or metadata.get("provider") != "firstParty":
                    return PolicyDecision("refused_provider", "additional_model_provider_unapproved")
            return PolicyDecision("exact_model", None)
        if not self.permit_unclassified_haiku:
            return PolicyDecision("refused_extra_model", "additional_model_usage_unapproved")
        if requested_model != CLAUDE_MODEL or models != {CLAUDE_MODEL, HAIKU_MODEL}:
            return PolicyDecision("refused_model_identity", "additional_model_usage_unapproved")
        for model in (CLAUDE_MODEL, HAIKU_MODEL):
            metadata = raw_usage.get(model)
            if not isinstance(metadata, dict) or metadata.get("provider") != "firstParty":
                return PolicyDecision("refused_provider", "additional_model_provider_unapproved")
        haiku = normalized_usage.get(HAIKU_MODEL)
        raw_haiku = raw_usage.get(HAIKU_MODEL)
        if not isinstance(haiku, dict) or not isinstance(raw_haiku, dict):
            return PolicyDecision("refused_usage", "additional_model_usage_incomplete")
        counts = tuple(haiku.get(key) for key in (
            "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        if any(type(value) is not int or value < 0 for value in counts):
            return PolicyDecision("refused_usage", "additional_model_usage_incomplete")
        if type(raw_haiku.get("webSearchRequests")) is not int or raw_haiku["webSearchRequests"] != 0:
            return PolicyDecision("refused_operational_use", "additional_model_operational_use")
        input_with_cache = counts[0] + counts[2] + counts[3]
        if input_with_cache > self.haiku_input_with_cache_limit or counts[1] > self.haiku_output_limit:
            return PolicyDecision("refused_bound", "additional_model_usage_bound_exceeded")
        return PolicyDecision("unclassified", None)


@dataclass(frozen=True)
class PolicyDecision:
    disposition: str
    failure: str | None


EXACT_MODEL_ONLY = PilotPolicy()
CLAUDE_MAX_HAIKU_OVERHEAD = PilotPolicy(
    id=HAIKU_OVERHEAD_POLICY_ID,
    permit_unclassified_haiku=True,
    haiku_input_with_cache_limit=4096,
    haiku_output_limit=256,
)
CLAUDE_MAX_HAIKU_CONTEXT = PilotPolicy(
    id=HAIKU_CONTEXT_POLICY_ID,
    permit_unclassified_haiku=True,
    haiku_input_with_cache_limit=CONTEXT_HAIKU_INPUT_PER_CALL,
    haiku_output_limit=CONTEXT_HAIKU_OUTPUT_PER_CALL,
)
