import pytest

from harness.cli import main
from harness.roles import RoleDef, RoleLibrary
from test_runner import scaffold_project


def test_boundaries_are_machine_appended():
    role = RoleDef(name="implementer", kind="worker", prompt="# Worker\nDo things.")
    system = role.system_prompt(extra_context="Goal: x")
    assert "Boundaries (harness-enforced)" in system
    assert "Never fabricate command output" in system     # from DEFAULT_BOUNDARIES
    # stable prefix first, volatile context after (prompt caching order)
    assert system.index("Boundaries (harness-enforced)") < system.index("Run context")


def test_unknown_agent_name_lists_known(tmp_path):
    (tmp_path / "orchestrator.md").write_text("# O")
    lib = RoleLibrary.load(tmp_path)
    with pytest.raises(KeyError) as exc:
        lib.get("nonexistent")
    assert "known:" in str(exc.value)


def test_cli_report_missing_run(tmp_path):
    assert main(["--root", str(tmp_path), "report", "no-such-run"]) == 1


def test_cli_run_exits_2_on_needs_human(tmp_path, capsys):
    # unscripted mock brain never calls tools -> plan phase ends no_action ->
    # needs_human -> CI-gateable exit code 2, plain-language halt with an action
    scaffold_project(tmp_path)
    code = main(["--root", str(tmp_path), "run", "workflows/mini.yaml",
                 "--goal", "g"])
    assert code == 2
    out = capsys.readouterr().out
    assert "stopped and is waiting for you" in out   # plain, not raw status
    assert "harnessie resume" in out                 # one named next action


def test_cli_report_renders_finished_run(tmp_path, capsys):
    scaffold_project(tmp_path)
    main(["--root", str(tmp_path), "run", "workflows/mini.yaml", "--goal", "g"])
    capsys.readouterr()
    run_id = next((tmp_path / "runs").iterdir()).name
    assert main(["--root", str(tmp_path), "report", run_id]) == 0
    out = capsys.readouterr().out
    # plain-language report leads, names the audit follow-up, no raw JSON dump
    assert "Phases:" in out
    assert f"harnessie audit {run_id}" in out
    assert "step_done" not in out
    # the raw developer view is still available behind --raw
    assert main(["--root", str(tmp_path), "report", run_id, "--raw"]) == 0
    raw = capsys.readouterr().out
    assert "events" in raw


def test_cli_init_scaffolds_project(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init"]) == 0
    out = capsys.readouterr().out
    assert "initialized Harnessie project" in out
    assert (tmp_path / "agents" / "orchestrator.md").exists()
    assert (tmp_path / "config" / "models.yaml").exists()
    assert (tmp_path / "evals" / "baseline.yaml").exists()


def test_cli_init_does_not_overwrite_by_default(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    target = tmp_path / "config" / "models.yaml"
    target.write_text("custom")
    assert main(["--root", str(tmp_path), "init"]) == 0
    capsys.readouterr()
    assert target.read_text() == "custom"
