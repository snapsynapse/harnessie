"""Harnessie as a Harbor custom verifier, running on the host.

Harbor lets a job replace the in-sandbox `tests/test.sh` with a Python class
whose `verify()` runs in the Harbor process and reaches the task environment
through `self.environment`. That fits Harnessie: the verifier runs under
Harnessie's own OS sandbox on the host (Seatbelt on macOS, bubblewrap or
firejail on Linux) instead of needing one inside the task container, and
Harbor still receives a plain `VerifierResult`.

Use it from a job:

    harbor run -p examples/harbor-verifier/tasks -a oracle -e docker \\
      --verifier examples.harbor-verifier.harnessie_verifier:HarnessieVerifier

The module must be importable by the Harbor process; run from the repository
root or put the example directory on PYTHONPATH. Harbor is imported here, so
this file is only loadable where Harbor is installed; the exit-code mapping
it relies on lives in `harnessie_reward.py`, which has no such dependency.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from harbor.models.verifier.result import VerifierResult
from harbor.verifier.base import BaseVerifier

from harnessie_reward import (
    parse_checks,
    run_harnessie_verify,
    write_reward_files,
)

DEFAULT_CHECKS = (
    "python3 -c 'import calc; assert calc.add(2, 3) == 5'",
    "python3 -c \"import calc\nraised = False\ntry:\n    calc.mean([])\n"
    "except ValueError:\n    raised = True\nassert raised\"",
)


class HarnessieVerifier(BaseVerifier):
    """Download the agent's workspace, verify it with `harnessie verify
    --no-verifier` on the host, and return the mapped reward.

    Kwargs (via `--verifier-kwarg key=value`):
      workspace  path inside the environment to verify (default `/app`)
      claims     claims file relative to the task directory
                 (default `tests/claims.md`)
      checks     deterministic check commands separated by ` ;; `
                 (default: this example's two checks)
      python     interpreter that has harnessie installed
                 (default: the Harbor process's interpreter)
    """

    def __init__(self, *, workspace: str = "/app", claims: str = "tests/claims.md",
                 checks: str | list[str] | None = None,
                 python: str = sys.executable, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.workspace = workspace
        self.claims = claims
        self.checks = parse_checks(checks) if checks is not None else list(DEFAULT_CHECKS)
        self.python = python

    async def verify(self) -> VerifierResult:
        task_dir = Path(self.task.paths.tests_dir).parent
        claims_path = task_dir / self.claims
        if not claims_path.is_file():
            # No claims means nothing to verify against: unscorable, not zero.
            write_reward_files(Path(self.trial_paths.verifier_dir), 2)
            return VerifierResult(rewards=None)
        staging = Path(tempfile.mkdtemp(prefix="harnessie-harbor-"))
        try:
            target = staging / "workspace"
            target.mkdir()
            await self.environment.download_dir(self.workspace, target)
            # Some environments copy the directory itself into the target.
            nested = target / Path(self.workspace).name
            workspace = nested if nested.is_dir() and not any(
                p for p in target.iterdir() if p != nested) else target
            report_dir = Path(self.trial_paths.verifier_dir) / "harnessie"
            exit_code = run_harnessie_verify(workspace, claims_path, self.checks,
                                             report_dir, python=self.python)
            rewards = write_reward_files(Path(self.trial_paths.verifier_dir),
                                         exit_code, report_dir / "report.md")
            return VerifierResult(rewards=rewards)
        finally:
            shutil.rmtree(staging, ignore_errors=True)


__all__ = ["DEFAULT_CHECKS", "HarnessieVerifier"]
