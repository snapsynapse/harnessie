"""Guided first run for `harnessie init`.

The 0.6 "Ease" promise: someone who has never identified as a developer runs
one command, and the tool tells them plainly whether their machine is ready,
what (if anything) they need to set up, and proves itself with a run that costs
zero dollars. No config file to edit before the first green result.

Each check returns (ok, message) so the caller can render a readiness report
and decide an exit code. The mock verification runs the scaffolded eval
baseline on the no-network mock path, so the first run bills nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from . import sandbox

MIN_PYTHON = (3, 11)


def check_python() -> tuple[bool, str]:
    v = sys.version_info
    if (v.major, v.minor) >= MIN_PYTHON:
        return True, f"Python {v.major}.{v.minor} meets the 3.11+ requirement."
    return False, (f"Python {v.major}.{v.minor} is below the required 3.11. "
                   "Install a newer Python before running real workflows.")


def check_sandbox() -> tuple[bool, str]:
    name = sandbox.backend_name()
    if name:
        return True, f"OS sandbox backend detected: {name}. Shell work will be confined."
    return False, (
        "No usable OS sandbox backend on this platform. Shell-using workflows "
        "fail closed (they are blocked, never run unconfined) until you wire "
        "one — that is protection, not breakage. On Windows, use WSL2. The "
        "zero-dollar mock run below needs no sandbox.")


def key_guidance(config_path: Path) -> tuple[bool, str]:
    """Explain API-key setup from the scaffolded config. Keys are environment
    variables, never file contents."""
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return False, f"No config at {config_path}. Re-run init to scaffold it."
    if not isinstance(cfg, dict):
        return True, ("A custom config is in place. Review its tiers and export "
                      "any api_key_env it names as an environment variable "
                      "before a live run (never store a key in the file).")
    tiers = cfg.get("tiers", {})
    providers = {t.get("provider") for t in tiers.values()}
    if providers <= {"mock"}:
        return True, (
            "No API key needed: this scaffold uses the mock brain, so your first "
            "run costs zero dollars. To use a real brain later, edit "
            "config/models.yaml and export its key as an environment variable "
            "(never store a key in the file).")
    envs = sorted({t.get("api_key_env") for t in tiers.values() if t.get("api_key_env")})
    lines = ["The configured brains are real providers. Export each key as an "
             "environment variable before a live run (never store keys in the file):"]
    lines += [f"  export {e}=..." for e in envs] or ["  (no api_key_env set on any tier)"]
    return True, "\n".join(lines)


def run_mock_verification(root: Path) -> tuple[bool, str]:
    """Run the scaffolded eval baseline on the mock, no-network path. This is
    the green zero-dollar first run."""
    from .evals import run_eval_suite

    suite = root / "evals" / "baseline.yaml"
    if not suite.exists():
        return False, "No evals/baseline.yaml to run. Re-run init to scaffold it."
    scorecard = run_eval_suite(root, suite_path=suite)
    passed, total = scorecard["passed"], scorecard["total"]
    ok = total > 0 and passed == total
    if ok:
        return True, (f"Zero-dollar mock run: {passed}/{total} eval baseline "
                      "checks passed. Your harness works end to end and billed "
                      "nothing.")
    return False, (f"Zero-dollar mock run: only {passed}/{total} baseline checks "
                   "passed. Something in the scaffold is off; re-run init --force.")


def guided_first_run(root: Path) -> tuple[bool, str]:
    """Full guided readiness report. Returns (all_ready, text)."""
    checks = [
        ("Python", check_python()),
        ("Sandbox", check_sandbox()),
        ("API keys", key_guidance(root / "config" / "models.yaml")),
        ("First run", run_mock_verification(root)),
    ]
    lines = ["", "Guided first run — is this machine ready?", ""]
    for label, (ok, message) in checks:
        mark = "ok  " if ok else "note"
        lines.append(f"  [{mark}] {label}: {message}")
    # Only Python and the mock run are hard readiness gates; a missing sandbox
    # is an informational note (mock work still runs), and key guidance is
    # advisory. The first experience is "green" if the mock run is green.
    all_ready = check_python()[0] and run_mock_verification(root)[0]
    lines.append("")
    if all_ready:
        lines.append("You are ready. Run your first workflow:")
        lines.append("  harnessie run workflows/build-and-verify.yaml --goal "
                     "\"your goal here\"")
        lines.append("Then read what happened in plain language:")
        lines.append("  harnessie report <run_id>")
    else:
        lines.append("Fix the notes above, then re-run: harnessie init")
    return all_ready, "\n".join(lines)


__all__ = [
    "check_python",
    "check_sandbox",
    "key_guidance",
    "run_mock_verification",
    "guided_first_run",
    "MIN_PYTHON",
]
