"""Atomic artifact-volume ceilings for one phase and one workflow run.

The meter snapshots a phase workspace around each mutating operation. Accepted
changes consume three cumulative counters:

- files touched: unique file or symlink paths changed by the phase/run;
- edits applied: changed paths per accepted operation, so rewrites count;
- bytes written: resulting bytes for changed regular files and symlinks.

If a declared phase or run limit would be exceeded, the operation is rolled
back to its exact pre-operation snapshot and the caller must halt the phase.
Workflows without ``blast_radius`` declarations never construct a meter and
retain their prior behavior.
"""

from __future__ import annotations

import os
import shutil
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

from .events import EventLog

T = TypeVar("T")

COUNTERS = (
    "max_files_touched",
    "max_edits_applied",
    "max_bytes_written",
)


class BlastRadiusConfigError(ValueError):
    """A workflow declared an ambiguous or unsafe ceiling."""


@dataclass(frozen=True)
class BlastRadiusLimits:
    max_files_touched: int | None = None
    max_edits_applied: int | None = None
    max_bytes_written: int | None = None

    @property
    def active(self) -> bool:
        return any(getattr(self, name) is not None for name in COUNTERS)


def parse_limits(raw: object, location: str) -> BlastRadiusLimits:
    if raw is None:
        return BlastRadiusLimits()
    if not isinstance(raw, dict):
        raise BlastRadiusConfigError(
            f"{location} blast_radius must be a mapping")
    unknown = sorted(set(raw) - set(COUNTERS))
    if unknown:
        raise BlastRadiusConfigError(
            f"{location} blast_radius has unknown keys: {unknown}")
    values: dict[str, int | None] = {}
    for name in COUNTERS:
        value = raw.get(name)
        if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise BlastRadiusConfigError(
                f"{location} blast_radius {name} must be a non-negative integer")
        values[name] = value
    return BlastRadiusLimits(**values)


@dataclass(frozen=True)
class _Entry:
    kind: str
    data: bytes
    mode: int


@dataclass(frozen=True)
class _Snapshot:
    entries: dict[str, _Entry]
    directories: dict[str, int]


class UnsupportedWorkspaceEntry(RuntimeError):
    pass


def _snapshot(workspace: Path) -> _Snapshot:
    workspace.mkdir(parents=True, exist_ok=True)
    entries: dict[str, _Entry] = {}
    directories: dict[str, int] = {}
    for current, dirnames, filenames in os.walk(workspace, followlinks=False):
        current_path = Path(current)
        for dirname in list(dirnames):
            path = current_path / dirname
            rel = path.relative_to(workspace).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                entries[rel] = _Entry(
                    "symlink", os.readlink(path).encode("utf-8", errors="surrogateescape"),
                    stat.S_IMODE(info.st_mode))
                dirnames.remove(dirname)
            elif stat.S_ISDIR(info.st_mode):
                directories[rel] = stat.S_IMODE(info.st_mode)
            else:
                raise UnsupportedWorkspaceEntry(
                    f"unsupported workspace entry {rel!r}")
        for filename in filenames:
            path = current_path / filename
            rel = path.relative_to(workspace).as_posix()
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                entries[rel] = _Entry(
                    "file", path.read_bytes(), stat.S_IMODE(info.st_mode))
            elif stat.S_ISLNK(info.st_mode):
                entries[rel] = _Entry(
                    "symlink", os.readlink(path).encode("utf-8", errors="surrogateescape"),
                    stat.S_IMODE(info.st_mode))
            else:
                raise UnsupportedWorkspaceEntry(
                    f"unsupported workspace entry {rel!r}")
    return _Snapshot(entries=entries, directories=directories)


def _restore(workspace: Path, snapshot: _Snapshot) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    for child in list(workspace.iterdir()):
        mode = child.lstat().st_mode
        if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
            shutil.rmtree(child)
        else:
            child.unlink()
    for rel, mode in sorted(
            snapshot.directories.items(), key=lambda item: item[0].count("/")):
        path = workspace / rel
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)
    for rel, entry in snapshot.entries.items():
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if entry.kind == "file":
            path.write_bytes(entry.data)
            path.chmod(entry.mode)
        else:
            os.symlink(entry.data.decode("utf-8", errors="surrogateescape"), path)


@dataclass(frozen=True)
class _Delta:
    paths: frozenset[str]
    edits: int
    bytes_written: int


def _delta(before: _Snapshot, after: _Snapshot) -> _Delta:
    changed = frozenset(
        path for path in set(before.entries) | set(after.entries)
        if before.entries.get(path) != after.entries.get(path)
    )
    written = sum(
        len(after.entries[path].data)
        for path in changed
        if path in after.entries
    )
    return _Delta(paths=changed, edits=len(changed), bytes_written=written)


@dataclass(frozen=True)
class BlastRadiusExceeded(RuntimeError):
    scope: str
    counter: str
    count: int
    limit: int
    phase: str
    operation: str

    @property
    def detail(self) -> str:
        return (
            f"{self.scope} blast radius {self.counter}={self.count} "
            f"exceeded limit {self.limit} during {self.operation}; "
            "the operation was rolled back and the phase was halted"
        )

    def __str__(self) -> str:
        return self.detail


def _breach(limits: BlastRadiusLimits, files: int, edits: int,
            written: int) -> tuple[str, int, int] | None:
    counts = {
        "max_files_touched": files,
        "max_edits_applied": edits,
        "max_bytes_written": written,
    }
    for counter in COUNTERS:
        limit = getattr(limits, counter)
        if limit is not None and counts[counter] > limit:
            return counter, counts[counter], limit
    return None


