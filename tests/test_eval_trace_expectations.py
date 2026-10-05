"""`expect_trace` on loop scenarios asserts exact trace-metric values."""

from harness.evals import run_scenario


def _scenario(expect_trace):
    return {
        "id": "trace-expectation",
        "kind": "loop",
        "role": "worker",
        "max_steps": 4,
        "task": "list and finish",
        "script": [
            {"tool": "bash", "args": {"command": "ls"}},
            {"tool": "list_files", "args": {}},
            {"tool": "task_complete", "args": {"report": "done"}},
        ],
        "expect_stop": "complete",
        "expect_trace": expect_trace,
    }


def test_matching_trace_expectations_pass():
    result = run_scenario(_scenario({"tool_contract_breaks": 1,
                                     "completed_tasks": 1,
                                     "tool_calls_per_completed_task": 2.0}))
    assert result.passed, result.observed


def test_mismatched_trace_value_fails_and_names_the_metric():
    result = run_scenario(_scenario({"tool_contract_breaks": 0}))
    assert not result.passed
    assert any("tool_contract_breaks=1, expected 0" in p for p in result.observed)


def test_unknown_metric_name_fails_rather_than_passing_vacuously():
    result = run_scenario(_scenario({"no_such_metric": 1}))
    assert not result.passed
    assert any("unknown metric 'no_such_metric'" in p for p in result.observed)
