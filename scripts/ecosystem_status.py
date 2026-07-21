#!/usr/bin/env python3
"""Offline, read-only status for the federated Harnessie project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import sys
import tomllib
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


class EcosystemError(ValueError):
    pass


def _nested(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise EcosystemError(f"missing key {dotted!r}")
        value = value[part]
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("schema_version") != 1:
        raise EcosystemError("schema_version must be 1")
    components = data.get("components")
    if not isinstance(components, dict) or not components:
        raise EcosystemError("components must be a non-empty mapping")
    authority = data.get("authority")
    if authority not in components:
        raise EcosystemError("authority must name a component")
    for name, component in components.items():
        if not isinstance(component, dict):
            raise EcosystemError(f"component {name!r} must be a mapping")
        repo = component.get("repo")
        if not isinstance(repo, str) or repo.count("/") != 1:
            raise EcosystemError(f"component {name!r} has invalid repo")
        local_dir = component.get("local_dir")
        if not isinstance(local_dir, str) or "/" in local_dir or local_dir in ("", ".", ".."):
            raise EcosystemError(f"component {name!r} has invalid local_dir")
        if not isinstance(component.get("role"), str) or not component["role"]:
            raise EcosystemError(f"component {name!r} has invalid role")
        for source_name in ("version_source", "core_pin_source"):
            source = component.get(source_name)
            if source is None:
                continue
            if not isinstance(source, dict) or not isinstance(source.get("path"), str):
                raise EcosystemError(
                    f"component {name!r} has invalid {source_name}")
            source_path = PurePosixPath(source["path"])
            if source_path.is_absolute() or ".." in source_path.parts:
                raise EcosystemError(
                    f"component {name!r} {source_name} escapes its repository")
    trains = data.get("release_trains")
    if not isinstance(trains, dict) or not trains:
        raise EcosystemError("release_trains must be a non-empty mapping")
    for train, spec in trains.items():
        order = spec.get("order") if isinstance(spec, dict) else None
        if not isinstance(order, list) or not order:
            raise EcosystemError(f"release train {train!r} needs an order")
        unknown = [name for name in order if name not in components]
        if unknown:
            raise EcosystemError(f"release train {train!r} names unknown components: {unknown}")
    return data


def _git(path: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True,
        timeout=10, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _source_value(repo_path: Path, source: dict[str, Any]) -> str:
    path = repo_path / str(source["path"])
    if not path.is_file():
        raise EcosystemError(f"missing version source {path}")
    kind = source.get("format")
    if kind == "toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return str(_nested(data, str(source["key"])))
    if kind == "yaml":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return str(_nested(data, str(source["key"])))
    if kind == "python-sdist-url":
        package = re.escape(str(source["package"]))
        match = re.search(rf"{package}-([0-9]+(?:\.[0-9]+)+)\.tar\.gz",
                          path.read_text(encoding="utf-8"))
        if not match:
            raise EcosystemError(f"no {source['package']} sdist version in {path}")
        return match.group(1)
    raise EcosystemError(f"unsupported version source format {kind!r}")


def collect_status(manifest: dict[str, Any], git_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"project": manifest["project"], "components": {}}
    for name, component in manifest["components"].items():
        repo_path = git_root / component["local_dir"]
        row: dict[str, Any] = {
            "repo": component["repo"],
            "role": component["role"],
            "path": str(repo_path),
            "available": repo_path.is_dir(),
        }
        if row["available"]:
            row["branch"] = _git(repo_path, "branch", "--show-current")
            row["revision"] = _git(repo_path, "rev-parse", "--short=12", "HEAD")
            porcelain = _git(repo_path, "status", "--porcelain")
            row["dirty"] = None if porcelain is None else bool(porcelain)
            try:
                if "version_source" in component:
                    row["version"] = _source_value(repo_path, component["version_source"])
                if "core_pin_source" in component:
                    row["core_pin"] = _source_value(repo_path, component["core_pin_source"])
            except EcosystemError as exc:
                row["source_error"] = str(exc)
        result["components"][name] = row

    core_version = result["components"].get("core", {}).get("version")
    compatibility: list[dict[str, Any]] = []
    for name, row in result["components"].items():
        if "core_pin" not in row:
            continue
        pin = row["core_pin"]
        compatibility.append({
            "component": name,
            "expected_core": core_version,
            "observed_pin": pin,
            "status": ("unknown" if core_version is None else
                       "match" if core_version == pin else "drift"),
        })
    result["compatibility"] = compatibility
    return result


def _github_json(endpoint: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True,
        timeout=20, check=False)
    if proc.returncode != 0:
        raise EcosystemError(proc.stderr.strip() or f"GitHub query failed: {endpoint}")
    return json.loads(proc.stdout)


def add_github_observations(status: dict[str, Any]) -> None:
    """Add optional cloud observations without making them authoritative."""
    for row in status["components"].values():
        repo = row["repo"]
        remote: dict[str, Any] = {}
        try:
            releases = _github_json(f"repos/{repo}/releases?per_page=1")
            remote["latest_release"] = (
                releases[0].get("tag_name") if releases else None)
            pulls = _github_json(f"repos/{repo}/pulls?state=open&per_page=100")
            remote["open_pull_requests"] = [{
                "number": pull.get("number"),
                "title": pull.get("title"),
                "draft": bool(pull.get("draft")),
                "url": pull.get("html_url"),
            } for pull in pulls]
        except (EcosystemError, json.JSONDecodeError, TypeError, OSError) as exc:
            remote["error"] = str(exc)
        row["github"] = remote


def _print_human(status: dict[str, Any]) -> None:
    print(f"{status['project']} ecosystem (offline local state)")
    for name, row in status["components"].items():
        if not row["available"]:
            print(f"- {name}: unavailable at {row['path']}")
            continue
        version = f" version={row['version']}" if row.get("version") else ""
        pin = f" core_pin={row['core_pin']}" if row.get("core_pin") else ""
        dirty = ("git-unavailable" if row.get("dirty") is None else
                 "dirty" if row["dirty"] else "clean")
        revision = row.get("revision") or "unknown"
        branch = row.get("branch") or "detached/unknown"
        print(f"- {name}: {branch}@{revision} {dirty}{version}{pin}")
        if row.get("source_error"):
            print(f"  source_error: {row['source_error']}")
        github = row.get("github")
        if github:
            if github.get("error"):
                print(f"  github_error: {github['error']}")
            else:
                print("  github: latest_release="
                      f"{github.get('latest_release') or 'none'} "
                      f"open_prs={len(github.get('open_pull_requests', []))}")
    for check in status["compatibility"]:
        print("- compatibility: "
              f"{check['component']} core pin {check['observed_pin']} "
              f"vs {check['expected_core']} [{check['status']}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "ecosystem.yaml")
    parser.add_argument("--git-root", type=Path, default=ROOT.parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--github", action="store_true",
                        help="add non-authoritative GitHub release and open-PR observations")
    parser.add_argument("--validate", action="store_true",
                        help="validate the manifest without reading sibling repositories")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        if args.validate:
            print(f"ecosystem manifest OK: {len(manifest['components'])} component(s)")
            return 0
        status = collect_status(manifest, args.git_root)
        if args.github:
            add_github_observations(status)
    except (EcosystemError, OSError, yaml.YAMLError, tomllib.TOMLDecodeError) as exc:
        print(f"ecosystem error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_human(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
