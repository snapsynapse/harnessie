#!/usr/bin/env python3
"""Verify exact release bytes and original GitHub build provenance, never re-attest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

REPOSITORY = "snapsynapse/harnessie"
WORKFLOW = REPOSITORY + "/.github/workflows/release.yml"


class ProvenanceError(ValueError):
    pass


def sha256(path: Path) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProvenanceError("unsafe release asset")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_release(root: Path, tag: str, commit: str, *, run=subprocess.run) -> dict:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ProvenanceError("invalid release tag or commit")
    version = tag[1:]
    names = [f"dist/harnessie-{version}-py3-none-any.whl",
             f"dist/harnessie-{version}.tar.gz", f"release/harnessie-{version}.cdx.json"]
    checksum = f"release/harnessie-{version}.SHA256SUMS"
    try:
        for directory in (root / "dist", root / "release"):
            if directory.is_symlink() or not directory.is_dir():
                raise ProvenanceError("unsafe release directory")
        digests = {name: sha256(root / name) for name in [*names, checksum]}
        recorded = {}
        for line in (root / checksum).read_text().splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if not match or match[2] not in names or match[2] in recorded:
                raise ProvenanceError("invalid checksum inventory")
            recorded[match[2]] = match[1]
        if recorded != {name: digests[name] for name in names}:
            raise ProvenanceError("release checksum mismatch or missing asset")
        for name in digests:
            # gh makes signer-workflow and cert-identity mutually exclusive.
            # The exact certificate identity already binds repository, workflow
            # path and tag; the digest checks below also bind both commits.
            command = ["gh", "attestation", "verify", str(root / name),
                       "--repo", REPOSITORY,
                       "--cert-identity", f"https://github.com/{WORKFLOW}@refs/tags/{tag}",
                       "--source-ref", f"refs/tags/{tag}", "--source-digest", commit,
                       "--signer-digest", commit, "--deny-self-hosted-runners",
                       "--predicate-type", "https://slsa.dev/provenance/v1", "--format", "json"]
            try:
                result = run(command, check=True, capture_output=True, text=True, timeout=120)
                verified = json.loads(result.stdout)
                if not isinstance(verified, list) or not verified:
                    raise ProvenanceError("empty attestation verification result")
            except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
                raise ProvenanceError(f"attestation verification failed for {name}") from exc
        # A caller must not mutate downloads during verification.
        if any(sha256(root / name) != digest for name, digest in digests.items()):
            raise ProvenanceError("release assets changed during verification")
        return {"repository": REPOSITORY, "workflow": WORKFLOW, "tag": tag,
                "commit": commit, "assets": digests, "verified": True}
    except (OSError, UnicodeError) as exc:
        raise ProvenanceError(f"release asset unavailable: {type(exc).__name__}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_release(args.root, args.tag, args.commit), sort_keys=True))
    except ProvenanceError as exc:
        print(f"release provenance FAILED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
