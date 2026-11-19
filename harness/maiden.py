"""Propose-only first execution for newly declared phase contracts.

A phase opts in by declaring ``phase_type``. The exact normalized phase
mapping is fingerprinted, so changing its task, role, permissions, or gate
creates a new contract even when the human-readable type label is reused.
Unapproved contracts execute against a staged clone of their target workspace.
Only the explicit ``approve-maiden`` operator command may promote that clone.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import verify_chain
from .events import EventLog
from .ownership import OwnershipLedger
from .state import RunState
from .trust_manifest import sha256_file

PHASE_TYPE_RE = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
PROPOSAL_VERSION = 1


class MaidenConfigError(ValueError):
    pass


@dataclass(frozen=True)
class MaidenApprovalResult:
    ok: bool
    message: str


def phase_fingerprint(phase: dict[str, Any]) -> tuple[str, str]:
    phase_type = phase.get("phase_type")
    if not isinstance(phase_type, str) or not PHASE_TYPE_RE.fullmatch(phase_type):
        raise MaidenConfigError(
            "phase_type must be a lowercase slug of letters, digits, "
            "hyphens, or underscores")
    if len(phase_type) > 64:
        raise MaidenConfigError("phase_type must be 64 characters or fewer")
    canonical = json.dumps(
        phase, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return phase_type, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def approved_fingerprints(root: Path) -> set[str]:
    """Read only clean, hash-chained approval events from prior runs."""
    approved: set[str] = set()
    runs = root / "runs"
    if not runs.exists():
        return approved
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        events_path = run_dir / "events.jsonl"
        if not events_path.exists() or not verify_chain(run_dir)["ok"]:
            continue
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("kind") == "maiden_approved":
                fingerprint = str(event.get("fingerprint", ""))
                if len(fingerprint) == 64:
                    approved.add(fingerprint)
    return approved


def workspace_sha256(root: Path) -> str:
    """Hash a workspace tree including relative paths, kinds, modes, and data."""
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(dirnames):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                _digest_entry(
                    digest, "symlink", rel, stat.S_IMODE(info.st_mode),
                    os.readlink(path).encode(
                        "utf-8", errors="surrogateescape"))
                dirnames.remove(name)
            elif stat.S_ISDIR(info.st_mode):
                _digest_entry(
                    digest, "directory", rel, stat.S_IMODE(info.st_mode), b"")
            else:
                raise ValueError(f"unsupported workspace entry {rel!r}")
        for name in sorted(filenames):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                _digest_file(digest, rel, path, info)
            elif stat.S_ISLNK(info.st_mode):
                _digest_entry(
                    digest, "symlink", rel, stat.S_IMODE(info.st_mode),
                    os.readlink(path).encode(
                        "utf-8", errors="surrogateescape"))
            else:
                raise ValueError(f"unsupported workspace entry {rel!r}")
    return digest.hexdigest()


def _digest_entry(
        digest: Any, kind: str, rel: str, mode: int, data: bytes) -> None:
    for value in (
            kind.encode("ascii"), rel.encode("utf-8"), str(mode).encode("ascii"),
            str(len(data)).encode("ascii"), data):
        digest.update(str(len(value)).encode("ascii") + b":" + value)


HASH_CHUNK_BYTES = 1 << 20
ABSENT = "absent"
# Regenerable OS and interpreter caches: never a phase product, so they are
# neither attributed to a phase nor bound on resume. Deliberately narrow:
# only regular files named .DS_Store and regular *.pyc / *.pyo files directly
# inside a __pycache__ directory. Anything else there is manifested.
_NOISE_FILES = frozenset({".DS_Store"})
_NOISE_CACHE_DIR = "__pycache__"
_NOISE_CACHE_SUFFIXES = (".pyc", ".pyo")
_NOFOLLOW_FLAGS = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                   | getattr(os, "O_NONBLOCK", 0))


def _stream_fd(fd: int, digest: Any) -> int:
    total = 0
    while True:
        chunk = os.read(fd, HASH_CHUNK_BYTES)
        if not chunk:
            return total
        digest.update(chunk)
        total += len(chunk)


def _digest_file(digest: Any, rel: str, path: Path, info: os.stat_result) -> None:
    """Frame a regular file exactly as _digest_entry would, streaming its
    bytes so memory stays bounded whatever the file size."""
    fd = os.open(path, _NOFOLLOW_FLAGS)
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino)
                != (info.st_dev, info.st_ino)):
            raise ValueError(f"workspace entry {rel!r} changed while hashing")
        for value in (b"file", rel.encode("utf-8"),
                      str(stat.S_IMODE(opened.st_mode)).encode("ascii"),
                      str(opened.st_size).encode("ascii")):
            digest.update(str(len(value)).encode("ascii") + b":" + value)
        digest.update(str(opened.st_size).encode("ascii") + b":")
        if _stream_fd(fd, digest) != opened.st_size:
            raise ValueError(f"workspace entry {rel!r} changed while hashing")
    finally:
        os.close(fd)


def _is_noise(rel: str, info: os.stat_result) -> bool:
    if not stat.S_ISREG(info.st_mode):
        return False
    parts = rel.split("/")
    if parts[-1] in _NOISE_FILES:
        return True
    return (len(parts) > 1 and parts[-2] == _NOISE_CACHE_DIR
            and parts[-1].endswith(_NOISE_CACHE_SUFFIXES))


def _special_entry(mode: int) -> str:
    for test, kind in ((stat.S_ISFIFO, "fifo"), (stat.S_ISSOCK, "socket"),
                       (stat.S_ISCHR, "char"), (stat.S_ISBLK, "block"),
                       (stat.S_ISDIR, "directory")):
        if test(mode):
            return f"special:{kind}"
    return "special:other"


def _entry_for(path: Path, info: os.stat_result) -> str:
    """One manifest entry. Non-regular files get a marker and are never
    opened, so a FIFO or socket cannot block or fail the snapshot."""
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(path).encode("utf-8", errors="surrogateescape")
        return "symlink:" + hashlib.sha256(target).hexdigest()
    if not stat.S_ISREG(info.st_mode):
        return _special_entry(info.st_mode)
    try:
        fd = os.open(path, _NOFOLLOW_FLAGS)
    except FileNotFoundError:
        return ABSENT
    except OSError:
        return "unreadable"
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            return _special_entry(opened.st_mode)
        digest = hashlib.sha256()
        _stream_fd(fd, digest)
    finally:
        os.close(fd)
    # A multiply linked file shares its inode with a path that may lie
    # outside the workspace, so the marker is part of the entry: swapping
    # an output for a hardlink with identical bytes and mode still differs.
    links = "links>1:" if opened.st_nlink > 1 else ""
    return f"file:{stat.S_IMODE(opened.st_mode):o}:{links}{digest.hexdigest()}"


def _raise(error: OSError) -> None:
    raise error


def workspace_manifest(root: Path,
                       cache: dict[str, tuple[tuple, str]] | None = None
                       ) -> dict[str, str]:
    """Map every workspace file (relative POSIX path) to a content entry.

    ``cache`` reuses a digest while a file's inode, size, mode and change
    times are unchanged, so snapshots around every phase cost one stat per
    unchanged file. Directories are structure, not content, and are omitted.
    """
    manifest: dict[str, str] = {}
    seen: set[str] = set()
    for current, dirnames, filenames in os.walk(
            root, followlinks=False, onerror=_raise):
        current_path = Path(current)
        for name in sorted(dirnames):
            path = current_path / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                manifest[path.relative_to(root).as_posix()] = _entry_for(
                    path, info)
                dirnames.remove(name)
        for name in filenames:
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if _is_noise(rel, info):
                continue
            signature = (info.st_dev, info.st_ino, info.st_size,
                         info.st_mtime_ns, info.st_ctime_ns, info.st_mode,
                         info.st_nlink)
            cached = cache.get(rel) if cache is not None else None
            if (cached is not None and cached[0] == signature
                    and stat.S_ISREG(info.st_mode)):
                entry = cached[1]
            else:
                entry = _entry_for(path, info)
                if cache is not None and stat.S_ISREG(info.st_mode):
                    cache[rel] = (signature, entry)
            if entry != ABSENT:
                manifest[rel] = entry
            seen.add(rel)
    if cache is not None:
        for stale in set(cache) - seen:
            del cache[stale]
    return manifest


def path_entry(root: Path, rel: str) -> str:
    """The current manifest entry for one path, without walking the tree.
    A parent that is not a real directory (a swapped-in symlink) never
    yields the recorded entry, so the bytes behind it are not trusted."""
    parts = rel.split("/")
    if not rel or rel.startswith("/") or any(
            part in ("", ".", "..") for part in parts):
        return "special:invalid-path"
    current = root
    for part in parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return ABSENT
        if not stat.S_ISDIR(info.st_mode):
            return "special:parent-not-directory"
    path = current / parts[-1]
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ABSENT
    return _entry_for(path, info)


def manifest_changes(before: dict[str, str],
                     after: dict[str, str]) -> dict[str, str]:
    """Paths whose entry differs, mapped to the after entry (ABSENT when
    the path was removed)."""
    return {rel: after.get(rel, ABSENT)
            for rel in sorted(set(before) | set(after))
            if before.get(rel) != after.get(rel)}


def clone_workspace(source: Path, destination: Path) -> None:
    """Replace destination with an exact-enough staged copy of source."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir() and not child.is_symlink():
            shutil.copytree(child, target, symlinks=True, copy_function=shutil.copy2)
        elif child.is_symlink():
            target.symlink_to(os.readlink(child), target_is_directory=child.is_dir())
        else:
            shutil.copy2(child, target, follow_symlinks=False)


