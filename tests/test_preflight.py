from harness.models.base import ModelSpec
from harness.preflight import build_preview, format_preview


def _tier(name, provider, out_rate=0.0):
    return ModelSpec(name=name, provider=provider, model_id=f"{name}-model",
                     cost_per_mtok_out=out_rate)


MOCK_TIERS = {"local": _tier("local", "mock")}
LIVE_TIERS = {
    "cheap": _tier("cheap", "anthropic", out_rate=5.0),
    "frontier": _tier("frontier", "anthropic", out_rate=25.0),
    "local": _tier("local", "openai-compat", out_rate=0.0),
}
CEILING = {"max_usd": 10.0, "max_tokens": 2_000_000}


def test_mock_run_never_refuses_even_without_ceiling():
    preview = build_preview(MOCK_TIERS, {})
    assert preview.live is False
    assert preview.refuse_reason is None
    assert "MOCK" in format_preview(preview)


def test_live_run_without_ceiling_refuses():
    preview = build_preview(LIVE_TIERS, {})
    assert preview.live is True
    assert preview.has_ceiling is False
    reason = preview.refuse_reason
    assert reason is not None
    assert "no budget ceiling" in reason
    assert "budget:" in reason  # points at the fix
    assert "NONE SET" in format_preview(preview)


def test_live_run_with_ceiling_does_not_refuse():
    preview = build_preview(LIVE_TIERS, CEILING)
    assert preview.live is True
    assert preview.has_ceiling is True
    assert preview.refuse_reason is None


def test_priciest_tier_and_worst_case_math():
    preview = build_preview(LIVE_TIERS, CEILING)
    # frontier is the priciest output rate in the fixture
    assert preview.priciest_tier == "frontier"
    assert preview.priciest_out_rate == 25.0
    # 2,000,000 tokens * $25/Mtok = $50 implied by the token ceiling
    assert preview.token_implied_usd == 50.0
    text = format_preview(preview)
    assert "$50.00" in text
    assert "$10.00" in text
    # token ceiling implies more than the USD cap -> USD cap binds first
    assert "USD cap" in text


def test_token_cap_binds_when_cheaper_than_usd_ceiling():
    preview = build_preview(LIVE_TIERS, {"max_usd": 1000.0, "max_tokens": 100_000})
    # 100,000 tokens * $25/Mtok = $2.50, well under the $1000 USD cap
    assert preview.token_implied_usd == 2.5
    assert "token cap" in format_preview(preview)


def test_unknown_provider_is_treated_as_live_fail_safe():
    # A provider not in the zero-cost set is assumed billable, so a new
    # adapter cannot slip past the ceiling refusal.
    tiers = {"local": _tier("local", "some-new-provider")}
    preview = build_preview(tiers, {})
    assert preview.live is True
    assert preview.refuse_reason is not None
