from harness.firstrun import (
    check_python,
    check_sandbox,
    guided_first_run,
    key_guidance,
    run_mock_verification,
)
from harness.init_project import init_project


def test_check_python_passes_on_supported_interpreter():
    # The test suite itself requires 3.11+, so this must be True here.
    ok, msg = check_python()
    assert ok is True
    assert "3.11" in msg


def test_check_sandbox_returns_message_either_way():
    ok, msg = check_sandbox()
    assert isinstance(ok, bool)
    assert msg.strip()
    if not ok:
        # a missing backend must be framed as protection, not breakage
        assert "fail closed" in msg or "fail-closed" in msg.lower()


def test_key_guidance_mock_config_needs_no_key(tmp_path):
    init_project(tmp_path)
    ok, msg = key_guidance(tmp_path / "config" / "models.yaml")
    assert ok is True
    assert "No API key needed" in msg
    assert "zero dollars" in msg


def test_key_guidance_real_provider_names_env_var(tmp_path):
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        "tiers:\n"
        "  mid:\n"
        "    provider: anthropic\n"
        "    model_id: claude-sonnet-5\n"
        "    api_key_env: ANTHROPIC_API_KEY\n",
        encoding="utf-8")
    ok, msg = key_guidance(cfg)
    assert ok is True
    assert "export ANTHROPIC_API_KEY" in msg
    assert "never store" in msg.lower()


def test_mock_verification_is_green_and_zero_dollar(tmp_path):
    init_project(tmp_path)
    ok, msg = run_mock_verification(tmp_path)
    assert ok is True
    assert "billed\nnothing" in msg or "billed nothing" in msg.replace("\n", " ")


def test_guided_first_run_is_ready_after_scaffold(tmp_path):
    init_project(tmp_path)
    ready, report = guided_first_run(tmp_path)
    assert ready is True
    assert "Guided first run" in report
    assert "harnessie run workflows/build-and-verify.yaml" in report
    assert "harnessie report" in report
    # every readiness line is present
    for label in ("Python:", "Sandbox:", "API keys:", "First run:"):
        assert label in report
