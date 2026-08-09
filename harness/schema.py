"""Versioned validation for Harnessie's public authoring contracts.

YAML is the authoring syntax; JSON Schema Draft 2020-12 is the executable,
portable contract. A missing schema_version is implicit v1 for every 0.8
document and remains accepted throughout the 1.x line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator


SCHEMA_VERSION = 1
KINDS = frozenset({
    "models", "cascade", "boundary", "approval-policy", "ownership", "workflow",
})
_PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_-]*)\}")


@dataclass(frozen=True, order=True)
class ValidationProblem:
    source: str
    path: str
    code: str
    message: str
    schema_version: int = SCHEMA_VERSION

    def render(self) -> str:
        location = f"{self.source}:{self.path}" if self.path else self.source
        return f"{location}: [{self.code}] {self.message}"


@dataclass
class ValidationReport:
    problems: list[ValidationProblem] = field(default_factory=list)
    documents: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


class ConfigurationError(ValueError):
    def __init__(self, problems: Iterable[ValidationProblem]):
        self.problems = sorted(problems)
        super().__init__("; ".join(problem.render() for problem in self.problems))


def _schema(kind: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"unknown schema kind {kind!r}")
    resource = files("harness.schemas.v1").joinpath(f"{kind}.schema.json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)
    return data


def _path(parts: Iterable[Any]) -> str:
    out = "$"
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out


def validate_data(data: Any, kind: str, source: str = "<memory>") -> list[ValidationProblem]:
    if isinstance(data, dict):
        version = data.get("schema_version", SCHEMA_VERSION)
        if isinstance(version, bool) or not isinstance(version, int):
            return [ValidationProblem(source, "$.schema_version", "schema.version_type",
                                      "schema_version must be the integer 1")]
        if version != SCHEMA_VERSION:
            return [ValidationProblem(source, "$.schema_version", "schema.version_unsupported",
                                      f"unsupported schema_version {version}; supported: 1")]
    validator = Draft202012Validator(_schema(kind))
    return sorted(
        ValidationProblem(
            source=source,
            path=_path(error.absolute_path),
            code=f"schema.{error.validator}",
            message=error.message,
        )
        for error in validator.iter_errors(data)
    )


def read_document(path: Path, kind: str) -> dict[str, Any]:
    source = str(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigurationError([
            ValidationProblem(source, "$", "document.missing", "file does not exist")
        ]) from None
    except (UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError([
            ValidationProblem(source, "$", "document.invalid_yaml",
                              f"invalid YAML: {type(exc).__name__}")
        ]) from None
    if data is None:
        data = {}
    problems = validate_data(data, kind, source)
    if problems:
        raise ConfigurationError(problems)
    return data


def _cross_problem(source: Path, path: str, code: str, message: str) -> ValidationProblem:
    return ValidationProblem(str(source), path, code, message)


def workflow_cross_checks(
    workflow: dict[str, Any], source: Path, *, tiers: set[str], policies: set[str],
    roles: set[str],
) -> list[ValidationProblem]:
    problems: list[ValidationProblem] = []
    phases = workflow.get("phases", [])
    names: list[str] = [phase["name"] for phase in phases]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in duplicates:
        problems.append(_cross_problem(
            source, "$.phases", "workflow.duplicate_phase", f"duplicate phase name {name!r}"))

    prior = {"goal"}
    for index, phase in enumerate(phases):
        prefix = f"$.phases[{index}]"
        agent = phase.get("agent", "implementer" if phase.get("mode") == "adversarial" else "orchestrator")
        if phase.get("mode") != "adversarial" and agent not in roles:
            problems.append(_cross_problem(
                source, f"{prefix}.agent", "workflow.unknown_role", f"unknown role {agent!r}"))
        cascade = phase.get("cascade")
        if cascade and cascade not in policies:
            problems.append(_cross_problem(
                source, f"{prefix}.cascade", "workflow.unknown_cascade",
                f"unknown cascade policy {cascade!r}; define it in config/cascade.yaml"))
        verify = phase.get("verify") or {}
        verifier = verify.get("verifier")
        if verifier and verifier not in roles:
            problems.append(_cross_problem(
                source, f"{prefix}.verify.verifier", "workflow.unknown_role",
                f"unknown verifier role {verifier!r}"))
        for pos_index, position in enumerate(phase.get("positions") or []):
            pos_agent = position.get("agent", "implementer")
            if pos_agent not in roles:
                problems.append(_cross_problem(
                    source, f"{prefix}.positions[{pos_index}].agent", "workflow.unknown_role",
                    f"unknown position role {pos_agent!r}"))
        unknown = sorted(set(_PLACEHOLDER.findall(phase["task"])) - prior)
        for placeholder in unknown:
            problems.append(_cross_problem(
                source, f"{prefix}.task", "workflow.unknown_placeholder",
                f"placeholder {{{placeholder}}} does not name goal or a prior phase"))
        prior.add(phase["name"])

    labels: dict[str, list[int]] = {}
    for index, phase in enumerate(phases):
        if phase.get("parallel"):
            labels.setdefault(phase["parallel"], []).append(index)
    for label, indices in labels.items():
        if indices != list(range(min(indices), max(indices) + 1)):
            problems.append(_cross_problem(
                source, "$.phases", "workflow.nonconsecutive_parallel",
                f"parallel group {label!r} must be consecutive"))
    return sorted(problems)


def validate_project(root: Path, paths: Iterable[Path] = ()) -> ValidationReport:
    root = root.resolve()
    report = ValidationReport()
    documents: dict[str, Any] = {}

    standard = [
        (root / "config/models.yaml", "models", True),
        (root / "config/cascade.yaml", "cascade", False),
        (root / "config/boundary.yaml", "boundary", False),
        (root / "OWNERSHIP.yaml", "ownership", False),
    ]
    requested = list(paths)
    if requested:
        for path in requested:
            resolved = path if path.is_absolute() else root / path
            name = resolved.name
            if name == "models.yaml":
                kind = "models"
            elif name == "cascade.yaml":
                kind = "cascade"
            elif name == "boundary.yaml":
                kind = "boundary"
            elif name == "OWNERSHIP.yaml":
                kind = "ownership"
            elif "approval" in name or "rehydration" in name:
                kind = "approval-policy"
            else:
                kind = "workflow"
            standard.append((resolved, kind, True))
    else:
        standard.extend((path, "workflow", True)
                        for path in sorted((root / "workflows").glob("*.yaml")))

    seen_paths: set[Path] = set()
    for path, kind, required in standard:
        path = path.resolve()
        if path in seen_paths:
            continue
        seen_paths.add(path)
        if not path.exists() and not required:
            continue
        try:
            data = read_document(path, kind)
        except ConfigurationError as exc:
            report.problems.extend(exc.problems)
            continue
        documents[str(path.resolve())] = (kind, data, path)
        report.documents += 1

    models = next((data for kind, data, _ in documents.values() if kind == "models"), {})
    cascade = next((data for kind, data, _ in documents.values() if kind == "cascade"), {})
    tiers = set(models.get("tiers", {}))
    policies = set(cascade.get("policies") or {})
    roles = {"orchestrator"}
    agents = root / "agents"
    if agents.exists():
        roles.update(path.stem for path in agents.rglob("*.md"))
    for kind, data, path in documents.values():
        if kind == "workflow":
            report.problems.extend(workflow_cross_checks(
                data, path, tiers=tiers, policies=policies, roles=roles))
        elif kind == "models":
            for task_class, route in data.get("routing", {}).items():
                if route["tier"] not in tiers:
                    report.problems.append(_cross_problem(
                        path, f"$.routing.{task_class}.tier", "models.unknown_tier",
                        f"tier {route['tier']!r} is not configured"))
        elif kind == "cascade":
            for name, policy in (data.get("policies") or {}).items():
                for index, tier in enumerate(policy["ladder"]):
                    if tiers and tier not in tiers:
                        report.problems.append(_cross_problem(
                            path, f"$.policies.{name}.ladder[{index}]", "cascade.unknown_tier",
                            f"tier {tier!r} is not configured"))
        elif kind == "boundary":
            grants_ref = data.get("rehydration_grants")
            if grants_ref:
                grants_path = (root / grants_ref).resolve()
                if grants_path.exists() and grants_path not in seen_paths:
                    try:
                        read_document(grants_path, "approval-policy")
                        report.documents += 1
                    except ConfigurationError as exc:
                        report.problems.extend(exc.problems)
    report.problems = sorted(set(report.problems))
    return report


def format_report(report: ValidationReport) -> str:
    if report.ok:
        return f"configuration valid: {report.documents} document(s), schema v1"
    return "configuration invalid:\n" + "\n".join(
        f"- {problem.render()}" for problem in report.problems)


__all__ = [
    "ConfigurationError", "KINDS", "SCHEMA_VERSION", "ValidationProblem",
    "ValidationReport", "format_report", "read_document", "validate_data",
    "validate_project", "workflow_cross_checks",
]
