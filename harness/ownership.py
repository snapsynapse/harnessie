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

Interpreter and check subprocesses receive a kernel-enforced read-only overlay
for operator lanes, other-agent lanes, and other agents' first-writer claims.
Patterns that cannot be translated conservatively make subprocess execution
fail closed rather than falling back to workspace-wide write access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePosixPath

import yaml

from .schema import read_document


_GLOB_META = frozenset("*?[")


@dataclass(frozen=True)
class OwnershipDecision:
    """Read-only explanation of one agent/path write decision."""

    allowed: bool
    agent: str
    path: str
    source: str
    reason: str
    owner: str | None = None
    pattern: str | None = None
    remedy: str | None = None


def _pattern_protection_root(pattern: str) -> PurePosixPath:
    """Return a conservative literal root covering every fnmatch match.

    `src/*` becomes `src`; `*.lock` becomes the workspace root. Exact paths
    remain exact. Protecting a broader root is safe: it may refuse a write,
    but can never admit one the ledger denies.
    """
    if not isinstance(pattern, str) or not pattern or pattern != pattern.strip():
        raise ValueError("ownership lane patterns must be non-empty strings without surrounding whitespace")
    if any(ord(char) < 32 or ord(char) == 127 for char in pattern):
        raise ValueError(f"ownership lane pattern {pattern!r} contains control characters")
    if "\\" in pattern or pattern.startswith("/"):
        raise ValueError(f"ownership lane pattern {pattern!r} must be a relative POSIX path")
    parts = pattern.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"ownership lane pattern {pattern!r} contains an unsafe path segment")
    literal: list[str] = []
    for part in parts:
        if any(char in part for char in _GLOB_META):
            break
        literal.append(part)
    return PurePosixPath(*literal) if literal else PurePosixPath(".")


def _confinement_roots(workspace: Path, patterns: list[str]) -> tuple[Path, ...]:
    ws = workspace.resolve()
    roots: set[Path] = set()
    for pattern in patterns:
        relative = _pattern_protection_root(pattern)
        root = (ws / relative).resolve()
        if not root.is_relative_to(ws):
            raise ValueError(f"ownership lane pattern {pattern!r} resolves outside the workspace")
        roots.add(root)
    ordered = sorted(roots, key=lambda path: (len(path.parts), str(path)))
    collapsed: list[Path] = []
    for root in ordered:
        if not any(root == parent or root.is_relative_to(parent)
                   for parent in collapsed):
            collapsed.append(root)
    return tuple(collapsed)


@dataclass
class OwnershipLedger:
    path: Path
    schema_version: int | None = None
    agent_lanes: dict[str, list[str]] = field(default_factory=dict)
    collaborative: list[str] = field(default_factory=list)
    operator: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)   # rel path -> owner
    claim_event: str = "ownership_claimed"

    @classmethod
    def load(cls, path: Path) -> "OwnershipLedger":
        led = cls(path=Path(path))
        if led.path.exists():
            data = read_document(led.path, "ownership")
            led.schema_version = data.get("schema_version")
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
        if self.schema_version is not None:
            data = {"schema_version": self.schema_version, **data}
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

    def _declared_decision(
            self, agent: str, rel: str) -> OwnershipDecision | None:
        for pattern in self.operator:
            if fnmatch(rel, pattern):
                reason = (f"{rel!r} is in an operator-owned lane; no agent may "
                          "write it. This is not negotiable at agent level.")
                return OwnershipDecision(
                    allowed=False, agent=agent, path=rel,
                    source="operator_lane", owner="operator", pattern=pattern,
                    reason=reason, remedy="operator_reassignment")
        for owner, globs in self.agent_lanes.items():
            for pattern in globs:
                if not fnmatch(rel, pattern):
                    continue
                if owner == agent:
                    return OwnershipDecision(
                        allowed=True, agent=agent, path=rel,
                        source="agent_lane", owner=owner, pattern=pattern,
                        reason="agent lane")
                reason = (f"{rel!r} is in the lane of agent {owner!r}. "
                          "You may not modify another agent's files; call "
                          "request_change to record what you need changed.")
                return OwnershipDecision(
                    allowed=False, agent=agent, path=rel,
                    source="agent_lane", owner=owner, pattern=pattern,
                    reason=reason, remedy="request_change")
        for pattern in self.collaborative:
            if fnmatch(rel, pattern):
                return OwnershipDecision(
                    allowed=True, agent=agent, path=rel,
                    source="collaborative_lane", pattern=pattern,
                    reason="collaborative lane")
        return None

    def explain_write(self, agent: str, rel: str) -> OwnershipDecision:
        """Explain the same decision used by ``check_write`` without writing."""
        declared = self._declared_decision(agent, rel)
        if declared is not None:
            return declared
        claimed = self.files.get(rel)
        if claimed is not None:
            if claimed == agent:
                return OwnershipDecision(
                    allowed=True, agent=agent, path=rel,
                    source="first_writer", owner=claimed,
                    reason="unowned (first writer claims)")
            reason = (f"{rel!r} is owned by agent {claimed!r} (first writer). "
                      "You may not modify another agent's files; call "
                      "request_change to record what you need changed.")
            return OwnershipDecision(
                allowed=False, agent=agent, path=rel,
                source="first_writer", owner=claimed,
                reason=reason, remedy="request_change")
        return OwnershipDecision(
            allowed=True, agent=agent, path=rel, source="unowned",
            reason="unowned (first writer claims)")

    def declared_write(self, agent: str, rel: str) -> tuple[bool, str] | None:
        """Evaluate operator/agent/collaborative lanes only.

        `None` means no declared lane matched and the caller may apply its own
        auto-claim semantics. Isolated parallel workspaces use this seam so
        declared authority remains enforced without conflating two physically
        separate `out.txt` files into one first-writer claim.
        """
        decision = self._declared_decision(agent, rel)
        return ((decision.allowed, decision.reason)
                if decision is not None else None)

    def check_write(self, agent: str, rel: str) -> tuple[bool, str]:
        """May `agent` write workspace-relative `rel`? (allowed, reason)."""
        decision = self.explain_write(agent, rel)
        return decision.allowed, decision.reason

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

    def confinement_roots(self, agent: str, workspace: Path) -> tuple[Path, ...]:
        """Paths a subprocess must see as read-only for this agent."""
        patterns = list(self.operator)
        for owner, globs in self.agent_lanes.items():
            if owner != agent:
                patterns.extend(globs)
        patterns.extend(path for path, owner in self.files.items()
                        if owner != agent)
        return _confinement_roots(workspace, patterns)


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

    def confinement_roots(self, agent: str, workspace: Path) -> tuple[Path, ...]:
        # Auto-claims describe the shared target workspace, not physically
        # distinct parallel phase workspaces. Declared lanes still apply.
        patterns = list(self.ledger.operator)
        for owner, globs in self.ledger.agent_lanes.items():
            if owner != agent:
                patterns.extend(globs)
        return _confinement_roots(workspace, patterns)
