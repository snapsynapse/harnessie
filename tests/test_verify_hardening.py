"""Regression tests for the 2026-11-18 verify-subsystem findings.

SEC-20261118-003: admitted evidence and bundle bytes are snapshotted at
preflight and served from that snapshot, never reopened by path.
SEC-20261118-012: check output is streamed under byte ceilings with a whole-call
deadline and process-group cleanup.
SEC-20261118-015: each verifier mode assembles exactly one output contract.
SEC-20261118-016: checks that could not execute are cannot-verify (exit 2), not
failed artifacts (exit 1).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from harness import sandbox
from harness import verify as verify_mod
from harness.events import EventLog
from harness.memory import ProofStore
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.roles import RoleDef
from harness.tools.registry import ToolRegistry
from harness.verify import Check, run_checks
from harness.verify_evidence import (
    EvidenceValidationError,
    load_evidence_bundle,
    register_evidence_reader,
)
from harness.verify_standalone import (
    DEFAULT_VERIFIER_PROMPT,
    EXIT_CANNOT_VERIFY,
    EXIT_FAILED,
    EXIT_VERIFIED,
    VerifyRequest,
    run_standalone_verify,
)

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

needs_sandbox = pytest.mark.skipif(
    not sandbox.available(), reason="no OS sandbox backend admitted")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- SEC-20261118-003: admitted evidence is bound to the bytes served --------

ADMITTED = b"original admitted bytes\n"


def admit(tmp_path: Path, relative: str = "proof.txt"):
    root = tmp_path / "evidence"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(ADMITTED)
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "workspace": {"revision": "abc123", "dirty": False},
        "evidence": [{"id": "proof", "path": relative,
                      "sha256": digest(ADMITTED), "media_type": "text/plain"}],
        "claims": [{"id": "C1", "statement": "synthetic",
                    "evidence": ["proof"]}],
    }), encoding="utf-8")
    bundle = load_evidence_bundle(bundle_path, evidence_root=root,
                                  current_revision="abc123",
                                  current_dirty=False)
    registry = ToolRegistry()
    register_evidence_reader(registry, bundle)
    return bundle, registry, root, target, bundle_path


def read_proof(registry: ToolRegistry) -> str:
    result = registry.dispatch("verifier", "read_evidence",
                               {"evidence_id": "proof"})
    assert result.ok
    return result.content


def test_unchanged_proof_is_served_positive_control(tmp_path):
    _, registry, *_ = admit(tmp_path)
    assert ADMITTED.decode() in read_proof(registry)


def test_proof_content_replaced_after_admission_serves_admitted_bytes(tmp_path):
    _, registry, _, target, _ = admit(tmp_path)
    target.write_bytes(b"replaced after admission\n")
    content = read_proof(registry)
    assert ADMITTED.decode() in content
    assert "replaced after admission" not in content


def test_proof_file_unlinked_after_admission_serves_admitted_bytes(tmp_path):
    _, registry, _, target, _ = admit(tmp_path)
    target.unlink()
    assert ADMITTED.decode() in read_proof(registry)


def test_parent_directory_replaced_after_admission(tmp_path):
    _, registry, root, target, _ = admit(tmp_path, "logs/proof.txt")
    (root / "logs").rename(root / "logs-old")
    (root / "logs").mkdir()
    (root / "logs" / "proof.txt").write_bytes(b"swapped parent bytes\n")
    content = read_proof(registry)
    assert ADMITTED.decode() in content
    assert "swapped parent bytes" not in content


def test_symlink_swap_to_outside_root_after_admission(tmp_path):
    _, registry, _, target, _ = admit(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"synthetic outside-root bytes\n")
    target.unlink()
    target.symlink_to(outside)
    content = read_proof(registry)
    assert "synthetic outside-root bytes" not in content
    assert ADMITTED.decode() in content


def test_bundle_digest_is_bound_to_admitted_bytes(tmp_path):
    bundle, _, _, _, bundle_path = admit(tmp_path)
    admitted = digest(bundle_path.read_bytes())
    bundle_path.write_text("replaced: true\n", encoding="utf-8")
    assert bundle.source_sha256 == admitted


def test_oversized_evidence_is_refused_at_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.verify_evidence.MAX_EVIDENCE_FILE_BYTES", 8)
    with pytest.raises(EvidenceValidationError) as exc:
        admit(tmp_path)
    assert {p.code for p in exc.value.problems} == {"file.too_large"}


def test_oversized_bundle_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.verify_evidence.MAX_BUNDLE_BYTES", 8)
    with pytest.raises(EvidenceValidationError) as exc:
        admit(tmp_path)
    assert {p.code for p in exc.value.problems} == {"document.too_large"}


def test_fifo_evidence_is_refused_without_blocking(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    os.mkfifo(root / "proof.txt")
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "workspace": {"revision": "abc123", "dirty": False},
        "evidence": [{"id": "proof", "path": "proof.txt",
                      "sha256": digest(b""), "media_type": "text/plain"}],
        "claims": [{"id": "C1", "statement": "s", "evidence": ["proof"]}],
    }), encoding="utf-8")
    with pytest.raises(EvidenceValidationError) as exc:
        load_evidence_bundle(bundle_path, evidence_root=root)
    assert "file.not_regular" in {p.code for p in exc.value.problems}


def test_read_evidence_output_stays_bounded(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    big = b"y" * 1_000_000
    (root / "big.log").write_bytes(big)
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "workspace": {"revision": "abc123", "dirty": False},
        "evidence": [{"id": "proof", "path": "big.log",
                      "sha256": digest(big), "media_type": "text/plain"}],
        "claims": [{"id": "C1", "statement": "s", "evidence": ["proof"]}],
    }), encoding="utf-8")
    bundle = load_evidence_bundle(bundle_path, evidence_root=root)
    registry = ToolRegistry()
    register_evidence_reader(registry, bundle)
    assert len(bundle.snapshots["proof"]) < len(big)
    content = read_proof(registry)
    assert "y" * 100_000 + "\n[harnessie:truncated" in content
    assert "y" * 100_001 not in content
    assert truncation_marker(content) == {
        "evidence_id": "proof", "served_bytes": 100_000,
        "total_bytes": len(big), "sha256": digest(big)}


TRUNCATION = re.compile(
    r"\[harnessie:truncated source=read_evidence evidence_id=(?P<evidence_id>\S+) "
    r"served_bytes=(?P<served_bytes>\d+) total_bytes=(?P<total_bytes>\d+) "
    r"sha256=(?P<sha256>[0-9a-f]{64})\]")


def truncation_marker(content: str) -> dict | None:
    found = TRUNCATION.findall(content)
    if not found:
        return None
    assert len(found) == 1
    evidence_id, served, total, sha = found[0]
    return {"evidence_id": evidence_id, "served_bytes": int(served),
            "total_bytes": int(total), "sha256": sha}


def _admit_bytes(tmp_path: Path, data: bytes):
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "run.log").write_bytes(data)
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "workspace": {"revision": "abc123", "dirty": False},
        "evidence": [{"id": "proof", "path": "run.log",
                      "sha256": digest(data), "media_type": "text/plain"}],
        "claims": [{"id": "C1", "statement": "s", "evidence": ["proof"]}],
    }), encoding="utf-8")
    registry = ToolRegistry()
    register_evidence_reader(
        registry, load_evidence_bundle(bundle_path, evidence_root=root))
    return registry


def test_hidden_failure_past_the_cut_is_marked_not_silently_dropped(tmp_path):
    # 120 KB of PASS lines with the decisive failure past the served prefix:
    # the verifier must be told the suffix exists and was not served.
    passing = b"".join(b"test_%05d PASS\n" % i for i in range(8000))
    data = passing + b"FINAL: 3 tests FAILED\n"
    assert len(data) > 100_000
    content = read_proof(_admit_bytes(tmp_path, data))
    assert "FAILED" not in content.split("[harnessie:truncated")[0]
    marker = truncation_marker(content)
    assert marker is not None
    assert marker["served_bytes"] == 100_000
    assert marker["total_bytes"] == len(data)
    assert marker["sha256"] == digest(data)


def test_multibyte_truncation_counts_served_bytes_exactly(tmp_path):
    data = "\u00e9".encode("utf-8") * 100_001
    content = read_proof(_admit_bytes(tmp_path, data))
    assert content.count("\u00e9") == 100_000
    marker = truncation_marker(content)
    assert marker["served_bytes"] == 200_000
    assert marker["total_bytes"] == len(data)


@pytest.mark.parametrize("size", [0, 1, 99_999, 100_000])
def test_complete_evidence_carries_no_truncation_marker(tmp_path, size):
    data = b"z" * size
    content = read_proof(_admit_bytes(tmp_path, data))
    assert content.count("z") == size
    assert "harnessie:truncated" not in content


def _git_workspace(ws: Path) -> str:
    ws.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    (ws / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    subprocess.run(["git", "add", "artifact.txt"], cwd=ws, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Harnessie", "-c",
         "user.email=harnessie@example.invalid", "-c", "commit.gpgsign=false",
         "commit", "-qm", "fixture"], cwd=ws, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ws, check=True,
                          capture_output=True, text=True).stdout.strip()


def write_models_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text("tiers:\n  mid:\n    provider: mock\n    model_id: mock\n",
                    encoding="utf-8")
    return path


def patch_model(monkeypatch, script):
    model = MockModel(ModelSpec(name="mock", provider="mock", model_id="mock"),
                      script=script)
    monkeypatch.setattr("harness.verify_standalone.build_model",
                        lambda spec: model)
    return model


def turn(name, arguments, call_id="c"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name,
                                              arguments=arguments)])


@needs_sandbox
def test_check_mutating_evidence_and_bundle_cannot_change_consumed_bytes(
        tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    _git_workspace(ws)
    # Evidence and bundle live inside the mutable workspace, so the check
    # command can rewrite both between preflight and consumption.
    evidence_root = ws / "evidence"
    evidence_root.mkdir()
    (evidence_root / "focused.log").write_bytes(ADMITTED)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ws, check=True,
                              capture_output=True, text=True).stdout.strip()
    bundle_path = ws / "bundle.json"
    bundle_path.write_text(json.dumps({
        "schema_version": 1,
        "workspace": {"revision": revision, "dirty": True},
        "evidence": [{"id": "focused-log", "path": "focused.log",
                      "sha256": digest(ADMITTED)}],
        "claims": [{"id": "C1", "statement": "artifact.txt exists",
                    "evidence": ["focused-log"]}],
    }), encoding="utf-8")
    admitted_bundle = digest(bundle_path.read_bytes())
    tamper = (f"{PY} -c \"import pathlib;"
              "pathlib.Path('evidence/focused.log').write_text('tampered by check');"
              "pathlib.Path('bundle.json').write_text('{}')\"")
    model = patch_model(monkeypatch, [
        turn("read_evidence", {"evidence_id": "focused-log"}, "read"),
        turn("task_complete", {"report": json.dumps({"claims": [{
            "id": "C1", "status": "reproduced", "required": True}]})}, "done"),
    ])
    out = run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=None, evidence_bundle_path=bundle_path,
        evidence_root=evidence_root, models_path=write_models_yaml(tmp_path),
        checks=[Check("tamper", tamper)], report_dir=tmp_path / "report"))
    assert (evidence_root / "focused.log").read_text() == "tampered by check"
    tool_results = [m.content for m in model.calls[1]["messages"]
                    if m.role == "tool"]
    assert any(ADMITTED.decode() in content for content in tool_results)
    assert not any("tampered by check" in content for content in tool_results)
    report = out.report_path.read_text(encoding="utf-8")
    assert f"evidence_bundle_sha256: {admitted_bundle}" in report
    assert out.exit_code == EXIT_VERIFIED


# -- SEC-20261118-012: bounded child output, deadline, group cleanup ---------

def identity_wrap(monkeypatch):
    # Removes only the OS sandbox wrapper so these process-supervision tests
    # run deterministically on any host; the commands are synthetic Python.
    monkeypatch.setattr("harness.sandbox.wrap", lambda argv, *a, **k: argv)


def checks_run(tmp_path, checks):
    run_dir = tmp_path / "run"
    return run_checks(checks, tmp_path, ProofStore(run_dir),
                      EventLog(run_dir, echo=False), attempt=1)


def py_check(name: str, code: str, timeout: int = 30) -> Check:
    return Check(name, f"{PY} -c {shlex.quote(code)}", timeout=timeout)


def test_check_output_exactly_at_limit_is_not_truncated(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    monkeypatch.setattr(verify_mod, "CHECK_OUTPUT_LIMIT_BYTES", 1000)
    [result] = checks_run(tmp_path, [py_check(
        "exact", "import sys; sys.stdout.write('x' * 1000)")])
    assert result.outcome == "passed"
    assert result.truncated is False
    assert "x" * 1000 in result.output


def test_check_output_one_byte_over_limit_is_truncated(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    monkeypatch.setattr(verify_mod, "CHECK_OUTPUT_LIMIT_BYTES", 1000)
    [result] = checks_run(tmp_path, [py_check(
        "over", "import sys; sys.stdout.write('x' * 1001)")])
    assert result.outcome == "passed"
    assert result.truncated is True
    assert "x" * 1000 in result.output
    assert "x" * 1001 not in result.output


def test_large_stdout_and_stderr_are_bounded(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    [result] = checks_run(tmp_path, [py_check(
        "flood",
        "import sys\n"
        "chunk = 'z' * 65536\n"
        "for _ in range(160):\n"
        "    sys.stdout.write(chunk); sys.stderr.write(chunk)\n")])
    assert result.outcome == "passed"
    assert result.truncated is True
    assert len(result.output) <= 2 * verify_mod.CHECK_OUTPUT_LIMIT_BYTES + 1000


def _pid_gone(pid: int, wait: float = 5.0) -> bool:
    end = time.monotonic() + wait
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_inherited_pipe_child_does_not_hold_check_open(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    pid_file = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, sys\n"
        f"p = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(30)'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(p.pid))\n"
        "print('parent done')\n")
    started = time.monotonic()
    [result] = checks_run(tmp_path, [py_check("lingering", code, timeout=10)])
    elapsed = time.monotonic() - started
    assert elapsed < 8
    assert result.outcome == "passed"
    assert "parent done" in result.output
    assert _pid_gone(int(pid_file.read_text()))


def test_timeout_kills_the_whole_process_group(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    pid_file = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, sys, time\n"
        f"p = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(30)'],"
        " stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        f"open({str(pid_file)!r}, 'w').write(str(p.pid))\n"
        "time.sleep(30)\n")
    started = time.monotonic()
    [result] = checks_run(tmp_path, [py_check("slow", code, timeout=2)])
    assert time.monotonic() - started < 8
    assert result.outcome == "timeout"
    assert result.passed is False
    assert _pid_gone(int(pid_file.read_text()))


def test_escaped_descendant_holding_pipe_is_resource_stop(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    pid_file = tmp_path / "escaped.pid"
    code = (
        "import subprocess, sys\n"
        f"p = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(30)'],"
        " start_new_session=True)\n"
        f"open({str(pid_file)!r}, 'w').write(str(p.pid))\n")
    try:
        started = time.monotonic()
        [result] = checks_run(tmp_path, [py_check("escaped", code, timeout=10)])
        assert time.monotonic() - started < 8
        assert result.outcome == "resource"
        assert result.passed is False
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


# -- SEC-20261118-016: could-not-execute is cannot-verify --------------------

def standalone_checks(tmp_path, checks, report="report"):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    criteria = tmp_path / "criteria.md"
    criteria.write_text("synthetic", encoding="utf-8")
    return run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=criteria, checks=checks,
        report_dir=tmp_path / report, no_verifier=True))


def test_nonexistent_executable_without_wrapper_is_cannot_verify(
        tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    out = standalone_checks(tmp_path, [
        Check("missing", "harnessie-audit-nonexistent-binary")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


@needs_sandbox
def test_nonexistent_executable_under_sandbox_is_cannot_verify(tmp_path):
    out = standalone_checks(tmp_path, [
        Check("missing", "harnessie-audit-nonexistent-binary --flag")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


@needs_sandbox
def test_nonexistent_absolute_path_under_sandbox_is_cannot_verify(tmp_path):
    out = standalone_checks(tmp_path, [
        Check("missing", str(tmp_path / "no-such-tool"))])
    assert out.exit_code == EXIT_CANNOT_VERIFY


@pytest.mark.parametrize("command", ["pytest 'unbalanced", "", "   "])
def test_malformed_command_is_cannot_verify(tmp_path, command):
    out = standalone_checks(tmp_path, [Check("malformed", command)])
    assert out.exit_code == EXIT_CANNOT_VERIFY


def test_permission_denied_executable_is_cannot_verify(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    ws = tmp_path / "ws"
    ws.mkdir()
    script = ws / "check.sh"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o644)
    out = standalone_checks(tmp_path, [Check("noexec", "./check.sh")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


def relative_path_layout(tmp_path, monkeypatch, scripts: dict[str, int],
                         decoys: tuple[str, ...] = ()):
    """A workspace bin/ holding scripts, a harness cwd elsewhere holding only
    decoys, and a relative PATH entry that the launch resolves from the
    workspace (its cwd), never from the harness's own cwd."""
    ws = tmp_path / "ws"
    (ws / "bin").mkdir(parents=True)
    for name, code in scripts.items():
        script = ws / "bin" / name
        script.write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8")
        script.chmod(0o755)
    elsewhere = tmp_path / "harness-cwd"
    (elsewhere / "bin").mkdir(parents=True)
    for name in decoys:
        decoy = elsewhere / "bin" / name
        decoy.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        decoy.chmod(0o755)
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("PATH", "bin" + os.pathsep + os.environ["PATH"])


