"""Complete offline four-stage workload sizing."""
import json
from pathlib import Path

from scripts.pilot_contract import digest_json
from scripts.pilot_policy import (HAIKU_CONTEXT_POLICY_ID, CONTEXT_HAIKU_INPUT_PER_RUN,
                                  CONTEXT_TOTAL_TOKENS_PER_RUN)
from scripts.pilot_workload import measure_full_workload


REPO = Path(__file__).resolve().parents[1]


def test_full_declared_evidence_fits_byte_envelope_without_live_calls(tmp_path):
    report = measure_full_workload(REPO, tmp_path / "workload")
    assert report["status"] == "needs_arbitration"
    assert report["live_model_calls"] == 0
    assert report["synthetic_transport_calls"] == {"claude": 8, "qwen": 8}
    assert report["request_metrics"]["records"] == 16
    assert report["request_metrics"]["admitted"] == 16
    assert report["all_requests_admitted"] is True
    assert report["byte_envelope_result"] == "fits_candidate_process_limits"
    assert set(report["stages"]) == {
        "claude:position", "qwen:position", "claude:objection", "qwen:objection"}
    assert all(stage["requests"] == 4 for stage in report["stages"].values())
    assert all(stage["max_evidence_bytes"] > 190_000 for stage in report["stages"].values())
    assert report["token_limit_result"] == "not_inferred_from_bytes"
    assert report["existing_live_evidence"]["conclusion"].endswith("existing Haiku cap")
    assert report["policy_id"] == HAIKU_CONTEXT_POLICY_ID
    assert report["execution_limits"]["haiku_input_tokens"] == CONTEXT_HAIKU_INPUT_PER_RUN
    assert report["execution_limits"]["total_tokens"] == CONTEXT_TOTAL_TOKENS_PER_RUN
    assert report["synthetic_haiku_input_tokens"] < CONTEXT_HAIKU_INPUT_PER_RUN
    report_path = Path(report["report_path"])
    assert report["report_canonical_json_sha256"] == digest_json(
        json.loads(report_path.read_text()))
    assert "report_sha256" not in report
