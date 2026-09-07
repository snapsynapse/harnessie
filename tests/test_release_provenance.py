"""Provenance policy binds all assets, the original workflow, ref and commit."""
import hashlib
from pathlib import Path
import subprocess

import pytest

from scripts.verify_release_provenance import verify_release, ProvenanceError

COMMIT = "a" * 40


def assets(root):
    (root / "dist").mkdir()
    (root / "release").mkdir()
    names = ["dist/harnessie-1.3.0-py3-none-any.whl", "dist/harnessie-1.3.0.tar.gz",
             "release/harnessie-1.3.0.cdx.json"]
    for name in names:
        (root / name).write_bytes(name.encode())
    sums = root / "release/harnessie-1.3.0.SHA256SUMS"
    sums.write_text("".join(hashlib.sha256((root / n).read_bytes()).hexdigest() + "  " + n + "\n" for n in names))
    return names


def test_every_asset_requires_original_identity(tmp_path):
    assets(tmp_path)
    calls = []
    def successful(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout='[{"verified":true}]')
    receipt = verify_release(tmp_path, "v1.3.0", COMMIT, run=successful)
    assert len(receipt["assets"]) == len(calls) == 4
    for command in calls:
        assert command[command.index("--source-digest") + 1] == COMMIT
        assert command[command.index("--source-ref") + 1] == "refs/tags/v1.3.0"
        assert command[command.index("--signer-workflow") + 1] == "snapsynapse/harnessie/.github/workflows/release.yml"
        assert "--deny-self-hosted-runners" in command


@pytest.mark.parametrize("damage", ["bytes", "traversal", "missing", "duplicate", "symlink", "encoding"])
def test_integrity_damage_refuses_before_remote_verifier(tmp_path, damage):
    names = assets(tmp_path)
    sums = tmp_path / "release/harnessie-1.3.0.SHA256SUMS"
    if damage == "bytes":
        (tmp_path / names[0]).write_text("altered")
    elif damage == "traversal":
        sums.write_text(sums.read_text().replace(names[0], "../../elsewhere"))
    elif damage == "missing":
        (tmp_path / names[1]).unlink()
    elif damage == "duplicate":
        sums.write_text(sums.read_text() + sums.read_text().splitlines()[0] + "\n")
    elif damage == "encoding":
        sums.write_bytes(b"\xff")
    else:
        (tmp_path / names[0]).unlink()
        (tmp_path / names[0]).symlink_to(tmp_path / names[1])
    def forbidden(*args, **kwargs):
        raise AssertionError("remote verifier called before integrity refusal")
    with pytest.raises(ProvenanceError):
        verify_release(tmp_path, "v1.3.0", COMMIT, run=forbidden)


@pytest.mark.parametrize("failure", ["wrong repository", "wrong workflow", "wrong commit", "missing provenance"])
def test_verification_failure_never_yields_a_receipt(tmp_path, failure):
    assets(tmp_path)
    def rejected(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, stderr=failure)
    with pytest.raises(ProvenanceError, match="attestation"):
        verify_release(tmp_path, "v1.3.0", COMMIT, run=rejected)
