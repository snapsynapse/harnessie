"""Bounded, deterministic properties for evidence intake and structured verdicts."""
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from hypothesis import example, given, settings, strategies as st

from harness.verify import parse_verdict
from harness.verify_evidence import EvidenceValidationError, load_evidence_bundle

PILOT = settings(max_examples=200, derandomize=True, database=None, deadline=500)
TEXT = st.text(max_size=80)
SCALAR = st.none() | st.booleans() | st.integers(-10000, 10000) | TEXT
def json_values(depth):
    if depth == 0:
        return SCALAR
    child = json_values(depth - 1)
    return SCALAR | st.lists(child, max_size=3) | st.dictionaries(st.text(max_size=12), child, max_size=3)


JSON_VALUE = json_values(3)
IDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)


@PILOT
@given(JSON_VALUE)
@example([])
def test_arbitrary_claim_status_cannot_crash(status):
    result = parse_verdict(json.dumps({"claims": [{"id": "c", "status": status}]}))
    assert result.passed is (status == "reproduced")


@PILOT
@given(st.lists(IDS, min_size=1, max_size=8, unique=True), st.sampled_from(["refuted", "not_verifiable"]))
def test_one_unproven_required_claim_prevents_success(ids, status):
    claims = [{"id": name, "status": "reproduced"} for name in ids]
    assert parse_verdict(json.dumps({"claims": claims})).passed
    claims[-1]["status"] = status
    result = parse_verdict(json.dumps({"claims": claims}))
    assert not result.passed
    assert result.overall_status == ("failed" if status == "refuted" else "cannot_verify")


@PILOT
@given(st.lists(IDS, min_size=1, max_size=8, unique=True))
def test_no_required_claim_cannot_pass(ids):
    claims = [{"id": name, "status": "reproduced", "required": False} for name in ids]
    assert parse_verdict(json.dumps({"claims": claims})).overall_status == "cannot_verify"


@PILOT
@given(JSON_VALUE)
def test_malformed_claim_shapes_return_a_verdict(value):
    result = parse_verdict(json.dumps({"claims": [value]}))
    assert result.overall_status in {"verified", "failed", "cannot_verify"}
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value.get("id", "").strip():
        assert not result.passed


def bundle(root, payload=b"proof"):
    (root / "proof.txt").write_bytes(payload)
    data = {"schema_version": 1, "workspace": {"revision": "abc123", "dirty": False},
            "diff": {"path": "proof.txt", "sha256": hashlib.sha256(payload).hexdigest()},
            "claims": [{"id": "c", "statement": "The diff is bound.", "diff": True}]}
    path = root / "bundle.json"
    path.write_text(json.dumps(data))
    return path, data


@PILOT
@given(st.binary(max_size=512))
def test_valid_bundle_and_changed_digest(payload):
    with tempfile.TemporaryDirectory(prefix="harnessie-property-") as directory:
        root = Path(directory)
        path, data = bundle(root, payload)
        assert load_evidence_bundle(path, evidence_root=root).data == data
        (root / "proof.txt").write_bytes(payload + b"x")
        try:
            load_evidence_bundle(path, evidence_root=root)
        except EvidenceValidationError as exc:
            assert any(p.code == "file.hash_mismatch" for p in exc.problems)
        else:
            raise AssertionError("modified evidence passed preflight")


@PILOT
@given(st.sampled_from(["../", "/", "a/../../", "a\\", "\x00"]), IDS)
@example("\x00", "a")
def test_unsafe_paths_refuse(prefix, name):
    with tempfile.TemporaryDirectory(prefix="harnessie-property-") as directory:
        root = Path(directory)
        path, data = bundle(root)
        data["diff"]["path"] = prefix + name
        path.write_text(json.dumps(data))
        try:
            load_evidence_bundle(path, evidence_root=root)
        except EvidenceValidationError as exc:
            assert exc.problems
        else:
            raise AssertionError("unsafe path passed preflight")
        from harness.verify_standalone import VerifyRequest, run_standalone_verify
        with patch("harness.verify_standalone._workspace_git_state", return_value=("abc123", False)), \
                patch("harness.verify_standalone.build_model", side_effect=AssertionError("model dispatched")), \
                patch("harness.verify_standalone.run_checks", side_effect=AssertionError("checks dispatched")):
            request = VerifyRequest(workspace=root, criteria_path=None, evidence_bundle_path=path, evidence_root=root)
            assert run_standalone_verify(request).exit_code == 2


@PILOT
@given(JSON_VALUE)
def test_nonobject_bundle_refuses(value):
    if isinstance(value, dict):
        return
    with tempfile.TemporaryDirectory(prefix="harnessie-property-") as directory:
        root = Path(directory)
        path = root / "bundle.json"
        path.write_text(json.dumps(value))
        try:
            load_evidence_bundle(path, evidence_root=root)
        except EvidenceValidationError as exc:
            assert all(p.code.startswith("schema.") for p in exc.problems)
        else:
            raise AssertionError("non-object bundle accepted")
