"""Ownership lanes: agents own their files, not each other's.

Imported from Turnfile's OWNERSHIP.yaml + skill-ownership guard (PRD-033),
enforced at the write_file tool layer instead of a pre-commit hook.

The ledger lives at the project root — outside the workspace jail — so no
agent can edit its own permissions. The operator is the root owner: lane
declarations in the file always beat auto-claims, and editing the file is how
ownership is reassigned.

Lane kinds, checked in precedence order:
  operator lanes      no agent writes, ever
  agent lanes         only the named agent writes
  collaborative lanes any worker writes; no exclusive auto-claim
  files (auto)        first-writer-owns claims, auto-maintained
  unlisted            writable; the writer claims it

Glob semantics are fnmatch (a `*` crosses path separators), matched against
workspace-relative POSIX paths.

Honest limit (recorded, per the AIDR practice of stating what the runner
actually guarantees): enforcement happens in write_file dispatch. An
allowlisted interpreter can still write inside the workspace without a
per-file check; the OS sandbox confines writes to the workspace as a whole,
not per lane. Interpreter writes are visible in events and caught by
verifiers and audit, not blocked per file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml


@dataclass
class OwnershipLedger:
    path: Path
    agent_lanes: dict[str, list[str]] = field(default_factory=dict)
    collaborative: list[str] = field(default_factory=list)
    operator: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)   # rel path -> owner

    @classmethod
    def load(cls, path: Path) -> "OwnershipLedger":
        led = cls(path=Path(path))
        if led.path.exists():
            data = yaml.safe_load(led.path.read_text(encoding="utf-8")) or {}
            lanes = data.get("lanes", {}) or {}
            led.agent_lanes = {a: list(g) for a, g in (lanes.get("agent") or {}).items()}
            led.collaborative = list(lanes.get("collaborative") or [])
            led.operator = list(lanes.get("operator") or [])
            led.files = dict(data.get("files") or {})
        return led

    def save(self) -> None:
        data = {
            "lanes": {
                "agent": self.agent_lanes,
                "collaborative": self.collaborative,
                "operator": self.operator,
            },
            "files": self.files,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "# Ownership ledger — operator-owned. lanes: are declared by the\n"
            "# operator and always win; files: are first-writer auto-claims\n"
            "# maintained by the harness. Edit lanes to reassign; agents cannot\n"
            "# reach this file (it lives outside the workspace jail).\n"
            + yaml.safe_dump(data, sort_keys=True),
            encoding="utf-8")

    # -- queries ---------------------------------------------------------------

    def owner_of(self, rel: str) -> str | None:
        for agent, globs in self.agent_lanes.items():
            if any(fnmatch(rel, g) for g in globs):
                return agent
        return self.files.get(rel)

    def declared_write(self, agent: str, rel: str) -> tuple[bool, str] | None:
        """Evaluate operator/agent/collaborative lanes only.

        `None` means no declared lane matched and the caller may apply its own
        auto-claim semantics. Isolated parallel workspaces use this seam so
        declared authority remains enforced without conflating two physically
        separate `out.txt` files into one first-writer claim.
        """
        if any(fnmatch(rel, g) for g in self.operator):
            return False, (f"{rel!r} is in an operator-owned lane; no agent may "
                           "write it. This is not negotiable at agent level.")
        for owner, globs in self.agent_lanes.items():
            if any(fnmatch(rel, g) for g in globs):
                if owner == agent:
                    return True, "agent lane"
                return False, (f"{rel!r} is in the lane of agent {owner!r}. "
                               "You may not modify another agent's files; call "
                               "request_change to record what you need changed.")
        if any(fnmatch(rel, g) for g in self.collaborative):
            return True, "collaborative lane"
        return None

    def check_write(self, agent: str, rel: str) -> tuple[bool, str]:
        """May `agent` write workspace-relative `rel`? (allowed, reason)."""
        declared = self.declared_write(agent, rel)
        if declared is not None:
            return declared
        claimed = self.files.get(rel)
        if claimed and claimed != agent:
            return False, (f"{rel!r} is owned by agent {claimed!r} (first "
                           "writer). You may not modify another agent's files; "
                           "call request_change to record what you need changed.")
        return True, "unowned (first writer claims)"

    def claim(self, agent: str, rel: str) -> bool:
        """Record first-writer ownership. Returns True on a NEW claim.
        Collaborative-lane paths are never exclusively claimed."""
        if any(fnmatch(rel, g) for g in self.collaborative):
            return False
        if any(fnmatch(rel, g) for g in self.operator):
            return False
        if rel in self.files:
            return False
        self.files[rel] = agent
        self.save()
        return True

    def isolated_view(self) -> "IsolatedOwnershipView":
        return IsolatedOwnershipView(self)


@dataclass(frozen=True)
class IsolatedOwnershipView:
    """Declared-lane enforcement for a physically isolated phase workspace.

    Auto-claims are intentionally absent: two phase-local files with the same
    relative name are different artifacts. Static `writes` preflight owns
    cross-phase collision prevention when a workflow opts into that 0.8 seam.
    """
    ledger: OwnershipLedger

    def owner_of(self, rel: str) -> str | None:
        for agent, globs in self.ledger.agent_lanes.items():
            if any(fnmatch(rel, glob) for glob in globs):
                return agent
        return None

    def check_write(self, agent: str, rel: str) -> tuple[bool, str]:
        declared = self.ledger.declared_write(agent, rel)
        return declared if declared is not None else \
            (True, "isolated phase workspace")

    def claim(self, agent: str, rel: str) -> bool:
        return False
