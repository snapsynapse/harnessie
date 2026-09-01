#!/usr/bin/env python3
"""Fail-closed inspection of one Harnessie wheel and source distribution."""

from __future__ import annotations

import argparse
import email.parser
import re
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = frozenset({
    ".agents",
    ".codex",
    ".env",
    ".maiden",
    "build",
    "dist",
    "handoffs",
    "runs",
    "workspace",
})
FORBIDDEN_NAMES = frozenset({"roadmap-private.md"})
REQUIRED_PACKAGE_FILES = frozenset({
    "harness/inward_manifest.py",
    "harness/maiden.py",
    "harness/schema.py",
    "harness/verify_evidence.py",
    "harness/schemas/v1/models.schema.json",
    "harness/schemas/v1/cascade.schema.json",
    "harness/schemas/v1/boundary.schema.json",
    "harness/schemas/v1/approval-policy.schema.json",
    "harness/schemas/v1/ownership.schema.json",
    "harness/schemas/v1/verify-evidence.schema.json",
    "harness/schemas/v1/workflow.schema.json",
})
MAX_FILES = 5_000
MAX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class Archive:
    path: Path
    files: dict[str, bytes]


def project_version(root: Path = ROOT) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _safe_name(raw: str) -> str:
    name = PurePosixPath(raw)
    if name.is_absolute() or ".." in name.parts or "\\" in raw:
        raise ValueError(f"unsafe archive path: {raw!r}")
    return name.as_posix()


def read_wheel(path: Path) -> Archive:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        _check_archive_limits(
            path, [(info.filename, info.file_size) for info in members])
        for info in members:
            name = _safe_name(info.filename)
            if not info.is_dir():
                files[name] = archive.read(info)
    return Archive(path, files)


def read_sdist(path: Path) -> Archive:
    files: dict[str, bytes] = {}
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        _check_archive_limits(
            path, [(member.name, member.size) for member in members])
        for member in members:
            name = _safe_name(member.name)
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(
                    f"unsupported archive member type: {member.name!r}")
            if member.isfile():
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError(f"could not read archive member: {name}")
                files[name] = extracted.read()
    return Archive(path, files)


def _check_archive_limits(
        path: Path, members: list[tuple[str, int]]) -> None:
    if len(members) > MAX_FILES:
        raise ValueError(
            f"{path.name}: archive has {len(members)} entries, "
            f"limit is {MAX_FILES}")
    total = 0
    for name, size in members:
        if size < 0 or size > MAX_MEMBER_BYTES:
            raise ValueError(
                f"{path.name}: archive member {name!r} has invalid size {size}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError(
                f"{path.name}: expanded archive exceeds {MAX_TOTAL_BYTES} bytes")


def _relative_sdist_files(
        files: dict[str, bytes], version: str) -> dict[str, bytes]:
    prefix = f"harnessie-{version}/"
    if not files or any(not name.startswith(prefix) for name in files):
        raise ValueError(f"sdist entries must share root {prefix!r}")
    return {name[len(prefix):]: content for name, content in files.items()}


def _metadata(
    archive: Archive,
    name: str,
    *,
    exact: bool = False,
) -> email.message.Message:
    matches = [
        content for path, content in archive.files.items()
        if path == name or (not exact and path.endswith(name))
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{archive.path.name}: expected one {name}, found {len(matches)}")
    return email.parser.BytesParser().parsebytes(matches[0])


def _scrub_terms(root: Path) -> list[re.Pattern[bytes]]:
    path = root / "handoffs" / "scrub-list.txt"
    if not path.is_file():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(
                line.strip().encode("utf-8"), re.IGNORECASE))
        except re.error as exc:
            raise ValueError(f"invalid private scrub-list pattern: {exc}") from exc
    return patterns


def _check_names(archive: Archive) -> list[str]:
    problems = []
    for raw in archive.files:
        path = PurePosixPath(raw.lower())
        if path.name in FORBIDDEN_NAMES:
            problems.append(f"{archive.path.name}: forbidden file {raw}")
        forbidden = sorted(set(path.parts) & FORBIDDEN_PARTS)
        if forbidden:
            problems.append(
                f"{archive.path.name}: forbidden path component "
                f"{forbidden[0]!r} in {raw}")
    return problems


def _check_scrub_terms(
        archive: Archive,
        terms: list[re.Pattern[bytes]],
) -> list[str]:
    problems = []
    for name, content in archive.files.items():
        for term in terms:
            if term.search(content):
                problems.append(
                    f"{archive.path.name}: private scrub term found in {name}")
    return problems


def check_artifacts(
        dist_dir: Path, root: Path = ROOT) -> list[str]:
    version = project_version(root)
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    problems: list[str] = []
    if len(wheels) != 1:
        problems.append(f"expected one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        problems.append(f"expected one sdist, found {len(sdists)}")
    if problems:
        return problems
    if wheels[0].name != f"harnessie-{version}-py3-none-any.whl":
        problems.append(
            f"wheel filename does not match version {version}: {wheels[0].name}")
    if sdists[0].name != f"harnessie-{version}.tar.gz":
        problems.append(
            f"sdist filename does not match version {version}: {sdists[0].name}")

    try:
        wheel = read_wheel(wheels[0])
        raw_sdist = read_sdist(sdists[0])
        sdist = Archive(
            raw_sdist.path,
            _relative_sdist_files(raw_sdist.files, version),
        )
        scrub_terms = _scrub_terms(root)
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
        return problems + [str(exc)]

    for archive in (wheel, sdist):
        problems.extend(_check_names(archive))
        problems.extend(_check_scrub_terms(archive, scrub_terms))

    for required in REQUIRED_PACKAGE_FILES:
        if required not in wheel.files:
            problems.append(f"wheel missing {required}")
        if required not in sdist.files:
            problems.append(f"sdist missing {required}")
    for required in ("LICENSE", "NOTICE", "README.md", "pyproject.toml"):
        if required not in sdist.files:
            problems.append(f"sdist missing {required}")
    wheel_names = set(wheel.files)
    for required in ("LICENSE", "NOTICE"):
        if not any(name.endswith(f"/licenses/{required}")
                   for name in wheel_names):
            problems.append(f"wheel missing license file {required}")

    try:
        wheel_meta = _metadata(wheel, ".dist-info/METADATA")
        sdist_meta = _metadata(sdist, "PKG-INFO", exact=True)
    except ValueError as exc:
        problems.append(str(exc))
    else:
        for label, metadata in (("wheel", wheel_meta), ("sdist", sdist_meta)):
            if metadata.get("Name") != "harnessie":
                problems.append(f"{label} metadata Name is not harnessie")
            if metadata.get("Version") != version:
                problems.append(
                    f"{label} metadata Version does not match {version}")
            if metadata.get("License-Expression") != "Apache-2.0":
                problems.append(
                    f"{label} metadata lacks Apache-2.0 License-Expression")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dist_dir", nargs="?", default="dist",
        help="directory containing exactly one wheel and one sdist")
    args = parser.parse_args()
    dist_dir = Path(args.dist_dir).resolve()
    problems = check_artifacts(dist_dir)
    if problems:
        print("release artifacts FAILED")
        for problem in problems:
            print(f"- {problem}")
        return 2
    print("release artifacts OK: wheel and sdist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