@pytest.mark.parametrize("wrapped", [
    False, pytest.param(True, marks=needs_sandbox)])
def test_relative_path_entry_resolves_from_check_cwd(
        tmp_path, monkeypatch, wrapped):
    if not wrapped:
        identity_wrap(monkeypatch)
    relative_path_layout(tmp_path, monkeypatch,
                         {"harnessie-onlyinws": 0, "harnessie-failsinws": 1})
    expected = {"harnessie-onlyinws": EXIT_VERIFIED,
                "harnessie-failsinws": EXIT_FAILED,
                "harnessie-audit-nonexistent-binary": EXIT_CANNOT_VERIFY}
    for program, exit_code in expected.items():
        out = standalone_checks(tmp_path, [Check(program, program)],
                                report=program)
        assert out.exit_code == exit_code, program


@pytest.mark.parametrize("wrapped", [
    False, pytest.param(True, marks=needs_sandbox)])
def test_relative_path_entry_ignores_harness_cwd(tmp_path, monkeypatch, wrapped):
    # The program exists only relative to the harness's cwd: the check's
    # launch cannot find it, so it never ran and is cannot-verify.
    if not wrapped:
        identity_wrap(monkeypatch)
    relative_path_layout(tmp_path, monkeypatch, {},
                         decoys=("harnessie-onlyinharness",))
    out = standalone_checks(tmp_path, [Check("decoy", "harnessie-onlyinharness")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


def test_image_resolved_program_is_not_blocked_by_host_lookup(tmp_path):
    # A docker launcher resolves the program inside its image; the host
    # cannot decide that, so the check launches and its result classifies it.
    docker = ["docker", "run", "--rm", "-w", str(tmp_path), "image"]
    verify_mod._resolve_executable(
        ["harnessie-audit-nonexistent-binary"], tmp_path,
        {"PATH": "/usr/bin"}, docker + ["harnessie-audit-nonexistent-binary"])
    with pytest.raises(verify_mod._CheckBlocked):
        verify_mod._resolve_executable(
            ["./absent-in-workspace"], tmp_path, {"PATH": "/usr/bin"},
            docker + ["./absent-in-workspace"])


def test_timeout_is_failed_not_cannot_verify(tmp_path, monkeypatch):
    # A launched check that hangs is an observed artifact failure. Mapping it
    # to cannot-verify would let a failing artifact make itself unscorable.
    identity_wrap(monkeypatch)
    out = standalone_checks(tmp_path, [
        py_check("slow", "import time; time.sleep(30)", timeout=1)])
    assert out.exit_code == EXIT_FAILED


def test_escaped_descendant_is_failed_not_cannot_verify(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    pid_file = tmp_path / "escaped.pid"
    code = (
        "import subprocess, sys\n"
        f"p = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(30)'],"
        " start_new_session=True)\n"
        f"open({str(pid_file)!r}, 'w').write(str(p.pid))\n"
        "raise SystemExit(1)\n")
    try:
        out = standalone_checks(tmp_path, [py_check("escape", code, timeout=10)])
        assert out.exit_code == EXIT_FAILED
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_checks_run_without_os_waitid(tmp_path, monkeypatch):
    # CPython exposes os.waitid on macOS only from 3.13; 3.11 and 3.12 are
    # supported, so the bounded runner must not depend on it.
    identity_wrap(monkeypatch)
    monkeypatch.delattr(os, "waitid", raising=False)
    [ok] = checks_run(tmp_path, [py_check("ok", "pass")])
    assert ok.outcome == "passed"
    (tmp_path / "s").mkdir()
    out = standalone_checks(tmp_path / "s", [py_check("fails", "raise SystemExit(1)")])
    assert out.exit_code == EXIT_FAILED


def test_sandbox_refusal_is_cannot_verify(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.sandbox.backend_name", lambda: None)
    out = standalone_checks(tmp_path, [Check("t", "true")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


def test_executed_exit_one_is_failed_control(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    out = standalone_checks(tmp_path, [
        py_check("fails", "raise SystemExit(1)")])
    assert out.exit_code == EXIT_FAILED


@needs_sandbox
def test_executed_exit_one_under_sandbox_is_failed_control(tmp_path):
    out = standalone_checks(tmp_path, [Check("fails", "false")])
    assert out.exit_code == EXIT_FAILED


def test_observed_failure_outranks_blocked_check(tmp_path, monkeypatch):
    # An observed failure is evidence about the artifact; a blocked sibling
    # must not hide it behind cannot-verify.
    identity_wrap(monkeypatch)
    out = standalone_checks(tmp_path, [
        py_check("fails", "raise SystemExit(1)"),
        Check("missing", "harnessie-audit-nonexistent-binary")])
    assert out.exit_code == EXIT_FAILED


def test_blocked_check_alone_is_cannot_verify_control(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    out = standalone_checks(tmp_path, [
        py_check("ok", "pass"),
        Check("missing", "harnessie-audit-nonexistent-binary")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


def test_check_cannot_sabotage_a_later_check_into_blocked(tmp_path, monkeypatch):
    # Every check is resolved before any check runs, so artifact code in an
    # earlier check cannot turn a later check into a pre-launch block.
    identity_wrap(monkeypatch)
    ws = tmp_path / "ws"
    ws.mkdir()
    lint = ws / "lint.sh"
    lint.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    lint.chmod(0o755)
    out = standalone_checks(tmp_path, [
        py_check("sabotage", f"import os; os.chmod({str(lint)!r}, 0o644)"),
        Check("lint", "./lint.sh")])
    assert out.exit_code == EXIT_FAILED


def _fake_seatbelt(tmp_path, monkeypatch):
    fake = tmp_path / "fakebin" / "sandbox-exec"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\necho 'sandbox-exec: sandbox_apply: Operation "
                    "not permitted' >&2\nexit 71\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setattr("harness.sandbox.wrap",
                        lambda argv, *a, **k: [str(fake), "-p", "x", *argv])


def test_genuine_sandbox_apply_failure_is_cannot_verify_control(tmp_path, monkeypatch):
    _fake_seatbelt(tmp_path, monkeypatch)
    out = standalone_checks(tmp_path, [Check("t", "true")])
    assert out.exit_code == EXIT_CANNOT_VERIFY


@needs_sandbox
def test_artifact_mimicking_sandbox_apply_is_failed(tmp_path):
    if sandbox.backend_name() != "seatbelt":
        pytest.skip("Seatbelt-specific classification")
    code = ("import os, sys; sys.stderr.write('sandbox-exec: sandbox_apply: "
            "Operation not permitted\\n'); sys.stderr.flush(); os._exit(71)")
    out = standalone_checks(tmp_path, [
        Check("mimic", f"python3 -c {shlex.quote(code)}")])
    assert out.exit_code == EXIT_FAILED


def test_gate_check_outcomes_are_structured(tmp_path, monkeypatch):
    identity_wrap(monkeypatch)
    results = checks_run(tmp_path, [
        py_check("ok", "pass"),
        py_check("fails", "raise SystemExit(3)"),
        Check("missing", "harnessie-audit-nonexistent-binary"),
        Check("malformed", "x 'unbalanced"),
    ])
    assert [r.outcome for r in results] == [
        "passed", "failed", "blocked", "blocked"]
    assert [r.passed for r in results] == [True, False, False, False]
    events = [json.loads(line) for line in
              (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    assert [e["outcome"] for e in events if e["kind"] == "check"] == [
        "passed", "failed", "blocked", "blocked"]


# -- SEC-20261118-015: one mode-specific output contract ---------------------

LEGACY_SHAPE = '"passed"'
CLAIMS_SHAPE = '"claims"'


@pytest.mark.parametrize("name", ["code-verifier", "claims-verifier"])
def test_gate_verifier_prompt_has_exactly_one_legacy_contract(name):
    prompt = (ROOT / "agents" / "verifiers" / f"{name}.md").read_text(
        encoding="utf-8")
    system = RoleDef(name, "verifier", prompt).system_prompt(
        extra_context="phase context")
    assert system.count(LEGACY_SHAPE) == 1
    assert CLAIMS_SHAPE not in system


def test_generic_verifier_boundary_carries_no_serialization():
    system = RoleDef("v", "verifier", "# Verifier").system_prompt()
    boundary, _, contract = system.partition("## Output contract")
    assert LEGACY_SHAPE not in boundary and CLAIMS_SHAPE not in boundary
    assert contract.count(LEGACY_SHAPE) == 1


def test_claims_mode_prompt_has_exactly_one_claims_contract():
    system = RoleDef("verifier", "verifier", DEFAULT_VERIFIER_PROMPT,
                     output_contract="claims").system_prompt()
    assert system.count(CLAIMS_SHAPE) == 1
    assert LEGACY_SHAPE not in system


def test_unknown_output_contract_fails_closed():
    with pytest.raises(ValueError):
        RoleDef("v", "verifier", "# V", output_contract="freeform").system_prompt()


def test_non_verifier_roles_carry_no_output_contract():
    for kind in ("orchestrator", "worker"):
        system = RoleDef("r", kind, "# R").system_prompt()
        assert "## Output contract" not in system
        assert LEGACY_SHAPE not in system and CLAIMS_SHAPE not in system


def _system_prompt_seen(model: MockModel) -> str:
    messages = model.calls[0]["messages"]
    return next(m.content for m in messages if m.role == "system")


def _claims_pass():
    return turn("task_complete", {"report": json.dumps({"claims": [{
        "id": "C1", "status": "reproduced", "required": True}]})})


def test_standalone_criteria_mode_sends_one_claims_contract(tmp_path, monkeypatch):
    model = patch_model(monkeypatch, [_claims_pass()])
    ws = tmp_path / "ws"
    ws.mkdir()
    criteria = tmp_path / "criteria.md"
    criteria.write_text("- C1: out.txt exists", encoding="utf-8")
    out = run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=criteria,
        models_path=write_models_yaml(tmp_path),
        report_dir=tmp_path / "report"))
    assert out.exit_code == EXIT_VERIFIED
    system = _system_prompt_seen(model)
    assert system.count(CLAIMS_SHAPE) == 1
    assert LEGACY_SHAPE not in system


def test_standalone_operator_prompt_still_gets_one_contract(tmp_path, monkeypatch):
    model = patch_model(monkeypatch, [_claims_pass()])
    ws = tmp_path / "ws"
    ws.mkdir()
    criteria = tmp_path / "criteria.md"
    criteria.write_text("- C1: out.txt exists", encoding="utf-8")
    operator = tmp_path / "operator.md"
    operator.write_text("# Operator verifier\nBe thorough.", encoding="utf-8")
    run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=criteria, verifier_prompt_path=operator,
        models_path=write_models_yaml(tmp_path),
        report_dir=tmp_path / "report"))
    system = _system_prompt_seen(model)
    assert system.count(CLAIMS_SHAPE) == 1
    assert LEGACY_SHAPE not in system


def test_standalone_evidence_mode_sends_one_claims_contract(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    revision = _git_workspace(ws)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "focused.log").write_bytes(ADMITTED)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps({
        "schema_version": 1,
        "workspace": {"revision": revision, "dirty": False},
        "evidence": [{"id": "focused-log", "path": "focused.log",
                      "sha256": digest(ADMITTED)}],
        "claims": [{"id": "C1", "statement": "s", "evidence": ["focused-log"]}],
    }), encoding="utf-8")
    model = patch_model(monkeypatch, [_claims_pass()])
    out = run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=None, evidence_bundle_path=bundle_path,
        evidence_root=evidence_root, models_path=write_models_yaml(tmp_path),
        report_dir=tmp_path / "report"))
    assert out.exit_code == EXIT_VERIFIED
    system = _system_prompt_seen(model)
    assert system.count(CLAIMS_SHAPE) == 1
    assert LEGACY_SHAPE not in system


def test_evidence_mode_enforces_strict_claim_shape(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    revision = _git_workspace(ws)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "focused.log").write_bytes(ADMITTED)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps({
        "schema_version": 1,
        "workspace": {"revision": revision, "dirty": False},
        "evidence": [{"id": "focused-log", "path": "focused.log",
                      "sha256": digest(ADMITTED)}],
        "claims": [{"id": "C1", "statement": "s", "evidence": ["focused-log"]}],
    }), encoding="utf-8")
    patch_model(monkeypatch, [turn("task_complete", {"report": json.dumps(
        {"claims": [{"id": "C1", "status": "passed", "required": True}]})})])
    out = run_standalone_verify(VerifyRequest(
        workspace=ws, criteria_path=None, evidence_bundle_path=bundle_path,
        evidence_root=evidence_root, models_path=write_models_yaml(tmp_path),
        report_dir=tmp_path / "report"))
    assert out.exit_code == EXIT_CANNOT_VERIFY


# -- SEC-20261118-007: check output reaching a retry task is redacted --------

CHECK_SECRET = "pplx-" + "SYNTHETICCANARY" * 3


@pytest.mark.parametrize("offset", [0, 790, 3000])
def test_check_output_secret_never_reaches_retry_task(tmp_path, monkeypatch,
                                                      offset):
    from harness.loop import LoopResult
    from harness.routing import Route
    from harness.verify import VerificationGate

    identity_wrap(monkeypatch)
    code = (f"import sys; sys.stdout.write('x' * {offset} + "
            f"{CHECK_SECRET!r} + '\\n'); raise SystemExit(1)")
    tasks: list[str] = []

    def attempt(task, route):
        tasks.append(task)
        return LoopResult(stop="complete", report="did it", steps=1)

    run_dir = tmp_path / "run"
    gate = VerificationGate(workspace=tmp_path, proofs=ProofStore(run_dir),
                            events=EventLog(run_dir, echo=False),
                            max_attempts=2)
    result = gate.run(task="original task", attempt_fn=attempt, verify_fn=None,
                      checks=[py_check("leaky", code)],
                      route=Route("cheap", "low"))
    assert result.status == "needs_human"
    assert len(tasks) == 2
    for text in [*tasks, result.final_report,
                 *(v.reasons for v in result.verdicts)]:
        assert "pplx-" not in text
    if offset == 0:
        assert "[REDACTED-SECRET]" in tasks[1]
