"""Structured event log with a tamper-evident hash chain.

Every subsystem emits events through one funnel so a human can replay any run.
Events are appended as JSONL to runs/<run_id>/events.jsonl and optionally echoed
to stderr. Nothing in the harness prints ad hoc; observability is a boundary,
not an afterthought.

Each event carries `seq` and `prev` — the SHA-256 of the previous serialized
line (`genesis` for the first). Any post-hoc edit, deletion, or reorder breaks
every subsequent link, which `harnessie audit` detects (harness/audit.py).
Honest limit: a hash chain is tamper-evident, not tamper-proof; an attacker who
can rewrite the whole file can rewrite the whole chain. The defended failure is
silent partial edits. Reopening a log (resume) continues the chain from the
last line rather than restarting it.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GENESIS = "genesis"


def line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


@dataclass
class EventLog:
    run_dir: Path
    echo: bool = True
    _fh: Any = field(default=None, repr=False)
    _seq: int = field(default=0, repr=False)
    _prev: str = field(default=GENESIS, repr=False)

    def __post_init__(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path = self.run_dir / "events.jsonl"
        if path.exists():
            # Resume: continue the chain from the existing tail.
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._seq += 1
                    self._prev = line_hash(line)
        self._fh = path.open("a", encoding="utf-8")

    def emit(self, kind: str, **data: Any) -> dict:
        event = {"ts": time.time(), "seq": self._seq + 1, "prev": self._prev,
                 "kind": kind, **data}
        line = json.dumps(event, ensure_ascii=False, default=str)
        self._fh.write(line + "\n")
        self._fh.flush()
        self._seq += 1
        self._prev = line_hash(line)
        if self.echo:
            brief = {k: v for k, v in data.items() if k not in ("content", "messages")}
            print(f"[{kind}] {json.dumps(brief, default=str)[:240]}", file=sys.stderr)
        return event

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
