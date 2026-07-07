import os
from pathlib import Path

from harness.live_scorecard import discover_live_targets, format_live_scorecard


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
