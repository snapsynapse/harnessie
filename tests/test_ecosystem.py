import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import yaml
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ecosystem_status.py"


def _module():
    spec = importlib.util.spec_from_file_location("ecosystem_status", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_shipped_ecosystem_manifest_has_expected_authority_and_release_order():
    data = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
    assert data["authority"] == "core"
    assert set(data["components"]) == {
        "core", "engine_wrappers", "verify_action", "homebrew"}
    assert data["components"]["homebrew"]["shared"] is True
    assert data["release_trains"]["core"]["order"] == [
        "core", "verify_action", "homebrew"]
    assert data["release_trains"]["engine_wrappers"]["order"] == [
        "engine_wrappers"]
    _module().load_manifest(ROOT / "ecosystem.yaml")


def test_manifest_rejects_version_source_escape(tmp_path):
    path = tmp_path / "ecosystem.yaml"
    path.write_text(
        "schema_version: 1\n"
        "project: demo\n"
        "authority: core\n"
        "components:\n"
        "  core:\n"
        "    repo: example/core\n"
        "    local_dir: core\n"
        "    role: product-authority\n"
        "    version_source:\n"
        "      format: toml\n"
        "      path: ../private.toml\n"
        "      key: project.version\n"
        "release_trains:\n"
        "  core: {order: [core]}\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="escapes its repository"):
        _module().load_manifest(path)


def test_status_reads_versions_and_reports_drift_without_network(tmp_path):
    manifest = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
    for component in manifest["components"].values():
        (tmp_path / component["local_dir"]).mkdir()
    (tmp_path / "harnessie" / "pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n', encoding="utf-8")
    (tmp_path / "harnessie-engine-wrappers" / "pyproject.toml").write_text(
        '[project]\nversion = "0.1.0"\n', encoding="utf-8")
    (tmp_path / "harnessie-verify-action" / "action.yml").write_text(
        "inputs:\n  harnessie-version:\n    default: 0.8.0\n", encoding="utf-8")
    formula = tmp_path / "homebrew-tap" / "Formula"
    formula.mkdir()
    (formula / "harnessie.rb").write_text(
        'url "https://files.pythonhosted.org/harnessie-0.7.1.tar.gz"\n',
        encoding="utf-8")

    status = _module().collect_status(manifest, tmp_path)

    assert status["components"]["core"]["version"] == "0.8.0"
    assert status["components"]["engine_wrappers"]["version"] == "0.1.0"
    assert status["components"]["verify_action"]["core_pin"] == "0.8.0"
    assert status["compatibility"] == [
        {"component": "verify_action", "expected_core": "0.8.0",
         "observed_pin": "0.8.0", "status": "match"},
        {"component": "homebrew", "expected_core": "0.8.0",
         "observed_pin": "0.7.1", "status": "drift"},
    ]


def test_status_json_cli_is_machine_readable(tmp_path):
    manifest = tmp_path / "ecosystem.yaml"
    manifest.write_text(
        "schema_version: 1\n"
        "project: demo\n"
        "authority: core\n"
        "components:\n"
        "  core:\n"
        "    repo: example/core\n"
        "    local_dir: core\n"
        "    role: product-authority\n"
        "release_trains:\n"
        "  core: {order: [core]}\n",
        encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest", str(manifest),
         "--git-root", str(tmp_path), "--json"],
        capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout)
    assert payload["project"] == "demo"
    assert payload["components"]["core"]["available"] is False


def test_github_observations_are_optional_mirror(monkeypatch):
    module = _module()
    responses = {
        "repos/example/core/releases?per_page=1": [{"tag_name": "v1.2.3"}],
        "repos/example/core/pulls?state=open&per_page=100": [{
            "number": 7, "title": "Change", "draft": True,
            "html_url": "https://github.com/example/core/pull/7"}],
    }
    monkeypatch.setattr(module, "_github_json", responses.__getitem__)
    status = {"components": {"core": {"repo": "example/core"}}}

    module.add_github_observations(status)

    observed = status["components"]["core"]["github"]
    assert observed["latest_release"] == "v1.2.3"
    assert observed["open_pull_requests"] == [{
        "number": 7, "title": "Change", "draft": True,
        "url": "https://github.com/example/core/pull/7"}]
