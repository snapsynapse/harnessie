"""Minimized crashes found by the bounded property pilot, retained without Hypothesis."""
import hashlib
import json
from pathlib import Path

import pytest

from harness.verify import parse_verdict
from harness.verify_evidence import EvidenceValidationError, load_evidence_bundle

FIXTURES = Path(__file__).parent / "fixtures/parser-regressions"


def test_nonstring_claim_status_refuses_instead_of_raising():
    result = parse_verdict((FIXTURES / "nonstring-claim-status.json").read_text())
    assert not result.passed
    assert result.overall_status == "cannot_verify"


def test_nul_evidence_path_has_a_structured_refusal(tmp_path):
    fixture = json.loads((FIXTURES / "nul-evidence-path.json").read_text())
    data = {"schema_version": 1, "workspace": {"revision": "abc", "dirty": False},
            "diff": {"path": fixture["path"], "sha256": hashlib.sha256(b"").hexdigest()},
            "claims": [{"id": "c", "statement": "Bound diff", "diff": True}]}
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(data))
    with pytest.raises(EvidenceValidationError) as exc:
        load_evidence_bundle(path, evidence_root=tmp_path)
    assert fixture["expected_code"] in {p.code for p in exc.value.problems}
