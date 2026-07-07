from pathlib import Path

from harness.cli import main
from harness.trust_manifest import verify_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_shipped_trust_manifest_verifies():
    result = verify_manifest(ROOT, ROOT / "docs" / "MANIFEST.yaml")

    assert result.ok, result.problems
    assert result.files
    assert "docs/llms.txt" in result.files


def test_cli_verify_manifest(capsys):
    code = main(["--root", str(ROOT), "verify-manifest"])
    out = capsys.readouterr().out

    assert code == 0
    assert "trust manifest OK" in out


def test_trust_manifest_detects_tampering(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("trusted\n", encoding="utf-8")
    manifest = tmp_path / "MANIFEST.yaml"
    manifest.write_text(
        "kind: harnessie-trust-bundle\n"
        "version: 1\n"
        "files:\n"
        "  - path: source.txt\n"
        "    sha256: 7bd39a7cbcf687fd60f819645b8bcaf731a9f19cb102484a7b84530516d7e8b8\n",
        encoding="utf-8",
    )

    assert verify_manifest(tmp_path, manifest).ok
    source.write_text("changed\n", encoding="utf-8")

    result = verify_manifest(tmp_path, manifest)
    assert not result.ok
    assert any("sha256 mismatch" in p for p in result.problems)