@dataclass
class RunBlastRadius:
    limits: BlastRadiusLimits
    touched: set[str] = field(default_factory=set)
    edits: int = 0
    bytes_written: int = 0
    _lock: object = field(default_factory=threading.Lock, repr=False)

    def reserve(self, namespace: str, phase: str, delta: _Delta) -> (
            tuple[BlastRadiusExceeded | None, dict[str, int]]):
        keys = {f"{namespace}:{path}" for path in delta.paths}
        with self._lock:
            touched = self.touched | keys
            edits = self.edits + delta.edits
            written = self.bytes_written + delta.bytes_written
            violation = _breach(self.limits, len(touched), edits, written)
            if violation:
                counter, count, limit = violation
                return BlastRadiusExceeded(
                    "run", counter, count, limit, phase, ""), {
                        "files": len(self.touched),
                        "edits": self.edits,
                        "bytes": self.bytes_written,
                    }
            self.touched = touched
            self.edits = edits
            self.bytes_written = written
            return None, {
                "files": len(self.touched),
                "edits": self.edits,
                "bytes": self.bytes_written,
            }

    @classmethod
    def from_events(cls, limits: BlastRadiusLimits,
                    events: list[dict[str, Any]]) -> "RunBlastRadius":
        meter = cls(limits)
        for event in events:
            if event.get("kind") != "blast_radius_usage":
                continue
            phase = str(event.get("phase", ""))
            namespace = str(event.get("namespace", phase))
            meter.touched.update(
                f"{namespace}:{path}" for path in event.get("paths", []))
            meter.edits += int(event.get("edits_delta", 0))
            meter.bytes_written += int(event.get("bytes_delta", 0))
        return meter


@dataclass
class PhaseBlastRadius:
    phase: str
    namespace: str
    workspace: Path
    limits: BlastRadiusLimits
    run: RunBlastRadius
    events: EventLog
    touched: set[str] = field(default_factory=set)
    edits: int = 0
    bytes_written: int = 0
    _lock: object = field(default_factory=threading.Lock, repr=False)

    def apply(self, operation: str, action: Callable[[], T]) -> T:
        try:
            before = _snapshot(self.workspace)
        except UnsupportedWorkspaceEntry as exc:
            exceeded = BlastRadiusExceeded(
                "phase", "workspace_measurement", 1, 0,
                self.phase, operation)
            self.events.emit(
                "blast_radius_exceeded",
                phase=self.phase,
                scope="phase",
                counter="workspace_measurement",
                count=1,
                limit=0,
                operation=operation,
                rolled_back=False,
                detail=str(exc),
            )
            raise exceeded from exc
        try:
            result = action()
            after = _snapshot(self.workspace)
        except UnsupportedWorkspaceEntry as exc:
            _restore(self.workspace, before)
            exceeded = BlastRadiusExceeded(
                "phase", "workspace_measurement", 1, 0,
                self.phase, operation)
            self.events.emit(
                "blast_radius_exceeded",
                phase=self.phase,
                scope="phase",
                counter="workspace_measurement",
                count=1,
                limit=0,
                operation=operation,
                rolled_back=True,
                detail=str(exc),
            )
            raise exceeded from exc
        except Exception:
            _restore(self.workspace, before)
            raise
        delta = _delta(before, after)
        if not delta.paths:
            return result
        with self._lock:
            phase_touched = self.touched | set(delta.paths)
            phase_edits = self.edits + delta.edits
            phase_bytes = self.bytes_written + delta.bytes_written
            violation = _breach(
                self.limits, len(phase_touched), phase_edits, phase_bytes)
            exceeded: BlastRadiusExceeded | None = None
            if violation:
                counter, count, limit = violation
                exceeded = BlastRadiusExceeded(
                    "phase", counter, count, limit, self.phase, operation)
                run_totals = {
                    "files": len(self.run.touched),
                    "edits": self.run.edits,
                    "bytes": self.run.bytes_written,
                }
            else:
                exceeded, run_totals = self.run.reserve(
                    self.namespace, self.phase, delta)
                if exceeded is not None:
                    exceeded = BlastRadiusExceeded(
                        exceeded.scope, exceeded.counter, exceeded.count,
                        exceeded.limit, self.phase, operation)
            if exceeded is not None:
                _restore(self.workspace, before)
                self.events.emit(
                    "blast_radius_exceeded",
                    phase=self.phase,
                    scope=exceeded.scope,
                    counter=exceeded.counter,
                    count=exceeded.count,
                    limit=exceeded.limit,
                    operation=operation,
                    rolled_back=True,
                )
                raise exceeded
            self.touched = phase_touched
            self.edits = phase_edits
            self.bytes_written = phase_bytes
            self.events.emit(
                "blast_radius_usage",
                phase=self.phase,
                namespace=self.namespace,
                operation=operation,
                paths=sorted(delta.paths),
                edits_delta=delta.edits,
                bytes_delta=delta.bytes_written,
                phase_files=len(self.touched),
                phase_edits=self.edits,
                phase_bytes=self.bytes_written,
                run_files=run_totals["files"],
                run_edits=run_totals["edits"],
                run_bytes=run_totals["bytes"],
            )
        return result

    @classmethod
    def from_events(
        cls,
        phase: str,
        namespace: str,
        workspace: Path,
        limits: BlastRadiusLimits,
        run: RunBlastRadius,
        events_log: EventLog,
        history: list[dict[str, Any]],
    ) -> "PhaseBlastRadius":
        meter = cls(phase, namespace, workspace, limits, run, events_log)
        for event in history:
            if event.get("kind") != "blast_radius_usage" or \
                    event.get("phase") != phase:
                continue
            meter.touched.update(str(path) for path in event.get("paths", []))
            meter.edits += int(event.get("edits_delta", 0))
            meter.bytes_written += int(event.get("bytes_delta", 0))
        return meter
