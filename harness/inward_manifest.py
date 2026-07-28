"""Hash-pinned identity for the harness inputs that govern a run.

The outward trust manifest proves public discovery artifacts. This inward
manifest pins the role prompts and configuration loaded by the runner itself.
A present manifest is mandatory and fail-closed; absence remains a legacy
no-op so downstream projects created before 0.8 keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path

import yaml

from .trust_manifest import sha256_file

KIND = "harnessie-inward-manifest"
VERSION = 1
POLICIES = frozenset({"refuse", "record"})


@dataclass
class InwardManifestResult:
    ok: bool
    policy: str = "refuse"
    files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    manifest_sha256: str = ""


def discover_inward_files(root: Path) -> list[str]:
    """Return every shipped runtime input the inward manifest must pin."""
    root = root.resolve()
    paths: list[Path] = []
    agents = root / "agents"
    if agents.exists():
        paths.extend(path for path in agents.rglob("*.md") if path.is_file())
    config = root / "config"
    if config.exists():
        paths.extend(path for path in config.rglob("*.yaml") if path.is_file())
        paths.extend(path for path in config.rglob("*.yml") if path.is_file())
    ownership = root / "OWNERSHIP.yaml"
    if ownership.is_file():
        paths.append(ownership)
    return sorted({
        path.relative_to(root).as_posix()
        for path in paths
    })


def render_inward_manifest(root: Path, policy: str = "refuse") -> str:
    if policy not in POLICIES:
        raise ValueError(f"inward manifest policy must be one of {sorted(POLICIES)}")
    root = root.resolve()
    data = {
        "kind": KIND,
        "version": VERSION,
        "on_divergence": policy,
        "files": [
            ({
                "path": rel,
                "scope": "policy",
                "sha256": ownership_policy_sha256(root / rel),
            } if rel == "OWNERSHIP.yaml" else {
                "path": rel,
                "sha256": sha256_file(root / rel),
            })
            for rel in discover_inward_files(root)
        ],
    }
    return yaml.safe_dump(data, sort_keys=False)


def ownership_policy_sha256(path: Path) -> str:
    """Hash static ownership policy while excluding auto-maintained claims."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"ownership policy is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("ownership policy must be a mapping")
    policy = {key: value for key, value in data.items() if key != "files"}
    canonical = yaml.safe_dump(
        policy, sort_keys=True, allow_unicode=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_inward_manifest(
        root: Path, manifest_path: Path) -> InwardManifestResult:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    manifest_sha = (
        sha256_file(manifest_path) if manifest_path.is_file() else "")
    try:
        manifest = yaml.safe_load(
            manifest_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return InwardManifestResult(
            False, problems=[f"inward manifest missing: {manifest_path}"])
    except (UnicodeError, yaml.YAMLError) as exc:
        return InwardManifestResult(
            False, problems=[f"inward manifest is not valid YAML: {exc}"],
            manifest_sha256=manifest_sha)

    problems: list[str] = []
    structurally_valid = True
    if not isinstance(manifest, dict):
        return InwardManifestResult(
            False, problems=["inward manifest must be a mapping"],
            manifest_sha256=manifest_sha)
    if manifest.get("kind") != KIND:
        problems.append(f"manifest kind must be {KIND}")
        structurally_valid = False
    if manifest.get("version") != VERSION:
        problems.append(f"manifest version must be {VERSION}")
        structurally_valid = False
    raw_policy = manifest.get("on_divergence")
    policy = str(raw_policy) if raw_policy in POLICIES else "refuse"
    if raw_policy not in POLICIES:
        problems.append(
            f"on_divergence must be one of {sorted(POLICIES)}")
        structurally_valid = False

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        problems.append("manifest files must be a non-empty list")
        structurally_valid = False
        entries = []
    files: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append("manifest file entries must be mappings")
            structurally_valid = False
            continue
        rel = str(entry.get("path", ""))
        expected = str(entry.get("sha256", ""))
        scope = str(entry.get("scope", "file"))
        files.append(rel)
        if rel in seen:
            problems.append(f"duplicate inward manifest path: {rel}")
            structurally_valid = False
            continue
        seen.add(rel)
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            problems.append(f"invalid inward manifest path: {rel!r}")
            structurally_valid = False
            continue
        if len(expected) != 64 or any(
                char not in "0123456789abcdef" for char in expected):
            problems.append(f"invalid sha256 for {rel}")
            structurally_valid = False
            continue
        if scope not in {"file", "policy"}:
            problems.append(f"invalid inward manifest scope for {rel}: {scope!r}")
            structurally_valid = False
            continue
        if scope == "policy" and rel != "OWNERSHIP.yaml":
            problems.append(
                f"policy scope is supported only for OWNERSHIP.yaml, not {rel}")
            structurally_valid = False
            continue
        if rel == "OWNERSHIP.yaml" and scope != "policy":
            problems.append("OWNERSHIP.yaml must use policy scope")
            structurally_valid = False
            continue
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            problems.append(f"inward manifest path escapes root: {rel}")
            structurally_valid = False
            continue
        if not target.is_file():
            problems.append(f"inward manifest file missing: {rel}")
            continue
        try:
            actual = (ownership_policy_sha256(target)
                      if scope == "policy" else sha256_file(target))
        except ValueError as exc:
            problems.append(str(exc))
            structurally_valid = False
            continue
        if actual != expected:
            problems.append(
                f"sha256 mismatch for {rel}: expected {expected}, got {actual}")

    discovered = set(discover_inward_files(root))
    pinned = set(files)
    for rel in sorted(discovered - pinned):
        problems.append(f"unpinned inward file: {rel}")
    for rel in sorted(pinned - discovered):
        problems.append(f"unexpected inward file: {rel}")
    return InwardManifestResult(
        ok=not problems,
        policy=policy if structurally_valid else "refuse",
        files=files,
        problems=problems,
        manifest_sha256=manifest_sha,
    )


__all__ = [
    "InwardManifestResult",
    "discover_inward_files",
    "ownership_policy_sha256",
    "render_inward_manifest",
    "verify_inward_manifest",
]
