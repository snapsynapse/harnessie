"""Graceful Boundaries conformance for the refusal surface.

Harnessie is not an HTTP service, so the GB numbered levels that assume HTTP
transport (a `/.well-known/limits` discovery endpoint, `RateLimit` headers)
are N/A by transport. What is in scope, per the GB FAQ ("the principles and
field names apply to any request-response protocol"), is the Level 1
structured-refusal shape and the Action Boundaries refusal vocabulary
(spec Appendix C.4). These tests are the falsifiable check behind the
conformance claim cited in GOVERNANCE.md.

The core assertion: every denial the harness emits carries the full
{error, boundary, detail, why} grammar, the `error` is a stable snake_case
code, and `why` explains a reason rather than restating the error.
"""

import dataclasses
import re

import pytest

from harness.tools.registry import (
    PermissionDenied,
    Refusal,
    ToolRegistry,
)
from harness.tools.builtin import register_builtin

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")

# The subset of GB Action Boundaries recommended refusal errors (spec
# Appendix C.4) that the harness's action surface is expected to speak.
GB_ACTION_VOCAB = {"authority_insufficient", "approval_required", "action_unsupported"}


def _registry(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    reg = ToolRegistry()
    register_builtin(reg, workspace=ws)
    return reg


def _assert_gb_level1(refusal: Refusal):
    """A refusal satisfies the GB Level 1 shape, transport-adapted."""
    assert isinstance(refusal, Refusal)
    for field in ("error", "boundary", "detail", "why"):
        value = getattr(refusal, field)
        assert isinstance(value, str) and value.strip(), f"empty {field}"
    assert SNAKE_CASE.match(refusal.error), f"error not snake_case: {refusal.error!r}"
    # why must be a reason, not a restatement of the error code
    assert refusal.why.strip().lower() != refusal.error.replace("_", " "), \
        "why restates the error instead of giving a reason"
    assert len(refusal.why) >= 15, f"why too thin to be a reason: {refusal.why!r}"


def test_refusal_type_makes_partial_refusals_impossible():
    # All four GB-aligned fields are required (no defaults), so a refusal
    # missing any field cannot be constructed. This is what makes the grammar
    # a guarantee rather than a convention.
    fields = {f.name: f for f in dataclasses.fields(Refusal)}
    assert set(fields) == {"error", "boundary", "detail", "why"}
    for f in fields.values():
        assert f.default is dataclasses.MISSING, f"{f.name} has a default"
        assert f.default_factory is dataclasses.MISSING, f"{f.name} has a factory"
    with pytest.raises(TypeError):
        Refusal(error="x")  # missing the other three


def test_unknown_tool_refusal_is_gb_shaped(tmp_path):
    result = _registry(tmp_path).dispatch("worker", "no_such_tool", {})
    assert result.ok is False
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "action_unsupported"


def test_role_denied_refusal_is_gb_shaped(tmp_path):
    with pytest.raises(PermissionDenied) as exc:
        _registry(tmp_path).dispatch("orchestrator", "write_file",
                                     {"path": "x.txt", "content": "y"})
    _assert_gb_level1(exc.value.refusal)
    assert exc.value.refusal.error == "authority_insufficient"


def test_consent_locked_refusal_is_gb_shaped(tmp_path):
    result = _registry(tmp_path).dispatch(
        "worker", "write_file", {"path": "x.txt", "content": "y"},
        side_effects_locked=True)
    assert result.ok is False
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "consent_required"


def test_approval_refusal_is_gb_shaped(tmp_path):
    result = _registry(tmp_path).dispatch("worker", "expire_fact", {"slug": "s"})
    assert result.ok is False
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "approval_required"


def test_secret_write_refusal_is_gb_shaped(tmp_path):
    result = _registry(tmp_path).dispatch(
        "worker", "write_file",
        {"path": "x.txt", "content": "key sk-ant-api03-AAAABBBBCCCCDDDD"})
    assert result.ok is False
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "secret_write_refused"


def test_workspace_jail_refusal_is_gb_shaped(tmp_path):
    result = _registry(tmp_path).dispatch(
        "worker", "write_file", {"path": "../escape.txt", "content": "y"})
    assert result.ok is False
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "workspace_jail_escape"


def test_shell_allowlist_refusal_is_gb_shaped(tmp_path):
    # run_shell denials return a Refusal wrapped as an ok=True observation the
    # agent can recover from (loop.py keys stall/refusal detection on the
    # refusal object, not on ok), but the GB grammar must still be complete.
    result = _registry(tmp_path).dispatch(
        "verifier", "run_shell", {"command": "python3 -c 1"})
    assert result.refusal is not None
    _assert_gb_level1(result.refusal)
    assert result.refusal.error == "command_not_allowlisted"


def test_gb_action_vocabulary_is_spoken_by_the_surface(tmp_path):
    # The three GB Action Boundaries refusal errors the harness commits to
    # must each appear on a real denial path, not just in a constant.
    reg = _registry(tmp_path)
    seen = set()
    seen.add(reg.dispatch("worker", "no_such_tool", {}).refusal.error)
    try:
        reg.dispatch("orchestrator", "write_file", {"path": "x", "content": "y"})
    except PermissionDenied as e:
        seen.add(e.refusal.error)
    seen.add(reg.dispatch("worker", "expire_fact", {"slug": "s"}).refusal.error)
    assert GB_ACTION_VOCAB <= seen, f"missing GB vocab: {GB_ACTION_VOCAB - seen}"
