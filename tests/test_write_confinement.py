"""SEC-20261118-001: write_file replaces only the authorized directory entry.

A hardlink alias inside an allowed lane must never let a direct write change
an operator-lane inode, another agent's claimed inode, or an inode outside
the workspace. Writes go to a same-directory exclusive temporary file and
atomically replace the entry; directory traversal is anchored and refuses
symlinks swapped in after the authorization check. All fixtures are
temporary and synthetic.
"""

import json
import os
import stat

import pytest

from harness.events import EventLog
from harness.ownership import OwnershipLedger
from harness.tools import builtin
from harness.tools.builtin import register_builtin
from harness.tools.registry import ToolRegistry


def _env(tmp_path, ledger=None, events=None):
    ws = tmp_path / "ws"
    ws.mkdir()
    reg = ToolRegistry()
    led = ledger if ledger is not None else OwnershipLedger(
        path=tmp_path / "OWNERSHIP.yaml", operator=["frozen/*"])
    register_builtin(reg, workspace=ws, ledger=led, events=events)
    return reg, ws, led


def _write(reg, path, content="changed by an otherwise allowed path", agent="bob"):
    return reg.dispatch("worker", "write_file", {"path": path, "content": content},
                        agent=agent)


def _leftovers(directory):
    return [p.name for p in directory.iterdir() if p.name.startswith(".harnessie-write-")]


# -- hardlink aliases ---------------------------------------------------------

def test_hardlink_to_operator_lane_leaves_protected_inode_unchanged(tmp_path):
    reg, ws, _ = _env(tmp_path)
    (ws / "frozen").mkdir()
    protected = ws / "frozen" / "value.txt"
    protected.write_text("original")
    os.link(protected, ws / "alias.txt")
    before = os.stat(protected)
    res = _write(reg, "alias.txt")
    assert res.ok, res.content
    assert protected.read_text() == "original"
    after = os.stat(protected)
    assert (after.st_ino, after.st_size, after.st_mtime_ns) == (
        before.st_ino, before.st_size, before.st_mtime_ns)
    assert (ws / "alias.txt").read_text() == "changed by an otherwise allowed path"
    assert os.stat(ws / "alias.txt").st_ino != before.st_ino


def test_hardlink_to_other_agents_claim_leaves_that_inode_unchanged(tmp_path):
    reg, ws, led = _env(tmp_path)
    owned = ws / "alice.txt"
    assert _write(reg, "alice.txt", "alice original", agent="alice").ok
    assert led.owner_of("alice.txt") == "alice"
    os.link(owned, ws / "bob-alias.txt")
    res = _write(reg, "bob-alias.txt", agent="bob")
    assert res.ok, res.content
    assert owned.read_text() == "alice original"


def test_hardlink_to_file_outside_workspace_leaves_it_unchanged(tmp_path):
    reg, ws, _ = _env(tmp_path)
    external = tmp_path / "outside-workspace.txt"
    external.write_text("original")
    os.link(external, ws / "external-alias.txt")
    res = _write(reg, "external-alias.txt")
    assert res.ok, res.content
    assert external.read_text() == "original"
    assert os.stat(external).st_nlink == 1


