import os
from pathlib import Path

from harness.live_scorecard import (
    LiveCaseResult,
    bundle_identity,
    discover_live_targets,
    format_live_scorecard,
)
from harness.models.base import ModelSpec


ROOT = Path(__file__).resolve().parents[1]


def test_live_targets_skip_without_opt_in(monkeypatch):
    monkeypatch.delenv("HARNESSIE_LIVE", raising=False)
    targets = discover_live_targets(ROOT, env=os.environ)

    assert targets
    assert {t.status for t in targets} == {"skipped"}
    rendered = format_live_scorecard({"passed": 0, "total": 0, "results": targets})
    assert "SKIP anthropic" in rendered
    assert "set HARNESSIE_LIVE=1" in rendered


def test_live_anthropic_skip_names_missing_key(monkeypatch):
    monkeypatch.setenv("HARNESSIE_LIVE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    targets = discover_live_targets(ROOT, env=os.environ)

    anthropic = next(t for t in targets if t.id == "anthropic")
    assert anthropic.status == "skipped"
    assert "ANTHROPIC_API_KEY" in anthropic.notes


def test_live_openai_responses_target_from_environment(monkeypatch):
    monkeypatch.setenv("HARNESSIE_LIVE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "configured-not-sent-during-discovery")
    monkeypatch.setenv("HARNESSIE_OPENAI_RESPONSES_MODEL", "test-model")
    targets = discover_live_targets(ROOT, env=os.environ)

    target = next(t for t in targets if t.id == "openai_responses")
    assert target.status == "ready"
    assert target.spec is not None
    assert target.spec.provider == "openai-responses"
    assert target.spec.model_id == "test-model"
    assert target.spec.base_url == "https://api.openai.com/v1"


def test_live_openai_responses_skip_names_missing_key(monkeypatch):
    monkeypatch.setenv("HARNESSIE_LIVE", "1")
    monkeypatch.setenv("HARNESSIE_OPENAI_RESPONSES_MODEL", "test-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    targets = discover_live_targets(ROOT, env=os.environ)

    target = next(t for t in targets if t.id == "openai_responses")
    assert target.status == "skipped"
    assert "OPENAI_API_KEY" in target.notes


def test_openai_responses_bundle_records_high_protocol_smoke():
    identity = bundle_identity(ROOT, ModelSpec(
        name="mid", provider="openai-responses", model_id="test",
        base_url="https://api.openai.com/v1"))

    assert identity.sampling == "effort=low; protocol-smoke=high"


def test_live_format_does_not_report_unknown_cost_as_zero():
    rendered = format_live_scorecard({
        "passed": 1,
        "total": 1,
        "results": [LiveCaseResult(
            id="smoke", provider="openai-responses", status="passed",
            passed=True, expected="ok", observed="ok", tokens=42,
            cost_usd=None)],
    })

    assert "tokens=42" in rendered
    assert "cost=$" not in rendered
