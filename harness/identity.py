"""Harness identity: which harness produced a result.

A score or verdict describes the model inside one harness, not the model in
general, so every result names the harness beside the brain: the installed
version, the digest of the inward manifest that pins role prompts and
configuration, and a digest of the tool surface the brain was offered. The
tool-set digest covers names, parameter schemas, effects and role grants, so
a renamed tool or a widened grant changes the identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__
from .tools.registry import ToolRegistry

INWARD_MANIFEST = "INWARD_MANIFEST.yaml"
ABSENT = "absent"


def tool_set_sha256(registry: ToolRegistry) -> str:
    surface = [
        {
            "name": spec.name,
            "parameters": spec.parameters,
            "effects": spec.effects,
            "roles": sorted(spec.allowed_roles),
        }
        for spec in sorted(registry.tools.values(), key=lambda spec: spec.name)
    ]
    encoded = json.dumps(surface, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def inward_manifest_sha256(root: Path | None) -> str:
    """Digest of the project's inward manifest, or ``absent`` when the project
    predates it. Absence is reported, never substituted with a hash of nothing."""
    if root is None:
        return ABSENT
    path = root / INWARD_MANIFEST
    if not path.is_file():
        return ABSENT
    return hashlib.sha256(path.read_bytes()).hexdigest()


def harness_identity(root: Path | None, registry: ToolRegistry) -> dict[str, str]:
    return {
        "harness_version": __version__,
        "inward_manifest_sha256": inward_manifest_sha256(root),
        "tool_set_sha256": tool_set_sha256(registry),
    }


def format_identity_lines(identity: dict[str, str]) -> list[str]:
    """Report-header lines, one per field, in the same bullet style as the
    rest of the verification report."""
    return [
        f"- harness: harnessie {identity['harness_version']}",
        f"- inward manifest sha256: {identity['inward_manifest_sha256']}",
        f"- tool set sha256: {identity['tool_set_sha256']}",
    ]


__all__ = [
    "ABSENT",
    "INWARD_MANIFEST",
    "format_identity_lines",
    "harness_identity",
    "inward_manifest_sha256",
    "tool_set_sha256",
]