def proposal_paths(
        root: Path, run_dir: Path,
        fingerprint: str) -> tuple[Path, Path, Path]:
    proposal_dir = run_dir / "maiden" / fingerprint
    staged_workspace = (
        root / ".maiden" / run_dir.name / fingerprint / "workspace")
    return (
        proposal_dir,
        staged_workspace,
        proposal_dir / "proposal.json",
    )


def write_proposal(
    root: Path,
    run_dir: Path,
    phase: dict[str, Any],
    fingerprint: str,
    baseline_sha256: str,
    staged_sha256: str,
    report: str,
    workflow: str,
    workflow_sha256: str,
    ownership_sha256: str,
    proposed_ownership_sha256: str,
) -> Path:
    phase_type = str(phase["phase_type"])
    proposal_dir, staged_workspace, proposal_path = proposal_paths(
        root, run_dir, fingerprint)
    proposal = {
        "version": PROPOSAL_VERSION,
        "phase": phase["name"],
        "phase_type": phase_type,
        "fingerprint": fingerprint,
        "baseline_sha256": baseline_sha256,
        "staged_sha256": staged_sha256,
        "staged_workspace": str(staged_workspace.relative_to(root)),
        "report": report,
        "report_sha256": text_sha256(report),
        "workflow": workflow,
        "workflow_sha256": workflow_sha256,
        "ownership_sha256": ownership_sha256,
        "proposed_ownership_sha256": proposed_ownership_sha256,
    }
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(
        json.dumps(proposal, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return proposal_path


def approve_maiden(
        root: Path, run_id: str, phase_name: str) -> MaidenApprovalResult:
    root = root.resolve()
    run_dir = root / "runs" / run_id
    if not run_dir.is_dir():
        return MaidenApprovalResult(False, f"run not found: {run_id}")
    chain = verify_chain(run_dir)
    if not chain["ok"]:
        return MaidenApprovalResult(
            False, "run audit chain is broken; maiden approval refused")

    matches: list[tuple[Path, dict[str, Any]]] = []
    for proposal_path in (run_dir / "maiden").glob("*/proposal.json"):
        try:
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if proposal.get("phase") == phase_name:
            matches.append((proposal_path, proposal))
    if len(matches) != 1:
        return MaidenApprovalResult(
            False,
            f"expected one maiden proposal for phase {phase_name!r}, "
            f"found {len(matches)}")

    proposal_path, proposal = matches[0]
    if proposal.get("version") != PROPOSAL_VERSION:
        return MaidenApprovalResult(False, "unsupported maiden proposal version")
    fingerprint = str(proposal.get("fingerprint", ""))
    if proposal_path.parent.name != fingerprint or len(fingerprint) != 64:
        return MaidenApprovalResult(False, "maiden proposal identity is invalid")

    existing_events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(
            encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(
            event.get("kind") == "maiden_approved"
            and event.get("fingerprint") == fingerprint
            for event in existing_events):
        return MaidenApprovalResult(
            True, f"maiden output already approved for {phase_name}")
    proposed_events = [
        event for event in existing_events
        if event.get("kind") == "maiden_proposed"
        and event.get("fingerprint") == fingerprint
    ]
    if len(proposed_events) != 1:
        return MaidenApprovalResult(
            False, "maiden proposal has no unique audit event")
    proposed = proposed_events[0]
    compared = (
        "phase", "phase_type", "fingerprint", "baseline_sha256",
        "staged_sha256", "workflow_sha256", "ownership_sha256",
        "proposed_ownership_sha256", "report_sha256", "staged_workspace")
    if any(proposed.get(key) != proposal.get(key) for key in compared):
        return MaidenApprovalResult(
            False, "maiden proposal does not match its audit event")

    _proposal_dir, staged, _expected_proposal = proposal_paths(
        root, run_dir, fingerprint)
    target = root / "workspace"
    ownership_path = root / "OWNERSHIP.yaml"
    current_ownership_sha = (
        sha256_file(ownership_path) if ownership_path.is_file() else "")
    if current_ownership_sha != proposal.get("ownership_sha256"):
        return MaidenApprovalResult(
            False, "ownership ledger changed after the proposal; promotion refused")
    if not staged.is_dir():
        return MaidenApprovalResult(False, "staged maiden workspace is missing")
    if workspace_sha256(staged) != proposal.get("staged_sha256"):
        return MaidenApprovalResult(
            False, "staged maiden output changed after verification")
    if workspace_sha256(target) != proposal.get("baseline_sha256"):
        return MaidenApprovalResult(
            False, "workspace changed after the proposal; promotion refused")

    backup = staged.parent / "approval-backup"
    clone_workspace(target, backup)
    ownership_backup = (
        ownership_path.read_bytes() if ownership_path.is_file() else None)
    proposed_ownership = staged.parent / "OWNERSHIP.yaml"
    if not proposed_ownership.is_file():
        return MaidenApprovalResult(
            False, "staged maiden ownership ledger is missing")
    if sha256_file(proposed_ownership) != proposal.get(
            "proposed_ownership_sha256"):
        return MaidenApprovalResult(
            False, "staged maiden ownership ledger changed after verification")
    if text_sha256(str(proposal.get("report", ""))) != proposal.get(
            "report_sha256"):
        return MaidenApprovalResult(
            False, "staged maiden report changed after verification")
    before_ledger = OwnershipLedger.load(ownership_path)
    after_ledger = OwnershipLedger.load(proposed_ownership)
    try:
        before_manifest = workspace_manifest(target)
    except OSError as exc:
        return MaidenApprovalResult(
            False, f"workspace could not be inventoried; promotion refused: {exc}")
    try:
        clone_workspace(staged, target)
        ownership_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proposed_ownership, ownership_path)
    except Exception as exc:
        clone_workspace(backup, target)
        if ownership_backup is None:
            if ownership_path.exists():
                ownership_path.unlink()
        else:
            ownership_path.write_bytes(ownership_backup)
        return MaidenApprovalResult(
            False, f"maiden promotion failed and was rolled back: {exc}")

    events = EventLog(run_dir, echo=False)
    events.emit(
        "maiden_approved",
        phase=phase_name,
        phase_type=proposal.get("phase_type"),
        fingerprint=fingerprint,
        proposal=str(proposal_path.relative_to(root)),
        staged_sha256=proposal.get("staged_sha256"),
    )
    events.emit(
        "phase_done",
        phase=phase_name,
        status="passed",
        source="maiden-approval",
        spent_usd=0.0,
        spent_tokens=0,
    )
    for path, owner in sorted(after_ledger.files.items()):
        if before_ledger.files.get(path) != owner:
            events.emit(
                "ownership_claimed", agent=owner, path=path,
                source="maiden-approval")
    events.close()
    # The acceptance keeps the binding the runner journaled with the staged
    # proposal and records the files promotion produced, so a resume reuses
    # it only under the same contract and over exactly those bytes.
    try:
        outputs = manifest_changes(before_manifest, workspace_manifest(target))
    except OSError:
        outputs = None
    state = RunState.open(run_dir)
    staged_record = state.completed.get(f"phase:{phase_name}")
    state.record(
        f"phase:{phase_name}",
        {"status": "passed", "report": proposal.get("report", ""),
         "binding": (staged_record.get("binding")
                     if isinstance(staged_record, dict) else None),
         "outputs": outputs})
    return MaidenApprovalResult(
        True,
        f"approved maiden output for {phase_name}; promoted staged artifacts")


__all__ = [
    "MaidenApprovalResult",
    "MaidenConfigError",
    "approve_maiden",
    "approved_fingerprints",
    "clone_workspace",
    "manifest_changes",
    "path_entry",
    "phase_fingerprint",
    "proposal_paths",
    "text_sha256",
    "workspace_manifest",
    "workspace_sha256",
    "write_proposal",
]
