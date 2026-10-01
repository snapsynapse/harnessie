from __future__ import annotations

import pytest

from scripts.pilot_contract import CLAUDE_MODEL, PilotRefusal
from scripts.pilot_policy import (
    CLAUDE_MAX_HAIKU_CONTEXT,
    CLAUDE_MAX_HAIKU_OVERHEAD,
    CONTEXT_HAIKU_INPUT_PER_CALL,
    CONTEXT_HAIKU_OUTPUT_PER_CALL,
    EXACT_MODEL_ONLY,
    HAIKU_CONTEXT_POLICY_ID,
    HAIKU_MODEL,
    HAIKU_OVERHEAD_POLICY_ID,
    PilotPolicy,
)


def _usage(input_tokens=2, output_tokens=3, cache_creation=0, cache_read=0):
    return {"input_tokens": input_tokens, "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation, "cache_read_input_tokens": cache_read}


def _raw(*, provider="firstParty", web_search=0):
    return {"provider": provider, "webSearchRequests": web_search}


def test_frozen_policy_constants_and_no_general_allowlist():
    assert EXACT_MODEL_ONLY.as_dict()["id"] == "exact-model-only/v1"
    assert CLAUDE_MAX_HAIKU_OVERHEAD.as_dict()["id"] == HAIKU_OVERHEAD_POLICY_ID
    assert CLAUDE_MAX_HAIKU_CONTEXT.as_dict() == {
        "id": HAIKU_CONTEXT_POLICY_ID,
        "permitted_additional_model_ids": [HAIKU_MODEL],
        "additional_model_role": "unclassified",
        "bounds": {
            "haiku_input_with_cache_limit": CONTEXT_HAIKU_INPUT_PER_CALL,
            "haiku_output_limit": CONTEXT_HAIKU_OUTPUT_PER_CALL,
        },
    }
    with pytest.raises(PilotRefusal, match="invalid_pilot_policy"):
        PilotPolicy(id="anything", permit_unclassified_haiku=True,
                    haiku_input_with_cache_limit=999999, haiku_output_limit=1)
    with pytest.raises(PilotRefusal, match="invalid_pilot_policy"):
        PilotPolicy(id="exact-model-only/v1", permit_unclassified_haiku=1,
                    haiku_input_with_cache_limit=0, haiku_output_limit=0)


def test_default_refuses_extra_but_opt_in_accepts_only_bounded_unclassified_haiku():
    raw = {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw()}
    normalized = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(989, 16, 0, 0)}
    assert EXACT_MODEL_ONLY.evaluate(CLAUDE_MODEL, raw, normalized).failure == "additional_model_usage_unapproved"
    accepted = CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, raw, normalized)
    assert accepted.failure is None and accepted.disposition == "unclassified"


def test_opt_in_rejects_alias_third_party_operational_and_overage():
    normal = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(1, 1, 0, 0)}
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), "claude-haiku-4-5": _raw()}, normal).failure == "additional_model_usage_incomplete"
    alias_normal = {CLAUDE_MODEL: _usage(), "claude-haiku-4-5": _usage(1, 1, 0, 0)}
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), "claude-haiku-4-5": _raw()}, alias_normal).failure == "additional_model_usage_unapproved"
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw(provider="other")}, normal).failure == "additional_model_provider_unapproved"
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw(web_search=1)}, normal).failure == "additional_model_operational_use"
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw()}, {CLAUDE_MODEL: _usage()}).failure is None
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(provider="other")}, {CLAUDE_MODEL: _usage()}).failure == "additional_model_provider_unapproved"
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw()}, {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(1, None, 0, 0)}).failure == "additional_model_usage_incomplete"
    at_limit = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(1, 256, 4095, 0)}
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw()}, at_limit).failure is None
    over = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(1, 256, 4096, 0)}
    assert CLAUDE_MAX_HAIKU_OVERHEAD.evaluate(CLAUDE_MODEL, {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw()}, over).failure == "additional_model_usage_bound_exceeded"


def test_context_policy_accepts_exact_limit_and_refuses_one_token_over():
    raw = {CLAUDE_MODEL: _raw(), HAIKU_MODEL: _raw()}
    exact = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(
        1, CONTEXT_HAIKU_OUTPUT_PER_CALL,
        CONTEXT_HAIKU_INPUT_PER_CALL - 1, 0)}
    assert CLAUDE_MAX_HAIKU_CONTEXT.evaluate(CLAUDE_MODEL, raw, exact).failure is None
    over_input = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(
        1, CONTEXT_HAIKU_OUTPUT_PER_CALL,
        CONTEXT_HAIKU_INPUT_PER_CALL, 0)}
    assert CLAUDE_MAX_HAIKU_CONTEXT.evaluate(
        CLAUDE_MODEL, raw, over_input).failure == "additional_model_usage_bound_exceeded"
    over_output = {CLAUDE_MODEL: _usage(), HAIKU_MODEL: _usage(
        1, CONTEXT_HAIKU_OUTPUT_PER_CALL + 1, 0, 0)}
    assert CLAUDE_MAX_HAIKU_CONTEXT.evaluate(
        CLAUDE_MODEL, raw, over_output).failure == "additional_model_usage_bound_exceeded"


def test_v1_overhead_policy_remains_unchanged():
    assert CLAUDE_MAX_HAIKU_OVERHEAD.bounds == {
        "haiku_input_with_cache_limit": 4096,
        "haiku_output_limit": 256,
    }
