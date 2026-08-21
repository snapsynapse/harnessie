#!/usr/bin/env python3
"""Executable proof that a second agent cannot overwrite the first agent."""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness.ownership import OwnershipLedger
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="harnessie-ownership-") as temp:
        root = Path(temp)
        workspace = root / "workspace"
        workspace.mkdir()
        ledger = OwnershipLedger.load(root / "OWNERSHIP.yaml")
        registry = ToolRegistry()
        register_builtin(registry, workspace=workspace, ledger=ledger)

        first = registry.dispatch(
            "worker", "write_file",
            {"path": "report.txt", "content": "alice-v1"}, agent="alice")
        overwrite = registry.dispatch(
            "worker", "write_file",
            {"path": "report.txt", "content": "bob-overwrite"}, agent="bob")
        artifact = (workspace / "report.txt").read_text(encoding="utf-8")

        blocked = (
            first.ok
            and not overwrite.ok
            and overwrite.refusal is not None
            and overwrite.refusal.error == "ownership_denied"
            and artifact == "alice-v1"
            and ledger.owner_of("report.txt") == "alice"
        )
        print("alice first write: ALLOWED" if first.ok else "alice first write: FAILED")
        print(
            "bob overwrite: DENIED (ownership_denied)"
            if overwrite.refusal and overwrite.refusal.error == "ownership_denied"
            else "bob overwrite: NOT DENIED")
        print(f"surviving artifact: {artifact}")
        print(f"recorded owner: {ledger.owner_of('report.txt')}")
        print(f"Golden Rule proof: {'PASS' if blocked else 'FAIL'}")
        return 0 if blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
