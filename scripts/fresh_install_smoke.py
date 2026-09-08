#!/usr/bin/env python3
"""Install a built wheel into a fresh venv and exercise public CLI surfaces."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def run(
    argv: list[str],
    cwd: Path,
    *,
    expected: int = 0,
    contains: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"{' '.join(argv)} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}")
    if contains is not None and contains not in result.stdout:
        raise RuntimeError(
            f"{' '.join(argv)} output did not contain {contains!r}\n"
            f"{result.stdout}")
    return result


def smoke(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="harnessie-install-smoke-") as raw:
        # macOS exposes tempfile's default /var path through a symlink. Use the
        # real fixture root because the exporter deliberately refuses aliases.
        temp = Path(raw).resolve()
        venv = temp / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)], check=True)
        python = venv / "bin" / "python"
        cli = venv / "bin" / "harnessie"
        run(
            [str(python), "-m", "pip", "install", str(wheel)],
            temp,
            contains="Successfully installed",
        )
        help_result = run([str(cli), "--help"], temp)
        for command in (
            "approve-maiden",
            "ownership",
            "observe",
            "export-aidr",
            "verify-inward-manifest",
            "verify-manifest",
        ):
            if command not in help_result.stdout:
                raise RuntimeError(f"installed CLI help omits {command}")

        run(
            [str(cli), "eval"],
            temp,
            expected=2,
            contains="refusing a vacuous pass",
        )
        project = temp / "project"
        run(
            [str(cli), "init", str(project), "--no-verify"],
            temp,
            contains="initialized Harnessie project",
        )
        run(
            [str(cli), "--root", str(project), "verify-inward-manifest"],
            temp,
            contains="inward manifest OK",
        )
        run(
            [str(cli), "--root", str(project), "ownership", "draft.txt",
             "--agent", "implementer", "--json"],
            temp,
            contains='"allowed": true',
        )
        run(
            [str(cli), "--root", str(project), "eval"],
            temp,
            contains="eval scorecard:",
        )
        run(
            [str(python), "-c",
             "from pathlib import Path; from harness.events import EventLog; "
             "import sys; log=EventLog(Path(sys.argv[1])/'runs'/'smoke', echo=False); "
             "log.emit('workflow_start', run_id='smoke'); "
             "log.emit('phase_start', phase='work'); "
             "log.emit('phase_done', phase='work', status='needs_human'); "
             "log.emit('workflow_done', statuses={'work':'needs_human'}); log.close()",
             str(project)], temp,
        )
        run([str(cli), "--root", str(project), "observe", "smoke"],
            temp, contains="observed smoke: needs_human")
        run([str(python), "-c", """
from pathlib import Path
import sys
from harness.adversarial import PositionRecord, assemble_record
root = Path(sys.argv[1])
(root / 'decisions').mkdir(exist_ok=True)
source = root / 'runs/smoke/decisions/DR-work.md'
source.parent.mkdir()
source.write_text(assemble_record(
    record_id='DR-work', title='Synthetic installed export',
    question='Adopt this synthetic change?', context='Installed package smoke.',
    arbiter='synthetic-human-tester', date='2026-09-08',
    positions=[PositionRecord('worker', 'worker', 'mock', 'mock', 'oppose',
                              'Preserve evidence.', 'Retain the original objection.')],
    objections=[{'by': 'worker', 'to': 'the record', 'text': 'Evidence may be lost.'}],
    evidence=['runs/smoke/events.jsonl — hash-chained event log evidencing isolated position generation']),
    encoding='utf-8')
""", str(project)], temp)
        source = project / "runs/smoke/decisions/DR-work.md"
        source_bytes = source.read_bytes()
        evidence_bytes = (project / "runs/smoke/events.jsonl").read_bytes()
        export_command = [str(cli), "--root", str(project), "export-aidr", "smoke", "work",
                          "--output", "decisions/AIDR-9999-synthetic-installed.md",
                          "--arbiter", "synthetic-human-tester"]
        run(export_command, temp, contains='"status": "exported"')
        output = project / "decisions/AIDR-9999-synthetic-installed.md"
        exported = output.read_bytes()
        run(export_command, temp, expected=2, contains='"status": "refused"')
        if source.read_bytes() != source_bytes or output.read_bytes() != exported \
                or (project / "runs/smoke/events.jsonl").read_bytes() != evidence_bytes:
            raise RuntimeError("installed export changed source, evidence or existing destination")
        if yaml.safe_load(exported.decode().split("---\n", 2)[1])["status"] != "open" \
                or b"Evidence may be lost." not in exported:
            raise RuntimeError("installed export lost open status or dissent")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel")
    args = parser.parse_args()
    wheel = Path(args.wheel).resolve()
    if not wheel.is_file():
        print(f"wheel not found: {wheel}", file=sys.stderr)
        return 2
    try:
        smoke(wheel)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"fresh-install smoke FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"fresh-install smoke OK: {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
