"""Map a `harnessie verify` exit code onto a Harbor reward, without Harbor.

Harnessie's verifier exits 0 (verified), 1 (failed) or 2 (cannot verify).
Harbor's verifier contract wants a number in `/logs/verifier/reward.txt`, or
no file at all. The one rule this module exists to keep is that exit 2 is
not a zero: a sandbox that died, a missing models file or an empty check
list mean nothing was verified, and a trainer must see that as unscorable,
not as a wrong answer. Writing `0` there would teach a policy that an
unverifiable result is a failure to avoid, which is a different lesson from
the one the task meant to teach.

This file imports nothing from Harbor so it can be tested on any machine;
`harnessie_verifier.py` wraps it for Harbor's host-side verifier interface
and `tasks/*/tests/test.sh` applies the same mapping inside a sandbox.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

EXIT_VERIFIED = 0
EXIT_FAILED = 1
EXIT_CANNOT_VERIFY = 2

REWARD_TEXT = "reward.txt"
DIAGNOSTIC_JSON = "harnessie-verify.json"


def reward_from_exit(exit_code: int) -> dict[str, float] | None:
    """`None` means unscorable. Only the two definite outcomes become numbers."""
    if exit_code == EXIT_VERIFIED:
        return {"reward": 1.0}
    if exit_code == EXIT_FAILED:
        return {"reward": 0.0}
    return None


def write_reward_files(verifier_dir: Path, exit_code: int,
                       report_path: Path | None = None) -> dict[str, float] | None:
    """Write Harbor's reward file for a definite outcome, or a diagnostic
    record and no reward file for an unscorable one. Returns the rewards."""
    verifier_dir.mkdir(parents=True, exist_ok=True)
    rewards = reward_from_exit(exit_code)
    diagnostic = {
        "verifier": "harnessie",
        "exit_code": exit_code,
        "outcome": {EXIT_VERIFIED: "verified", EXIT_FAILED: "failed"}.get(
            exit_code, "cannot_verify"),
        "scored": rewards is not None,
        "report": str(report_path) if report_path else None,
    }
    (verifier_dir / DIAGNOSTIC_JSON).write_text(
        json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8")
    if rewards is not None:
        (verifier_dir / REWARD_TEXT).write_text(
            f"{int(rewards['reward'])}\n", encoding="utf-8")
    return rewards


def verify_command(workspace: Path, claims: Path, checks: Sequence[str],
                   report_dir: Path, *, python: str = sys.executable) -> list[str]:
    """The exact `harnessie verify` invocation: deterministic checks only, no
    verifier model, so the reward never depends on a model's judgment."""
    argv = [python, "-m", "harness.cli", "verify",
            "--workspace", str(workspace), "--criteria", str(claims),
            "--no-verifier", "--report-dir", str(report_dir)]
    for check in checks:
        argv += ["--check", check]
    return argv


def run_harnessie_verify(workspace: Path, claims: Path, checks: Sequence[str],
                         report_dir: Path, *, python: str = sys.executable,
                         timeout_sec: int = 600) -> int:
    """Run the verifier as a subprocess and return its exit code. A crash or
    timeout of the verifier itself is reported as cannot-verify."""
    try:
        completed = subprocess.run(
            verify_command(workspace, claims, checks, report_dir, python=python),
            capture_output=True, text=True, timeout=timeout_sec, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return EXIT_CANNOT_VERIFY
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "verify-stdout.log").write_text(
        completed.stdout + completed.stderr, encoding="utf-8")
    return completed.returncode if completed.returncode in (
        EXIT_VERIFIED, EXIT_FAILED) else EXIT_CANNOT_VERIFY


def parse_checks(value: str | Sequence[str] | None) -> list[str]:
    """Harbor passes verifier kwargs as strings; several checks arrive
    separated by ` ;; `. A list passes through unchanged."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(" ;; ") if part.strip()]
    return [str(item) for item in value]


__all__ = [
    "EXIT_CANNOT_VERIFY",
    "EXIT_FAILED",
    "EXIT_VERIFIED",
    "parse_checks",
    "reward_from_exit",
    "run_harnessie_verify",
    "verify_command",
    "write_reward_files",
]
