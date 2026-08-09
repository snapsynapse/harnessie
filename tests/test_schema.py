"""Stable v1 authoring contracts and the side-effect-free validator."""

from importlib.resources import files
from pathlib import Path
import textwrap

from jsonschema import Draft202012Validator

from harness.cli import main
from harness.init_project import init_project
from harness.schema import (KINDS, ConfigurationError, read_document,
                            validate_data, validate_project)


ROOT = Path(__file__).resolve().parents[1]


def test_all_packaged_schemas_are_valid_draft_2020_12():
    package = files("harness.schemas.v1")
    assert KINDS == {
        "models", "cascade", "boundary", "approval-policy", "ownership", "workflow",
    }
    for kind in KINDS:
        import json
        schema = json.loads(package.joinpath(f"{kind}.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("https://harnessie.com/schemas/v1/")


def test_served_schemas_are_byte_identical_to_packaged_contracts():
    package = files("harness.schemas.v1")
    for kind in KINDS:
        filename = f"{kind}.schema.json"
        assert (ROOT / "docs" / "schemas" / "v1" / filename).read_text() == \
            package.joinpath(filename).read_text()


def test_shipped_project_validates_without_side_effects(capsys):
    runs_before = sorted((ROOT / "runs").iterdir()) if (ROOT / "runs").exists() else []
    assert main(["--root", str(ROOT), "validate"]) == 0
    assert "configuration valid: 9 document(s), schema v1" in capsys.readouterr().out
    runs_after = sorted((ROOT / "runs").iterdir()) if (ROOT / "runs").exists() else []
    assert runs_after == runs_before


def test_implicit_v1_remains_accepted_for_08_models(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text(textwrap.dedent("""
        tiers:
          mid: {provider: mock, model_id: mock}
        routing:
          default: {tier: mid, effort: medium}
    """))
    assert "schema_version" not in read_document(path, "models")


def test_unknown_keys_and_coercible_types_are_rejected():
    unknown = validate_data(
        {"tiers": {"mid": {"provider": "mock", "model_id": "mock", "max_token": 4}}},
        "models")
    wrong_type = validate_data(
        {"tiers": {"mid": {"provider": "mock", "model_id": "mock",
                            "supports_effort": "false"}}}, "models")
    assert any(problem.code == "schema.additionalProperties" for problem in unknown)
    assert any(problem.path.endswith("supports_effort") and problem.code == "schema.type"
               for problem in wrong_type)


def test_unsupported_schema_version_fails_before_other_validation():
    problems = validate_data({"schema_version": 2}, "boundary")
    assert [(p.path, p.code) for p in problems] == [
        ("$.schema_version", "schema.version_unsupported")]


def test_project_cross_checks_roles_cascades_placeholders_and_phase_names(tmp_path):
    init_project(tmp_path)
    workflow = tmp_path / "workflows" / "bad.yaml"
    workflow.write_text(textwrap.dedent("""
        schema_version: 1
        name: bad
        phases:
          - name: repeat
            agent: missing-agent
            cascade: missing-policy
            task: "Use {later}"
          - name: repeat
            task: "done"
    """))
    report = validate_project(tmp_path)
    codes = {problem.code for problem in report.problems}
    assert {"workflow.duplicate_phase", "workflow.unknown_role",
            "workflow.unknown_cascade", "workflow.unknown_placeholder"} <= codes


def test_requested_workflow_uses_project_context(tmp_path):
    init_project(tmp_path)
    report = validate_project(tmp_path, [Path("workflows/build-and-verify.yaml")])
    assert report.ok, report.problems
    assert report.documents == 3  # models, ownership, requested workflow


def test_cli_invalid_document_is_deterministic_and_exit_2(tmp_path, capsys):
    init_project(tmp_path)
    workflow = tmp_path / "workflows" / "bad.yaml"
    workflow.write_text("name: bad\nphases: nope\n")
    assert main(["--root", str(tmp_path), "validate", str(workflow)]) == 2
    err = capsys.readouterr().err
    assert "configuration invalid:" in err
    assert "$.phases" in err
    assert "[schema.type]" in err


def test_init_emits_explicit_v1_and_validates(tmp_path):
    init_project(tmp_path)
    for path in (tmp_path / "config" / "models.yaml",
                 tmp_path / "workflows" / "build-and-verify.yaml",
                 tmp_path / "OWNERSHIP.yaml"):
        assert "schema_version: 1" in path.read_text()
    assert validate_project(tmp_path).ok
