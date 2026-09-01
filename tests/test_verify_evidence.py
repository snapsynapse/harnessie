"""Deterministic evidence-bundle contract for standalone verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from harness.verify_evidence import (
    EvidenceValidationError,
    load_evidence_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bundle(tmp_path: Path, mutate=None) -> tuple[Path, Path, dict]:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    diff_data = b"diff --git a/a.txt b/a.txt\n"
    log_data = b"1 passed\n"
    (evidence_root / "change.diff").write_bytes(diff_data)
    (evidence_root / "test.log").write_bytes(log_data)
    data = {
        "schema_version": 1,
        "workspace": {"revision": "abc123", "dirty": False},
        "diff": {"path": "change.diff", "sha256": digest(diff_data)},
        "evidence": [{
            "id": "focused-tests",
            "path": "test.log",
            "sha256": digest(log_data),
            "media_type": "text/plain",
        }],
        "checks": [{
            "id": "pytest-focused",
            "command": "pytest tests/test_example.py -q",
            "exit_code": 0,
            "platform": "linux-x86_64",
            "environment": {"PYTHON_VERSION": "3.12"},
            "evidence": ["focused-tests"],
        }],
        "claims": [{
            "id": "parser-guard",
            "statement": "The parser rejects malformed input before workers run.",
            "diff": True,
            "evidence": ["focused-tests"],
            "checks": ["pytest-focused"],
        }],
    }
    if mutate:
        mutate(data, evidence_root)
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return bundle_path, evidence_root, data


def problem_codes(exc: EvidenceValidationError) -> set[str]:
    return {problem.code for problem in exc.problems}


def test_schema_is_valid_and_served_copy_is_identical():
    packaged = ROOT / "harness" / "schemas" / "v1" / "verify-evidence.schema.json"
    served = ROOT / "docs" / "schemas" / "v1" / "verify-evidence.schema.json"
    schema = json.loads(packaged.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert served.read_bytes() == packaged.read_bytes()


def test_passing_bundle_binds_claims_checks_and_hashed_files(tmp_path):
    bundle_path, evidence_root, data = write_bundle(tmp_path)
    bundle = load_evidence_bundle(
        bundle_path,
        evidence_root=evidence_root,
        current_revision="abc123",
        current_dirty=False,
    )
    assert bundle.data == data
    assert bundle.files == {
        "diff": (evidence_root / "change.diff").resolve(),
        "focused-tests": (evidence_root / "test.log").resolve(),
    }
    assert bundle.evidence_root == evidence_root.resolve()


def test_missing_evidence_is_rejected(tmp_path):
    def remove_log(_data, evidence_root):
        (evidence_root / "test.log").unlink()

    bundle_path, evidence_root, _ = write_bundle(tmp_path, remove_log)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert "file.missing" in problem_codes(caught.value)


def test_parent_traversal_is_rejected_even_if_target_exists(tmp_path):
    outside = tmp_path / "outside.log"
    outside.write_text("outside", encoding="utf-8")

    def traverse(data, _root):
        data["evidence"][0]["path"] = "../outside.log"
        data["evidence"][0]["sha256"] = digest(b"outside")

    bundle_path, evidence_root, _ = write_bundle(tmp_path, traverse)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert "file.unsafe_path" in problem_codes(caught.value)


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path / "outside.log"
    outside.write_text("outside", encoding="utf-8")

    def link_outside(data, evidence_root):
        (evidence_root / "escape.log").symlink_to(outside)
        data["evidence"][0]["path"] = "escape.log"
        data["evidence"][0]["sha256"] = digest(b"outside")

    bundle_path, evidence_root, _ = write_bundle(tmp_path, link_outside)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert "file.outside_root" in problem_codes(caught.value)


def test_hash_mismatch_is_rejected(tmp_path):
    def wrong_hash(data, _root):
        data["diff"]["sha256"] = "0" * 64

    bundle_path, evidence_root, _ = write_bundle(tmp_path, wrong_hash)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert "file.hash_mismatch" in problem_codes(caught.value)


def test_stale_revision_and_dirty_mismatch_are_distinct(tmp_path):
    bundle_path, evidence_root, _ = write_bundle(tmp_path)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(
            bundle_path,
            evidence_root=evidence_root,
            current_revision="def456",
            current_dirty=True,
        )
    assert {"workspace.stale_revision", "workspace.dirty_mismatch"} <= \
        problem_codes(caught.value)


def test_duplicate_claim_ids_are_rejected(tmp_path):
    def duplicate(data, _root):
        data["claims"].append({
            "id": "parser-guard",
            "statement": "A second claim reused the identifier.",
            "checks": ["pytest-focused"],
        })

    bundle_path, evidence_root, _ = write_bundle(tmp_path, duplicate)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert "claim.duplicate_id" in problem_codes(caught.value)


def test_unknown_claim_bindings_are_rejected(tmp_path):
    def unknown(data, _root):
        data["claims"][0]["evidence"] = ["missing-evidence"]
        data["claims"][0]["checks"] = ["missing-check"]

    bundle_path, evidence_root, _ = write_bundle(tmp_path, unknown)
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    assert {"claim.unknown_evidence", "claim.unknown_check"} <= \
        problem_codes(caught.value)


def test_schema_errors_are_reported_without_path_access(tmp_path):
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(
        "schema_version: 2\nworkspace: {}\nclaims: []\n", encoding="utf-8")
    with pytest.raises(EvidenceValidationError) as caught:
        load_evidence_bundle(bundle_path, evidence_root=evidence_root)
    codes = problem_codes(caught.value)
    assert "schema.const" in codes
    assert "schema.minItems" in codes
