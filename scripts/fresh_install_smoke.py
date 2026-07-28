#!/usr/bin/env python3
"""Install a built wheel into a fresh venv and exercise public CLI surfaces."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    argv: list[str],
    cwd: Path,
    *,
    expected: int = 0,
    contains: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"{' '.join(argv)} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}")
    if contains is not None and contains not in result.stdout:
        raise RuntimeError(
            f"{' '.join(argv)} output did not contain {contains!r}\n"
            f"{result.stdout}")
    return result


def smoke(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="harnessie-install-smoke-") as raw:
        temp = Path(raw)
        venv = temp / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)], check=True)
        python = venv / "bin" / "python"
        cli = venv / "bin" / "harnessie"
        run(
            [str(python), "-m", "pip", "install", str(wheel)],
            temp,
            contains="Successfully installed",
        )
        help_result = run([str(cli), "--help"], temp)
        for command in (
            "approve-maiden",
            "verify-inward-manifest",
            "verify-manifest",
        ):
            if command not in help_result.stdout:
                raise RuntimeError(f"installed CLI help omits {command}")

        run(
            [str(cli), "eval"],
            temp,
            expected=2,
            contains="refusing a vacuous pass",
        )
        project = temp / "project"
        run(
            [str(cli), "init", str(project), "--no-verify"],
            temp,
            contains="initialized Harnessie project",
        )
        run(
            [str(cli), "--root", str(project), "verify-inward-manifest"],
            temp,
            contains="inward manifest OK",
        )
        run(
            [str(cli), "--root", str(project), "eval"],
            temp,
            contains="eval scorecard:",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel")
    args = parser.parse_args()
    wheel = Path(args.wheel).resolve()
    if not wheel.is_file():
        print(f"wheel not found: {wheel}", file=sys.stderr)
        return 2
    try:
        smoke(wheel)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"fresh-install smoke FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"fresh-install smoke OK: {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
