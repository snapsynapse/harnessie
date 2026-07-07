"""Trust-bundle manifest integrity checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ManifestResult:
    ok: bool
    files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def verify_manifest(root: Path, manifest_path: Path) -> ManifestResult:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    problems: list[str] = []
    files: list[str] = []

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return ManifestResult(False, problems=[f"manifest missing: {manifest_path}"])
    if manifest.get("kind") != "harnessie-trust-bundle":
        problems.append("manifest kind must be harnessie-trust-bundle")
    if manifest.get("version") != 1:
        problems.append("manifest version must be 1")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        problems.append("manifest files must be a non-empty list")
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append("manifest file entries must be mappings")
            continue
        rel = str(entry.get("path", ""))
        expected = str(entry.get("sha256", ""))
        files.append(rel)
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            problems.append(f"invalid manifest path: {rel!r}")
            continue
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            problems.append(f"manifest path escapes root: {rel}")
            continue
        if not target.is_file():
            problems.append(f"manifest file missing: {rel}")
            continue
        actual = _sha256(target)
        if actual != expected:
            problems.append(f"sha256 mismatch for {rel}: expected {expected}, got {actual}")
    return ManifestResult(ok=not problems, files=files, problems=problems)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["ManifestResult", "verify_manifest"]
