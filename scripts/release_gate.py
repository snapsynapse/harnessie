#!/usr/bin/env python3
"""Compose the offline source gates and local package-install verification."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str]) -> None:
    print("+", " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, check=True)


def module_or_command(module: str, command: str) -> list[str]:
    if importlib.util.find_spec(module) is not None:
        return [sys.executable, "-m", module]
    resolved = shutil.which(command)
    if resolved is None:
        raise RuntimeError(
            f"{command} is required; install the project dev dependencies")
    return [resolved]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-core", action="store_true",
        help="skip pytest, evals, manifests, and ecosystem validation")
    args = parser.parse_args()
    try:
        if not args.skip_core:
            for command in (
                [sys.executable, "-m", "pytest", "-q"],
                [sys.executable, "-m", "harness.cli", "eval"],
                [sys.executable, "-m", "harness.cli", "verify-manifest"],
                [sys.executable, "-m", "harness.cli",
                 "verify-inward-manifest"],
                [sys.executable, "scripts/ecosystem_status.py", "--validate"],
            ):
                run(command)
        run([sys.executable, "scripts/build_docs_html.py", "--check"])
        run(["git", "diff", "--check"])

        with tempfile.TemporaryDirectory(
                prefix="harnessie-release-gate-") as raw:
            dist = Path(raw)
            run(module_or_command("build", "pyproject-build")
                + ["--outdir", str(dist)])
            run(module_or_command("twine", "twine")
                + ["check", *[str(path) for path in sorted(dist.iterdir())]])
            run([
                sys.executable,
                "scripts/check_release_artifacts.py",
                str(dist),
            ])
            wheels = sorted(dist.glob("*.whl"))
            if len(wheels) != 1:
                raise RuntimeError(
                    f"expected one wheel for smoke test, found {len(wheels)}")
            run([
                sys.executable,
                "scripts/fresh_install_smoke.py",
                str(wheels[0]),
            ])
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"release gate FAILED: {exc}", file=sys.stderr)
        return 2
    print("release gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
