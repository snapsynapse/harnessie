from pathlib import Path

from harness.cli import main
from harness.evals import run_eval_suite


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_eval_suite_passes():
    scorecard = run_eval_suite(ROOT, ROOT / "evals" / "baseline.yaml")
    assert scorecard["total"] == 10
    assert scorecard["passed"] == scorecard["total"]


def test_cli_eval_reports_scorecard(capsys):
    code = main(["--root", str(ROOT), "eval", "evals/baseline.yaml"])
    out = capsys.readouterr().out
    assert code == 0
    assert "eval scorecard: 10/10 passed" in out
    assert "recovery_second_attempt_passes" in out


def test_cli_live_eval_skips_without_opt_in(capsys, monkeypatch):
    monkeypatch.delenv("HARNESSIE_LIVE", raising=False)

    code = main(["--root", str(ROOT), "eval", "--live"])
    out = capsys.readouterr().out

    assert code == 0
    assert "live scorecard: 0/0 passed" in out
    assert "SKIP anthropic" in out
