import os
from pathlib import Path

import pytest

from harness.live_scorecard import format_live_scorecard, run_live_scorecard


ROOT = Path(__file__).resolve().parents[2]


def test_live_provider_scorecard_opt_in():
    if os.environ.get("HARNESSIE_LIVE") != "1":
        pytest.skip(
            "live providers are opt-in; set HARNESSIE_LIVE=1 and provider env vars"
        )

    scorecard = run_live_scorecard(ROOT)
    runnable = [r for r in scorecard["results"] if r.status != "skipped"]
    if not runnable:
        pytest.skip(format_live_scorecard(scorecard))

    assert scorecard["passed"] == scorecard["total"], format_live_scorecard(scorecard)
