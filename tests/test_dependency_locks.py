"""Lock drift and malformed lock data must refuse before installation."""
import json
import shutil
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.dependency_locks import validate

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    shutil.copy(ROOT / "pyproject.toml", tmp_path)
    shutil.copytree(ROOT / "requirements", tmp_path / "requirements")
    return tmp_path


def test_current_locks():
    assert validate(ROOT) == []


@pytest.mark.parametrize("damage", ["input", "hash", "duplicate", "missing", "manifest"])
def test_lock_damage_refuses(tmp_path, damage):
    root = fixture(tmp_path)
    lock = root / "requirements/dev.txt"
    if damage == "input":
        path = root / "pyproject.toml"
        path.write_text(path.read_text().replace('"pytest>=8.0"', '"pytest>=9.0"'))
    elif damage == "hash":
        lock.write_text(lock.read_text().replace("--hash=sha256:", "--hash=md5:", 1))
    elif damage == "duplicate":
        lock.write_text(lock.read_text() + "\npytest==9.9.9 --hash=sha256:" + "0" * 64 + "\n")
    elif damage == "missing":
        lock.unlink()
    else:
        (root / "requirements/manifest.json").write_text('{}')
    assert validate(root)


def test_release_version_change_does_not_stale_dependency_lock(tmp_path):
    root = fixture(tmp_path)
    path = root / "pyproject.toml"
    path.write_text(path.read_text().replace('version = "1.2.0"', 'version = "1.3.0"'))
    assert validate(root) == []


def wheel(directory, name, requires=""):
    path = directory / f"{name}-1.0-py3-none-any.whl"
    info = f"{name}-1.0.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{info}/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n" + requires)
        archive.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(f"{info}/RECORD", "")
    return path


@pytest.mark.parametrize("damage", [None, "tampered_wheel", "omitted_transitive"])
def test_pip_enforces_artifact_hashes_and_transitive_coverage(tmp_path, damage):
    # Synthetic wheels exercise the real installer entirely offline.
    parent = wheel(tmp_path, "lock_parent", "Requires-Dist: lock-child==1.0\n")
    child = wheel(tmp_path, "lock_child")
    lines = [f"{name}==1.0 --hash=sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
             for name, path in (("lock-parent", parent), ("lock-child", child))]
    if damage == "tampered_wheel":
        child.write_bytes(child.read_bytes() + b"changed")
    elif damage == "omitted_transitive":
        lines.pop()
    lock = tmp_path / "test.txt"
    lock.write_text("\n".join(lines) + "\n")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                             "--no-index", "--find-links", str(tmp_path), "--only-binary=:all:",
                             "--require-hashes", "--target", str(tmp_path / "installed"),
                             "-r", str(lock)], capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) is (damage is None), result.stdout + result.stderr
    if damage:
        assert "hash" in result.stderr.lower()
