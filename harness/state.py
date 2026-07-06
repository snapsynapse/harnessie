"""Run state: append-only JSONL journal per run.

Why a journal and not a status field: long autonomous runs crash, hit rate
limits, or get killed. An append-only journal means any run can be replayed to
its last good step and resumed, and every decision has an audit trail. Steps
carry idempotency keys so a resumed run does not re-execute completed work.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


@dataclass
class RunState:
    run_dir: Path
    completed: dict[str, Any] = field(default_factory=dict)  # step_key -> result

    @property
    def journal_path(self) -> Path:
        return self.run_dir / "journal.jsonl"

    @classmethod
    def open(cls, run_dir: Path) -> "RunState":
        """Create or resume. Resuming replays the journal so completed steps
        are skipped by callers checking has()."""
        state = cls(run_dir=run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        if state.journal_path.exists():
            for line in state.journal_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("kind") == "step_done":
                    state.completed[rec["step_key"]] = rec.get("result")
        return state

    def has(self, step_key: str) -> bool:
        return step_key in self.completed

    def result(self, step_key: str) -> Any:
        return self.completed[step_key]

    def record(self, step_key: str, result: Any) -> None:
        rec = {"ts": time.time(), "kind": "step_done",
               "step_key": step_key, "result": result}
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        self.completed[step_key] = result

    def note(self, kind: str, **data: Any) -> None:
        rec = {"ts": time.time(), "kind": kind, **data}
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
