#!/usr/bin/env python3
"""Generate and validate reviewed, hashed requirements. Validation is offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib import metadata
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("runtime", "dev", "release")


def inputs(root: Path) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text())
    tooling = json.loads((root / "requirements/tooling.json").read_text())
    return {"runtime": project["project"]["dependencies"],
            "dev": project["project"]["optional-dependencies"]["dev"],
            "build": project["build-system"], "tooling": tooling}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def input_digest(data: dict) -> str:
    return digest(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())


def validate(root: Path = ROOT) -> list[str]:
    problems = []
    try:
        data = inputs(root)
        manifest = json.loads((root / "requirements/manifest.json").read_text())
        if manifest.get("schema_version") != 1 or manifest.get("input_sha256") != input_digest(data):
            problems.append("dependency inputs changed; regenerate locks")
        if manifest.get("generator") != data["tooling"]:
            problems.append("generator or supported environments mismatch")
        if set(manifest.get("locks", {})) != set(PROFILES):
            problems.append("missing lock profile coverage")
        for profile in PROFILES:
            path = root / "requirements" / f"{profile}.txt"
            raw = path.read_bytes()
            if manifest.get("locks", {}).get(profile) != digest(raw):
                problems.append(f"{profile}: lock digest mismatch")
            seen = set()
            records = raw.decode().replace("\\\n", " ").splitlines()
            for line in records:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                requirement, *hashes = line.split("--hash=")
                # Only fully pinned registry requirements and SHA-256 hashes.
                match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)(\s*;[^\n]+)?\s*", requirement.strip())
                if not match or not hashes or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", h.strip()) for h in hashes):
                    problems.append(f"{profile}: unpinned requirement or invalid hash")
                    continue
                identity = (re.sub(r"[-_.]+", "-", match[1]).lower(), (match[3] or "").strip())
                if identity in seen:
                    problems.append(f"{profile}: duplicate or conflicting requirement")
                seen.add(identity)
            if not seen:
                problems.append(f"{profile}: empty lock")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(f"invalid lock set: {type(exc).__name__}")
    return problems


def generate(root: Path = ROOT, *, upgrade: bool = False) -> None:
    data = inputs(root)
    tooling = data["tooling"]
    version = subprocess.check_output(["uv", "--version"], text=True).split()[1]
    if version != tooling["generator_version"]:
        raise ValueError(f"requires uv {tooling['generator_version']}")
    # Stage the whole set; a failed resolution leaves existing locks untouched.
    with tempfile.TemporaryDirectory(prefix="harnessie-locks-") as temp:
        staged = Path(temp)
        hashes = {}
        for profile in PROFILES:
            requirements = list(data["runtime"])
            if profile != "runtime":
                requirements += data["dev"] + data["build"]["requires"]
            if profile == "release":
                requirements += tooling["release"]
            source = staged / f"{profile}.in"
            source.write_text("\n".join(requirements) + "\n")
            output = staged / f"{profile}.txt"
            existing = root / "requirements" / output.name
            if existing.exists():
                output.write_bytes(existing.read_bytes())
            command = ["uv", "pip", "compile", str(source), "--universal",
                       "--python-version", tooling["python"], "--generate-hashes",
                       "--no-header", "--no-annotate", "--only-binary", ":all:",
                       "--index-url", "https://pypi.org/simple", "--no-config",
                       "--output-file", str(output)]
            if profile != "runtime":
                command += ["--constraint", str(staged / "runtime.txt")]
            if upgrade:
                command.append("--upgrade")
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
            hashes[profile] = digest(output.read_bytes())
        manifest = {"schema_version": 1, "input_sha256": input_digest(data),
                    "generator": tooling, "locks": hashes}
        for profile in PROFILES:
            (root / "requirements" / f"{profile}.txt").write_bytes((staged / f"{profile}.txt").read_bytes())
        (root / "requirements/manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    problems = validate(root)
    if problems:
        raise ValueError("; ".join(problems))


def validate_installed(root: Path, profile: str) -> list[str]:
    """Check active pins in the interpreter doing the controlled build."""
    from packaging.requirements import Requirement
    problems = validate(root)
    if problems:
        return problems
    lines = (root / "requirements" / f"{profile}.txt").read_text().replace("\\\n", " ").splitlines()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement = Requirement(line.split("--hash=", 1)[0].strip())
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            problems.append(f"{requirement.name}: locked dependency is missing")
            continue
        if installed not in requirement.specifier:
            problems.append(f"{requirement.name}: installed version differs from lock")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--installed", choices=PROFILES)
    args = parser.parse_args()
    if args.upgrade and not args.update:
        parser.error("--upgrade requires --update")
    if args.update:
        generate(upgrade=args.upgrade)
    problems = validate_installed(ROOT, args.installed) if args.installed else validate()
    for problem in problems:
        print(problem)
    if not problems:
        print("dependency locks OK: runtime, dev, release; CPython 3.12 Linux/macOS")
    return 2 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
