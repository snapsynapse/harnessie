"""Standalone `harnessie verify` (AIDR-0006): exit contract and report shape.

Verifier-agent paths use MockModel through the real AgentLoop; deterministic
checks run through the real sandbox wrapper.
"""

import json

import pytest

from harness import sandbox

from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.verify import Check
needs_sandbox = pytest.mark.skipif(
    not sandbox.available(),
    reason="no OS sandbox backend: check-executing paths report cannot-verify "
           "(exit 2) by design; test_no_backend_checks_fail_closed covers that")

from harness.verify_standalone import (
    EXIT_CANNOT_VERIFY,
    EXIT_FAILED,
    EXIT_VERIFIED,
    VerifyRequest,
    run_standalone_verify,
)


def make_request(tmp_path, criteria="- out.txt exists", **kw):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    crit = tmp_path / "criteria.md"
    crit.write_text(criteria, encoding="utf-8")
    kw.setdefault("report_dir", tmp_path / "report")
    return VerifyRequest(workspace=ws, criteria_path=crit, **kw)


def patch_model(monkeypatch, script):
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    monkeypatch.setattr("harness.verify_standalone.build_model",
                        lambda spec: model)
    return model


def write_models_yaml(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        "tiers:\n"
        "  mid:\n"
        "    provider: mock\n"
        "    model_id: mock\n",
        encoding="utf-8")
    return p


def verdict_turn(passed, reasons="checked"):
    report = "findings...\n" + json.dumps({"passed": passed, "reasons": reasons})
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="c1", name="task_complete",
                                              arguments={"report": report})])


# -- infrastructure refusals (exit 2, nothing billed, nothing run) -----------

def test_missing_workspace_cannot_verify(tmp_path):
    crit = tmp_path / "criteria.md"
    crit.write_text("- anything", encoding="utf-8")
    req = VerifyRequest(workspace=tmp_path / "absent", criteria_path=crit)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY
    assert out.report_path is None


def test_missing_criteria_cannot_verify(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    req = VerifyRequest(workspace=ws, criteria_path=tmp_path / "absent.md")
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY


def test_missing_models_config_cannot_verify(tmp_path):
    req = make_request(tmp_path, models_path=tmp_path / "absent.yaml")
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY
    assert "models config" in out.summary


# -- deterministic-check layer ------------------------------------------------

@needs_sandbox
def test_failing_check_fails_without_consulting_verifier(tmp_path):
    req = make_request(tmp_path, checks=[Check(name="lie", command="false")],
                       no_verifier=True)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_FAILED
    report = out.report_path.read_text(encoding="utf-8")
    assert "FAILED" in report
    assert "[FAIL] lie" in report


@needs_sandbox
def test_passing_checks_no_verifier_verifies(tmp_path):
    req = make_request(tmp_path, checks=[Check(name="truth", command="true")],
                       no_verifier=True)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_VERIFIED
    report = out.report_path.read_text(encoding="utf-8")
    assert "[PASS] truth" in report
    assert "criteria_sha256" in report


def test_no_verifier_and_no_checks_fails_closed(tmp_path):
    req = make_request(tmp_path, no_verifier=True)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY


# -- verifier-agent layer -----------------------------------------------------

def test_verifier_pass_verdict_exits_zero(tmp_path, monkeypatch):
    (tmp_path / "ws").mkdir()
    patch_model(monkeypatch, [verdict_turn(True)])
    req = make_request(tmp_path, models_path=write_models_yaml(tmp_path))
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_VERIFIED
    report = out.report_path.read_text(encoding="utf-8")
    assert "Verdict: PASS" in report


def test_verifier_fail_verdict_exits_one(tmp_path, monkeypatch):
    patch_model(monkeypatch, [verdict_turn(False, "claim refuted")])
    req = make_request(tmp_path, models_path=write_models_yaml(tmp_path))
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_FAILED
    assert "claim refuted" in out.report_path.read_text(encoding="utf-8")


def test_verifier_without_verdict_object_fails_closed(tmp_path, monkeypatch):
    turn = AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="c1", name="task_complete",
                                              arguments={"report": "looks fine!"})])
    patch_model(monkeypatch, [turn])
    req = make_request(tmp_path, models_path=write_models_yaml(tmp_path))
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_FAILED   # parse_verdict fails closed


def test_verifier_loop_stop_is_cannot_verify(tmp_path, monkeypatch):
    # Script exhausts into plain no-tool turns -> loop stops "no_action":
    # infrastructure produced no verdict, so neither pass nor fail is earned.
    patch_model(monkeypatch, [])
    req = make_request(tmp_path, models_path=write_models_yaml(tmp_path))
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY
    assert "without a verdict" in out.report_path.read_text(encoding="utf-8")


def test_verifier_can_read_workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "out.txt").write_text("hello", encoding="utf-8")
    read = AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id="c1", name="read_file",
                                              arguments={"path": "out.txt"})])
    model = patch_model(monkeypatch, [read, verdict_turn(True)])
    req = make_request(tmp_path, models_path=write_models_yaml(tmp_path))
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_VERIFIED
    assert len(model.calls) == 2


def test_report_dir_must_not_be_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    crit = tmp_path / "criteria.md"
    crit.write_text("- x", encoding="utf-8")
    req = VerifyRequest(workspace=ws, criteria_path=crit, report_dir=ws,
                        no_verifier=True)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY


# -- CLI wiring ---------------------------------------------------------------

@needs_sandbox
def test_cli_verify_checks_only(tmp_path, monkeypatch):
    from harness.cli import main

    ws = tmp_path / "ws"
    ws.mkdir()
    crit = tmp_path / "criteria.md"
    crit.write_text("- workspace contains no claims to test", encoding="utf-8")
    code = main(["verify", "--workspace", str(ws), "--criteria", str(crit),
                 "--check", "true", "--no-verifier",
                 "--report-dir", str(tmp_path / "rep")])
    assert code == EXIT_VERIFIED
    assert (tmp_path / "rep" / "report.md").exists()


@needs_sandbox
def test_cli_verify_failing_check(tmp_path):
    from harness.cli import main

    ws = tmp_path / "ws"
    ws.mkdir()
    crit = tmp_path / "criteria.md"
    crit.write_text("- x", encoding="utf-8")
    code = main(["verify", "--workspace", str(ws), "--criteria", str(crit),
                 "--check", "false", "--no-verifier",
                 "--report-dir", str(tmp_path / "rep")])
    assert code == EXIT_FAILED


def test_no_backend_checks_fail_closed(tmp_path, monkeypatch):
    # With no admitted sandbox backend, a check-bearing verify must report
    # cannot-verify (exit 2), never run the check unsandboxed and never
    # report pass or fail. This is the contract the CI no-backend job proves.
    monkeypatch.setattr("harness.sandbox.backend_name", lambda: None)
    req = make_request(tmp_path, checks=[Check(name="truth", command="true")],
                       no_verifier=True)
    out = run_standalone_verify(req)
    assert out.exit_code == EXIT_CANNOT_VERIFY
    report = out.report_path.read_text(encoding="utf-8")
    assert "CANNOT VERIFY" in report
