"""Operator approval handling for approval-gated tools.

Policy is intentionally small: allow/deny lists of tool names, optionally
scoped to a workflow phase. No rule means deny. Explicit deny wins.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

import yaml


@dataclass(frozen=True)
class ApprovalRule:
    tool: str
    phase: str = ""

    def matches(self, phase: str, tool: str) -> bool:
        return self.tool == tool and (not self.phase or self.phase == phase)


@dataclass
class ApprovalPolicy:
    allow: list[ApprovalRule] = field(default_factory=list)
    deny: list[ApprovalRule] = field(default_factory=list)
    source: str = "policy-file"
    problems: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "ApprovalPolicy":
        problems: list[str] = []
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            return cls(source="policy-file", problems=[f"policy missing: {path}"])
        if not isinstance(data, dict):
            return cls(source="policy-file", problems=["policy root must be a mapping"])
        return cls(
            allow=_rules(data.get("allow"), "allow", problems),
            deny=_rules(data.get("deny"), "deny", problems),
            source="policy-file",
            problems=problems,
        )

    def decide(self, phase: str, tool: str, args: dict) -> bool | None:
        if self.problems:
            return False
        if any(rule.matches(phase, tool) for rule in self.deny):
            return False
        if any(rule.matches(phase, tool) for rule in self.allow):
            return True
        return None


def tty_approval(
    phase: str,
    tool: str,
    args: dict,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> bool | None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    if not stdin.isatty():
        return None
    stdout.write(f"Approve tool call {tool!r} in phase {phase!r}? [y/N] ")
    stdout.flush()
    answer = stdin.readline().strip().lower()
    return answer in {"y", "yes"}


def _rules(raw, key: str, problems: list[str]) -> list[ApprovalRule]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        problems.append(f"{key} must be a list")
        return []
    rules: list[ApprovalRule] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            problems.append(f"{key}[{i}] must be a mapping")
            continue
        tool = str(item.get("tool", "")).strip()
        phase = str(item.get("phase", "")).strip()
        if not tool:
            problems.append(f"{key}[{i}] must name a tool")
            continue
        rules.append(ApprovalRule(tool=tool, phase=phase))
    return rules


__all__ = ["ApprovalPolicy", "ApprovalRule", "tty_approval"]
