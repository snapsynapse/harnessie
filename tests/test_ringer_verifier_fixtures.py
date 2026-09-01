"""Network-free golden cases distilled from public Ringer verifier findings."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
CORPUS = yaml.safe_load((ROOT / "tests" / "fixtures" /
                         "ringer-verifier.yaml").read_text(
    encoding="utf-8"))
FIXTURES = CORPUS["fixtures"]


def path_allowed_like_fixture(path: str, allowed: list[str]) -> bool:
    """Reproduce the reverse-prefix rule under evaluation."""
    normalized = path.strip().rstrip("/")
    for raw in allowed:
        candidate = raw.strip().rstrip("/")
        if not candidate:
            continue
        if normalized == candidate or normalized.startswith(candidate + "/"):
            return True
        if candidate.startswith(normalized + "/"):
            return True
    return False


def harvest_like_fixture(stage: Path, repo: Path, owned: list[str]) -> tuple[list[str], bool]:
    """Minimal vulnerable staging algorithm captured by the synthetic corpus."""
    if not stage.is_dir():
        return [], True
    if stage.is_symlink():
        return [], False
    staged: list[tuple[Path, str]] = []
    for dirpath, _dirnames, filenames in os.walk(stage):
        # The intentionally unused dirnames reproduce the directory-symlink
        # blind spot. File symlinks are still refused.
        for name in filenames:
            source = Path(dirpath) / name
            relative = source.relative_to(stage).as_posix()
            if source.is_symlink() or not source.is_file():
                return [], False
            if not path_allowed_like_fixture(relative, owned):
                return [], False
            staged.append((source, relative))
    installed: list[str] = []
    for source, relative in staged:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)
        installed.append(relative)
    return installed, True


def materialize_stage(case: dict, tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    stage = tmp_path / "stage"
    if case.get("stage_root") == "dangling-symlink":
        stage.symlink_to(tmp_path / "missing", target_is_directory=True)
        return stage, repo
    stage.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    for entry in case["stage"]:
        target = stage / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if entry["type"] == "file":
            target.write_text(entry["content"], encoding="utf-8")
        elif entry["type"] == "directory-symlink":
            target.symlink_to(outside, target_is_directory=True)
        else:
            raise AssertionError(f"unknown synthetic entry type: {entry['type']}")
    return stage, repo


def fixture_by_id(fixture_id: str) -> dict:
    return next(item for item in FIXTURES if item["id"] == fixture_id)


def test_corpus_has_stable_unique_case_ids() -> None:
    ids = [case["id"] for case in FIXTURES]
    assert CORPUS["format"] == "synthetic-fixtures-v1"
    assert len(ids) == len(set(ids)) == 4


def test_quoted_command_substitution_does_not_fall_back_to_home() -> None:
    case = fixture_by_id("quoted_command_substitution_fails_closed")
    quoted = subprocess.run(["bash", "-c", case["quoted"]], capture_output=True, text=True)
    unquoted = subprocess.run(["bash", "-c", case["unquoted"]], capture_output=True, text=True)

    assert quoted.returncode != 0
    assert quoted.stdout == case["expect"]["quoted_stdout"]
    assert unquoted.returncode == case["expect"]["unquoted_exit"]
    assert unquoted.stdout


def test_parallel_identical_denials_are_one_decision_and_allow_recovery(tmp_path: Path) -> None:
    """Unit backstop for the governance scenario's multi-call turn shape."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    registry = ToolRegistry()
    register_builtin(registry, workspace=workspace)
    denied = AssistantTurn(
        content="",
        stop_reason="tool_use",
        tool_calls=[
            ToolCall(
                id=f"denied_{index}",
                name="run_shell",
                arguments={"command": "curl https://example.com/"},
            )
            for index in range(3)
        ],
    )
    complete = AssistantTurn(
        content="",
        stop_reason="tool_use",
        tool_calls=[ToolCall(
            id="complete",
            name="task_complete",
            arguments={"report": "recovered"},
        )],
    )
    model = MockModel(
        ModelSpec(name="mock", provider="mock", model_id="mock"),
        script=[denied, complete],
    )
    loop = AgentLoop(
        role="worker",
        model=model,
        registry=registry,
        events=EventLog(tmp_path / "run", echo=False),
    )

    result = loop.run("system", "recover from a denied parallel decision")

    assert result.stop == "complete"


@pytest.mark.parametrize("fixture_id", [
    "staged_parent_of_owned_child_is_accepted",
    "directory_symlink_is_ignored_while_sibling_installs",
    "dangling_stage_root_is_treated_as_absent",
])
def test_synthetic_staged_harvest_behaviors(fixture_id: str, tmp_path: Path) -> None:
    case = fixture_by_id(fixture_id)
    stage, repo = materialize_stage(case, tmp_path)

    installed, ok = harvest_like_fixture(stage, repo, case["owned"])

    assert ok is case["expect"]["ok"]
    assert installed == case["expect"]["installed"]
