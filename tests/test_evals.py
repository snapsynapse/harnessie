from pathlib import Path

import yaml

from harness.cli import main
from harness.evals import _check_events_absent, run_eval_suite


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_eval_suite_passes():
    scorecard = run_eval_suite(ROOT, ROOT / "evals" / "baseline.yaml")
    assert scorecard["total"] == 10
    assert scorecard["passed"] == scorecard["total"]


def test_redteam_eval_suite_passes():
    scorecard = run_eval_suite(ROOT, ROOT / "evals" / "redteam.yaml")
    assert scorecard["total"] == 3
    assert scorecard["passed"] == scorecard["total"]


def test_parallel_timing_eval_separates_parallel_from_sequential_execution():
    suite = yaml.safe_load(
        (ROOT / "evals" / "operability.yaml").read_text(encoding="utf-8"))
    scenario = next(
        item for item in suite["scenarios"]
        if item["id"] == "parallel_phases_use_independent_workspaces")

    delay = float(scenario["mock_delay_seconds"])
    threshold = float(scenario["expect_elapsed_lt"])
    assert delay < threshold
    assert threshold <= (2 * delay) - 0.10


def test_events_absent_check_can_fail(tmp_path):
    # The canary assertion must be falsifiable: a planted canary in the
    # events log is reported, an absent one is not, and value fragments in
    # the problem message are truncated.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text(
        '{"kind": "tool_result", "content": "key AKIACANARY0EVALTEST0 found"}\n',
        encoding="utf-8")

    problems: list[str] = []
    scenario = {"expect_events_absent": ["AKIACANARY0EVALTEST0", "ghp_notpresent"]}
    _check_events_absent(scenario, run_dir, problems)

    assert len(problems) == 1
    assert "leaked into events log" in problems[0]
    assert "AKIACANARY0EVALTEST0" not in problems[0]  # message itself truncates


def test_events_absent_check_passes_clean_log(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text(
        '{"kind": "refusal", "detail": "kinds: aws_access_key"}\n', encoding="utf-8")

    problems: list[str] = []
    _check_events_absent(
        {"expect_events_absent": ["AKIACANARY0EVALTEST0"]}, run_dir, problems)

    assert problems == []


def test_cli_eval_reports_scorecard(capsys):
    code = main(["--root", str(ROOT), "eval", "evals/baseline.yaml"])
    out = capsys.readouterr().out
    assert code == 0
    assert "eval scorecard: 10/10 passed" in out
    assert "recovery_second_attempt_passes" in out


def test_cli_eval_refuses_empty_suite_discovery(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "eval"])
    captured = capsys.readouterr()

    assert code == 2
    assert "no eval suites found" in captured.err
    assert "0/0 passed" not in captured.out


def test_cli_live_eval_skips_without_opt_in(capsys, monkeypatch):
    monkeypatch.delenv("HARNESSIE_LIVE", raising=False)

    code = main(["--root", str(ROOT), "eval", "--live"])
    out = capsys.readouterr().out

    assert code == 0
    assert "live scorecard: 0/0 passed" in out
    assert "SKIP anthropic" in out