def test_legitimate_hardlink_in_own_lane_is_detached_and_reported(tmp_path):
    log = EventLog(tmp_path / "run", echo=False)
    reg, ws, _ = _env(tmp_path, events=log)
    first = ws / "notes.txt"
    first.write_text("v1")
    os.link(first, ws / "notes-copy.txt")
    res = _write(reg, "notes.txt", "v2")
    log.close()
    assert res.ok, res.content
    assert first.read_text() == "v2"
    assert (ws / "notes-copy.txt").read_text() == "v1"
    assert os.stat(first).st_nlink == 1
    records = [json.loads(line) for line in
               (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    detached = [r for r in records if r["kind"] == "hardlink_detached"]
    assert detached and detached[0]["path"] == "notes.txt"
    assert detached[0]["links"] == 2


# -- symlinks and races -------------------------------------------------------

def test_symlink_target_into_operator_lane_is_denied(tmp_path):
    reg, ws, _ = _env(tmp_path)
    (ws / "frozen").mkdir()
    (ws / "frozen" / "value.txt").write_text("original")
    (ws / "link.txt").symlink_to(ws / "frozen" / "value.txt")
    res = _write(reg, "link.txt")
    assert not res.ok
    assert res.refusal.error == "operator_lane_denied"
    assert (ws / "frozen" / "value.txt").read_text() == "original"


def test_symlink_target_outside_workspace_is_jailed(tmp_path):
    reg, ws, _ = _env(tmp_path)
    external = tmp_path / "outside.txt"
    external.write_text("original")
    (ws / "link.txt").symlink_to(external)
    res = _write(reg, "link.txt")
    assert not res.ok
    assert res.refusal.error == "workspace_jail_escape"
    assert external.read_text() == "original"


@pytest.mark.parametrize("points_to,error", [
    ("outside", "workspace_jail_escape"),
    ("frozen", "operator_lane_denied"),
])
def test_symlinked_parent_is_resolved_before_authorization(tmp_path, points_to, error):
    reg, ws, _ = _env(tmp_path)
    (ws / "frozen").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (ws / "dirlink").symlink_to(outside if points_to == "outside" else ws / "frozen")
    res = _write(reg, "dirlink/new.txt")
    assert not res.ok
    assert res.refusal.error == error
    assert not (outside / "new.txt").exists()
    assert not (ws / "frozen" / "new.txt").exists()


class _SwappingLedger(OwnershipLedger):
    """Authorizes, then lets an attacker swap the path before the write."""

    def __init__(self, swap, **kw):
        super().__init__(**kw)
        self._swap = swap

    def check_write(self, agent, rel):
        allowed = super().check_write(agent, rel)
        self._swap()
        return allowed


def test_parent_replaced_by_symlink_after_check_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    ws_dir = tmp_path / "ws"

    def swap():
        (ws_dir / "sub").rename(tmp_path / "sub-moved")
        (ws_dir / "sub").symlink_to(outside)

    led = _SwappingLedger(swap, path=tmp_path / "OWNERSHIP.yaml")
    reg, ws, _ = _env(tmp_path, ledger=led)
    (ws / "sub").mkdir()
    res = _write(reg, "sub/new.txt")
    assert not res.ok
    assert res.refusal.error == "write_target_changed"
    assert res.refusal.boundary == "jail"
    assert list(outside.iterdir()) == []


def test_target_replaced_by_symlink_after_check_is_refused(tmp_path):
    external = tmp_path / "outside.txt"
    external.write_text("original")
    ws_dir = tmp_path / "ws"

    def swap():
        (ws_dir / "plain.txt").unlink()
        (ws_dir / "plain.txt").symlink_to(external)

    led = _SwappingLedger(swap, path=tmp_path / "OWNERSHIP.yaml")
    reg, ws, _ = _env(tmp_path, ledger=led)
    (ws / "plain.txt").write_text("in workspace")
    res = _write(reg, "plain.txt")
    assert not res.ok
    assert res.refusal.error == "write_target_changed"
    assert external.read_text() == "original"
    assert _leftovers(ws) == []


# -- positive controls and permissions ------------------------------------------

def _with_umask(mask):
    @pytest.fixture
    def fixture():
        previous = os.umask(mask)
        try:
            yield
        finally:
            os.umask(previous)
    return fixture


standard_umask = _with_umask(0o022)
private_umask = _with_umask(0o077)


def test_new_file_in_new_directories_gets_safe_mode(tmp_path, standard_umask):
    reg, ws, _ = _env(tmp_path)
    res = _write(reg, "pkg/sub/mod.py", "print('ok')\n")
    assert res.ok, res.content
    target = ws / "pkg" / "sub" / "mod.py"
    assert target.read_text() == "print('ok')\n"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o644
    assert _leftovers(ws / "pkg" / "sub") == []


def test_new_file_respects_process_umask(tmp_path, private_umask):
    reg, ws, _ = _env(tmp_path)
    res = _write(reg, "secret-notes/plan.txt", "private\n")
    assert res.ok, res.content
    assert stat.S_IMODE(os.stat(ws / "secret-notes" / "plan.txt").st_mode) == 0o600
    assert stat.S_IMODE(os.stat(ws / "secret-notes").st_mode) == 0o700


def test_detached_hardlink_alias_respects_process_umask(tmp_path, private_umask):
    reg, ws, _ = _env(tmp_path)
    first = ws / "notes.txt"
    first.write_text("v1")
    os.chmod(first, 0o644)
    os.link(first, ws / "notes-copy.txt")
    res = _write(reg, "notes.txt", "v2")
    assert res.ok, res.content
    assert stat.S_IMODE(os.stat(first).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(ws / "notes-copy.txt").st_mode) == 0o644


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses write permission")
@pytest.mark.parametrize("linked", [False, True])
def test_read_only_existing_target_is_refused(tmp_path, linked):
    reg, ws, _ = _env(tmp_path)
    target = ws / "locked.txt"
    target.write_text("original")
    if linked:
        os.link(target, ws / "locked-alias.txt")
    os.chmod(target, 0o444)
    before = os.stat(target)
    res = _write(reg, "locked.txt", "replaced")
    assert not res.ok
    assert res.refusal.error == "write_target_readonly"
    assert target.read_text() == "original"
    after = os.stat(target)
    assert (after.st_ino, after.st_mode) == (before.st_ino, before.st_mode)
    assert _leftovers(ws) == []


def test_writable_existing_target_is_rewritten_control(tmp_path):
    reg, ws, _ = _env(tmp_path)
    target = ws / "open.txt"
    target.write_text("original")
    os.chmod(target, 0o600)
    res = _write(reg, "open.txt", "replaced")
    assert res.ok, res.content
    assert target.read_text() == "replaced"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600


def test_overwrite_preserves_permission_bits_of_singly_linked_file(tmp_path):
    reg, ws, _ = _env(tmp_path)
    script = ws / "run.sh"
    script.write_text("echo old\n")
    os.chmod(script, 0o750)
    res = _write(reg, "run.sh", "echo new\n")
    assert res.ok, res.content
    assert script.read_text() == "echo new\n"
    assert stat.S_IMODE(os.stat(script).st_mode) == 0o750


def test_overwrite_never_carries_setuid_or_setgid(tmp_path):
    reg, ws, _ = _env(tmp_path)
    tool = ws / "tool"
    tool.write_text("x")
    os.chmod(tool, 0o6755)
    res = _write(reg, "tool", "y")
    assert res.ok, res.content
    assert stat.S_IMODE(os.stat(tool).st_mode) == 0o755


def test_directory_target_is_refused_without_leftovers(tmp_path):
    reg, ws, _ = _env(tmp_path)
    (ws / "adir").mkdir()
    res = _write(reg, "adir")
    assert not res.ok
    assert res.refusal.error == "write_target_unsupported"
    assert (ws / "adir").is_dir()
    assert _leftovers(ws) == []


def test_ordinary_rewrite_keeps_ownership_claims(tmp_path):
    reg, ws, led = _env(tmp_path)
    assert _write(reg, "mine.txt", "one", agent="alice").ok
    assert _write(reg, "mine.txt", "two", agent="alice").ok
    assert (ws / "mine.txt").read_text() == "two"
    assert led.owner_of("mine.txt") == "alice"
    denied = _write(reg, "mine.txt", "three", agent="bob")
    assert not denied.ok and denied.refusal.error == "ownership_denied"


def test_read_through_parent_swapped_after_jail_check_is_refused(tmp_path, monkeypatch):
    reg, ws, _ = _env(tmp_path)
    (ws / "sub").mkdir()
    (ws / "sub" / "x.txt").write_text("inside")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.txt").write_text("outside-workspace content")
    real_jail = builtin._jail

    def swapping_jail(root, rel):
        target = real_jail(root, rel)
        (ws / "sub").rename(tmp_path / "sub-moved")
        (ws / "sub").symlink_to(outside)
        return target

    monkeypatch.setattr(builtin, "_jail", swapping_jail)
    res = reg.dispatch("worker", "read_file", {"path": "sub/x.txt"})
    assert not res.ok
    assert res.refusal.error == "read_target_changed"
    assert "outside-workspace content" not in res.content
