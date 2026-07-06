"""Structured event log.

Every subsystem emits events through one funnel so a human can replay any run.
Events are appended as JSONL to runs/<run_id>/events.jsonl and optionally echoed
to stderr. Nothing in the harness prints ad hoc; observability is a boundary,
not an afterthought.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EventLog:
    run_dir: Path
    echo: bool = True
    _fh: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._fh = (self.run_dir / "events.jsonl").open("a", encoding="utf-8")

    def emit(self, kind: str, **data: Any) -> dict:
        event = {"ts": time.time(), "kind": kind, **data}
        self._fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()
        if self.echo:
            brief = {k: v for k, v in data.items() if k not in ("content", "messages")}
            print(f"[{kind}] {json.dumps(brief, default=str)[:240]}", file=sys.stderr)
        return event

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
