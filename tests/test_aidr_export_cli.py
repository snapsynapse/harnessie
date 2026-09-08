"""Offline export CLI contracts, separate from parser and publication tests."""

import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from harness.cli import main


OUTPUT = "decisions/AIDR-0042-review.md"


def arguments(root):
    return ["--root", str(root), "export-aidr", "R", "review",
            "--output", OUTPUT, "--arbiter", "sam"]


@pytest.fixture
def export_stub(monkeypatch):
    module = types.ModuleType("harness.aidr_export")

    class AIDRExportError(Exception):
        def __init__(self, code):
            self.code = code

    module.AIDRExportError = AIDRExportError
    monkeypatch.setitem(sys.modules, "harness.aidr_export", module)
    return module


def test_cli_passes_explicit_inputs_without_resolving_root(export_stub, capsys):
    expected = {"status": "exported", "output": OUTPUT,
                "source_sha256": "a" * 64, "evidence_sha256": "b" * 64,
                "output_sha256": "c" * 64, "target_spec": "0.1.0"}

    def export(**kwargs):
        assert kwargs == {"root": Path("relative/project"), "run_id": "R",
                          "phase": "review", "output": OUTPUT, "arbiter": "sam"}
        return expected

    export_stub.export_aidr = export
    assert main(arguments("relative/project")) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.err == ""


@pytest.mark.parametrize("code", ["unsafe_path", "missing_input", "invalid_record",
                                 "destination_collision"])
def test_cli_refusal_is_stable_json_without_traceback(export_stub, capsys, code):
    def export(**kwargs):
        raise export_stub.AIDRExportError(code)

    export_stub.export_aidr = export
    assert main(arguments(".")) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "refused", "code": code}
    assert captured.err == ""


@pytest.mark.parametrize("option", ["--output", "--arbiter"])
def test_cli_requires_destination_and_human_declaration(option, capsys):
    args = arguments(".")
    index = args.index(option)
    del args[index:index + 2]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert option in capsys.readouterr().err


@pytest.fixture
def source_project(tmp_path):
    from harness.adversarial import PositionRecord, assemble_record
    from harness.events import EventLog

    (tmp_path / "decisions").mkdir()
    run = tmp_path / "runs" / "R"
    (run / "decisions").mkdir(parents=True)
    log = EventLog(run, echo=False)
    log.emit("position_recorded", phase="review", label="reviewer", stance="oppose")
    log.close()
    source = run / "decisions" / "DR-review.md"
    source.write_text(assemble_record(
        "DR-review", "A storage decision", "Should we change storage?",
        "An existing recorded decision.", "operator",
        [PositionRecord("reviewer", "reviewer", "reported-model", "reported-provider",
                        "oppose", "Keep current storage.", "DISSENT: preserve the log.")],
        [{"by": "reviewer", "to": "the record", "text": "OBJECTION: migration loses history."}],
        ["runs/R/events.jsonl — hash-chained event log evidencing isolated position generation"],
        date="2026-09-08"), encoding="utf-8")
    return tmp_path


def test_cli_real_export_json_and_source_preservation(source_project, capsys):
    root = source_project
    before = {p: p.read_bytes() for p in (root / "runs").rglob("*") if p.is_file()}
    assert main(arguments(root)) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    output = root / result["output"]
    assert result["status"] == "exported"
    assert result["output"] == OUTPUT
    assert result["target_spec"] == "0.1.0"
    assert result["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert result["source_sha256"] == hashlib.sha256(
        before[root / "runs/R/decisions/DR-review.md"]).hexdigest()
    assert result["evidence_sha256"] == hashlib.sha256(
        before[root / "runs/R/events.jsonl"]).hexdigest()
    assert "DISSENT: preserve the log." in output.read_text()
    assert "OBJECTION: migration loses history." in output.read_text()
    assert "## Arbitration\n\n## Evidence" in output.read_text()
    assert all(path.read_bytes() == content for path, content in before.items())
    assert captured.err == ""


def test_cli_real_collision_refuses_without_overwrite(source_project, capsys):
    output = source_project / OUTPUT
    output.write_bytes(b"existing decision")
    assert main(arguments(source_project)) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "refused", "code": "destination_collision"}
    assert output.read_bytes() == b"existing decision"
    assert captured.err == ""


def test_cli_real_export_never_imports_runner_models_or_uses_network(source_project):
    script = """
import importlib.abc
import socket
import sys

class OfflineOnly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "harness.runner" or fullname.startswith("harness.models"):
            raise AssertionError("export imported execution code: " + fullname)

def forbidden(*args, **kwargs):
    raise AssertionError("export attempted network access")

sys.meta_path.insert(0, OfflineOnly())
socket.socket.connect = forbidden
socket.create_connection = forbidden
from harness.cli import main
raise SystemExit(main(sys.argv[1:]))
"""
    result = subprocess.run([sys.executable, "-c", script, *arguments(source_project)],
                            cwd=Path(__file__).resolve().parents[1],
                            text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "exported"
    assert result.stderr == ""
