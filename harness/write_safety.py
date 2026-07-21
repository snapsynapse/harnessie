"""Static write declarations for parallel phase preflight.

The 0.8 contract deliberately accepts a decidable path language instead of
pretending arbitrary glob intersection is safe to infer:

- `path/to/file.txt` declares one exact file.
- `path/to/directory/` declares that directory and every descendant.
- absolute paths, traversal, backslashes, and glob metacharacters are invalid.

Legacy parallel groups with no `writes` key retain their 0.7 behavior. Once
any phase in a group opts in, every phase must declare `writes` (an empty list
is the explicit read-only declaration).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import unicodedata


class WriteDeclarationError(ValueError):
    """A group partially opted in or used an ambiguous path declaration."""


@dataclass(frozen=True)
class WritePath:
    value: PurePosixPath
    directory: bool
    raw: str


@dataclass(frozen=True)
class WriteConflict:
    left_phase: str
    left: WritePath
    right_phase: str
    right: WritePath


def parse_write_path(raw: object) -> WritePath:
    if not isinstance(raw, str):
        raise WriteDeclarationError("write paths must be strings")
    if not raw or raw != raw.strip() or "\n" in raw or "\r" in raw:
        raise WriteDeclarationError("write paths must be non-empty single lines without surrounding whitespace")
    if "\\" in raw:
        raise WriteDeclarationError(f"write path {raw!r} must use POSIX '/' separators")
    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise WriteDeclarationError(f"write path {raw!r} contains control characters")
    if any(char in raw for char in "*?[]"):
        raise WriteDeclarationError(
            f"write path {raw!r} uses glob syntax; declare an exact file or a directory ending in '/'")
    directory = raw.endswith("/")
    value_text = raw.rstrip("/") if directory else raw
    segments = value_text.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise WriteDeclarationError(
            f"write path {raw!r} contains an empty, current, or parent segment")
    value = PurePosixPath(value_text)
    if value.is_absolute() or value_text in ("", ".") or \
            any(part in ("", ".", "..") for part in value.parts):
        raise WriteDeclarationError(
            f"write path {raw!r} must stay beneath the phase workspace")
    return WritePath(value=value, directory=directory, raw=raw)


def _comparison_parts(path: WritePath) -> tuple[str, ...]:
    # Cross-platform safety: macOS commonly compares names case-insensitively
    # and normalizes Unicode. Treat those aliases as conflicts everywhere so a
    # workflow admitted on Linux cannot collide when moved to a Mac.
    return tuple(unicodedata.normalize("NFC", part).casefold()
                 for part in path.value.parts)


def _contains(parent: WritePath, child: WritePath) -> bool:
    parent_parts = _comparison_parts(parent)
    child_parts = _comparison_parts(child)
    if not parent.directory:
        return parent_parts == child_parts
    return child_parts[:len(parent_parts)] == parent_parts


def overlap(left: WritePath, right: WritePath) -> bool:
    return _contains(left, right) or _contains(right, left)


def parallel_write_conflicts(phases: list[dict]) -> list[WriteConflict]:
    opted_in = ["writes" in phase for phase in phases]
    if not any(opted_in):
        return []
    if not all(opted_in):
        missing = [phase.get("name", "(unnamed)") for phase in phases
                   if "writes" not in phase]
        raise WriteDeclarationError(
            "every phase in an opted-in parallel group must declare writes; "
            f"missing: {missing}")

    declared: list[tuple[str, WritePath]] = []
    for phase in phases:
        values = phase.get("writes")
        if not isinstance(values, list):
            raise WriteDeclarationError(
                f"phase {phase.get('name')!r} writes must be a list")
        for raw in values:
            declared.append((phase["name"], parse_write_path(raw)))

    conflicts: list[WriteConflict] = []
    for index, (left_phase, left) in enumerate(declared):
        for right_phase, right in declared[index + 1:]:
            if left_phase != right_phase and overlap(left, right):
                conflicts.append(WriteConflict(
                    left_phase=left_phase, left=left,
                    right_phase=right_phase, right=right))
    return conflicts
