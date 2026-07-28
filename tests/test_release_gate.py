"""Release-gate checks must fail closed before publication is possible."""

import io
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

from scripts import build_docs_html
from scripts.check_release_artifacts import (
    MAX_MEMBER_BYTES,
    Archive,
    _check_archive_limits,
    _check_scrub_terms,
    check_artifacts,
    read_sdist,
    read_wheel,
)

ROOT = Path(__file__).resolve().parents[1]


def test_generated_docs_are_current():
    assert build_docs_html.check() == []


def test_artifact_check_refuses_empty_directory(tmp_path):
    problems = check_artifacts(tmp_path)

    assert "expected one wheel, found 0" in problems
    assert "expected one sdist, found 0" in problems


def test_wheel_reader_refuses_path_traversal(tmp_path):
    wheel = tmp_path / "hostile.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("../escape.py", "pass")

    with pytest.raises(ValueError, match="unsafe archive path"):
        read_wheel(wheel)


def test_sdist_reader_refuses_links(tmp_path):
    sdist = tmp_path / "hostile.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        payload = b"safe"
        regular = tarfile.TarInfo("harnessie-0.0.0/README.md")
        regular.size = len(payload)
        archive.addfile(regular, io.BytesIO(payload))
        link = tarfile.TarInfo("harnessie-0.0.0/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../outside"
        archive.addfile(link)

    with pytest.raises(ValueError, match="unsupported archive member"):
        read_sdist(sdist)


def test_archive_limits_refuse_oversized_member(tmp_path):
    with pytest.raises(ValueError, match="invalid size"):
        _check_archive_limits(
            tmp_path / "large.whl",
            [("payload.bin", MAX_MEMBER_BYTES + 1)],
        )


def test_scrub_patterns_keep_regular_expression_semantics(tmp_path):
    archive = Archive(
        tmp_path / "artifact.whl",
        {"module.py": b"alpha beta"},
    )

    problems = _check_scrub_terms(
        archive, [re.compile(b"alpha[- ]beta")])

    assert problems == [
        "artifact.whl: private scrub term found in module.py"]


def test_package_metadata_uses_current_spdx_fields():
    data = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["build-system"]["requires"] == ["setuptools>=77"]
    assert data["project"]["license"] == "Apache-2.0"
    assert data["project"]["license-files"] == ["LICENSE", "NOTICE"]
