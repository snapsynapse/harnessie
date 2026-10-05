"""Harness identity: version, inward manifest digest, tool-set digest."""

import hashlib

from harness import __version__
from harness.identity import (
    ABSENT,
    format_identity_lines,
    harness_identity,
    inward_manifest_sha256,
    tool_set_sha256,
)
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry, ToolSpec


def _registry(tmp_path):
    reg = ToolRegistry()
    register_builtin(reg, workspace=tmp_path / "ws")
    return reg


def test_tool_set_digest_is_deterministic_across_registries(tmp_path):
    assert tool_set_sha256(_registry(tmp_path)) == tool_set_sha256(_registry(tmp_path))


def test_tool_set_digest_changes_when_the_surface_changes(tmp_path):
    base = _registry(tmp_path)
    before = tool_set_sha256(base)
    base.register(ToolSpec(name="extra", description="x",
                           parameters={"type": "object", "properties": {}},
                           fn=lambda: "ok", effects="read",
                           allowed_roles=frozenset({"worker"})))
    assert tool_set_sha256(base) != before


def test_tool_set_digest_covers_role_grants_not_descriptions(tmp_path):
    schema = {"type": "object", "properties": {}}
    a = ToolRegistry()
    a.register(ToolSpec(name="t", description="one", parameters=schema,
                        fn=lambda: "", effects="read",
                        allowed_roles=frozenset({"worker"})))
    b = ToolRegistry()
    b.register(ToolSpec(name="t", description="two", parameters=schema,
                        fn=lambda: "", effects="read",
                        allowed_roles=frozenset({"worker"})))
    c = ToolRegistry()
    c.register(ToolSpec(name="t", description="one", parameters=schema,
                        fn=lambda: "", effects="read",
                        allowed_roles=frozenset({"worker", "verifier"})))
    assert tool_set_sha256(a) == tool_set_sha256(b)
    assert tool_set_sha256(a) != tool_set_sha256(c)


def test_inward_manifest_digest_reports_absence_rather_than_hashing_nothing(tmp_path):
    assert inward_manifest_sha256(None) == ABSENT
    assert inward_manifest_sha256(tmp_path) == ABSENT
    manifest = tmp_path / "INWARD_MANIFEST.yaml"
    manifest.write_bytes(b"kind: harnessie-inward-manifest\n")
    assert inward_manifest_sha256(tmp_path) == hashlib.sha256(
        manifest.read_bytes()).hexdigest()


def test_identity_names_version_manifest_and_tool_set(tmp_path):
    identity = harness_identity(tmp_path, _registry(tmp_path))
    assert identity["harness_version"] == __version__
    assert identity["inward_manifest_sha256"] == ABSENT
    assert len(identity["tool_set_sha256"]) == 64
    lines = format_identity_lines(identity)
    assert lines[0] == f"- harness: harnessie {__version__}"
    assert lines[1].startswith("- inward manifest sha256: ")
    assert lines[2].startswith("- tool set sha256: ")
