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


def test_each_stage_sees_budget_and_all_evidence_before_synthesis(tmp_path, monkeypatch):
    from scripts.pilot_claude_code import ClaudeCodePilot
    from scripts.pilot_qwen import QwenPilot
    from scripts.pilot_prepare import SOURCE_FILES

    observed = []
    for adapter in (ClaudeCodePilot, QwenPilot):
        original = adapter.prepare_request

        def inspect(self, messages, tools=None, effort='medium', original=original):
            budget = json.loads(messages[-1].content)
            assert budget['pilot_stage_budget']['calls_per_stage'] == 4
            call = budget['pilot_stage_budget']['call_number']
            assert budget['pilot_stage_budget']['calls_remaining_after_this'] == 4 - call
            assert budget['pilot_stage_budget']['final_call_reserved_for'] == 'task_complete'
            assert budget['pilot_stage_budget']['max_output_tokens_per_call'] == self.allowance.limits.max_output_tokens
            assert budget['pilot_stage_budget']['output_budget_scope'] == 'aggregate_reported_output_all_models'
            assert 'reasoning, formatter and helper-model output' in budget['output_instruction']
            assert 'evidence-path citations' in budget['output_instruction']
            assert 'uncertainty' in budget['output_instruction']
            role = messages[0].content
            assert 'Call 1:' in role and 'Call 4:' in role
            assert 'max_output_tokens_per_call' in role
            if call == 4:
                requests = {tc.id: tc.arguments['path'] for message in messages
                            for tc in message.tool_calls if tc.name == 'read_file'}
                results = {requests[m.tool_call_id]: m.content for m in messages
                           if m.role == 'tool' and m.tool_call_id in requests}
                assert set(results) == {'evidence-index.json'} | {f'evidence/{p}' for p in SOURCE_FILES}
                assert all(results.values())
                assert all((REPO / p).read_text() in results[f'evidence/{p}'] for p in SOURCE_FILES)
            observed.append((budget['pilot_stage_budget']['stage'], call))
            return (original(messages, tools, effort) if getattr(original, '__self__', None)
                    else original(self, messages, tools, effort))

        monkeypatch.setattr(adapter, 'prepare_request', inspect)
    report = measure_full_workload(REPO, tmp_path / 'scheduled')
    assert report['status'] == 'needs_arbitration', report
    assert len(observed) == 16
    assert [call for _, call in observed] == [1, 2, 3, 4] * 4
    assert report['next_live_allowance'] == {'claude': 0, 'qwen': 0}
