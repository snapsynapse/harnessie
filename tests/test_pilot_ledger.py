from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pilot_contract import PilotRefusal
from scripts.pilot_ledger import REQUIRED_LIMITS, RunLedger, read_ledger_summary
from scripts.pilot_policy import (HAIKU_MODEL, CONTEXT_HAIKU_INPUT_PER_RUN,
                                  CONTEXT_HAIKU_OUTPUT_PER_RUN, CONTEXT_TOTAL_TOKENS_PER_RUN)


MANIFEST = "a" * 64


def _receipt(*, input_tokens=1, output_tokens=2, cache_creation=3, cache_read=4,
             haiku=None):
    models = {}
    if haiku is not None:
        models[HAIKU_MODEL] = {
            "input_tokens": haiku[0], "output_tokens": haiku[1],
            "cache_creation_input_tokens": haiku[2], "cache_read_input_tokens": haiku[3],
        }
    return {"usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                       "cache_creation_input_tokens": cache_creation,
                       "cache_read_input_tokens": cache_read}, "model_usage": models}


def _dispatched(ledger):
    attempt = ledger.reserve("claude:position", "claude")
    ledger.dispatched(attempt)
    return attempt


def test_receipt_counts_all_four_usage_fields_and_hash_chain(tmp_path):
    run = tmp_path / "run"
    with RunLedger(run, MANIFEST, REQUIRED_LIMITS) as ledger:
        ledger.finish(_dispatched(ledger), _receipt(), accepted=True)
        summary = ledger.summary()
        assert summary["usage"] == {"input_tokens": 1, "output_tokens": 2,
                                     "cache_creation_input_tokens": 3,
                                     "cache_read_input_tokens": 4}
    assert read_ledger_summary(run)["integrity"] == "valid"


def test_helper_cached_tokens_and_exact_boundary_are_enforced(tmp_path):
    with RunLedger(tmp_path / "run", MANIFEST, REQUIRED_LIMITS) as ledger:
        receipt = _receipt(haiku=(1, 2, 32767, 0))
        ledger.finish(_dispatched(ledger), receipt, accepted=True)
        assert ledger.summary()["haiku_input_tokens"] == 32768
        assert ledger.summary()["haiku_output_tokens"] == 2


def test_unknown_usage_writes_receipt_then_halts(tmp_path):
    run = tmp_path / "run"
    with RunLedger(run, MANIFEST, REQUIRED_LIMITS) as ledger:
        receipt = {"usage": {"input_tokens": 1}, "model_usage": {}}
        with pytest.raises(PilotRefusal, match="receipt_usage_unknown"):
            ledger.finish(_dispatched(ledger), receipt, accepted=True)
        assert ledger.summary()["halted"] is True
    records = [json.loads(line) for line in (run / "ledger.jsonl").read_text().splitlines()]
    assert any(record["kind"] == "receipt" for record in records)


def test_refused_call_is_consumed_and_latched_without_retry(tmp_path):
    with RunLedger(tmp_path / "run", MANIFEST, REQUIRED_LIMITS) as ledger:
        ledger.finish(_dispatched(ledger), _receipt(), accepted=False)
        assert ledger.summary()["calls"]["claude"] == 1
        with pytest.raises(PilotRefusal, match="ledger_halted"):
            ledger.reserve("claude:position", "claude")


def test_overage_writes_evidence_halts_and_retains_raw_receipt(tmp_path):
    run = tmp_path / "run"
    with RunLedger(run, MANIFEST, REQUIRED_LIMITS) as ledger:
        over = _receipt(haiku=(32769, 1, 0, 0))
        with pytest.raises(PilotRefusal, match="haiku_input_budget_exceeded"):
            ledger.finish(_dispatched(ledger), over, accepted=True)
        assert ledger.summary()["halted"]
    text = (run / "ledger.jsonl").read_text()
    assert "32769" in text


def test_existing_run_and_second_instance_refuse(tmp_path):
    run = tmp_path / "run"
    ledger = RunLedger(run, MANIFEST, REQUIRED_LIMITS)
    try:
        with pytest.raises(PilotRefusal, match="ledger_directory_exists"):
            RunLedger(run, MANIFEST, REQUIRED_LIMITS)
    finally:
        ledger.close()
    with pytest.raises(PilotRefusal, match="ledger_directory_exists"):
        RunLedger(run, MANIFEST, REQUIRED_LIMITS)


def test_append_failure_halts_before_dispatch(monkeypatch, tmp_path):
    import scripts.pilot_ledger as module

    original = module.os.fsync
    calls = 0
    def fail_after_initial(fd):
        nonlocal calls
        calls += 1
        if calls > 3:
            raise OSError("disk full")
        return original(fd)
    monkeypatch.setattr(module.os, "fsync", fail_after_initial)
    ledger = RunLedger(tmp_path / "run", MANIFEST, REQUIRED_LIMITS)
    try:
        with pytest.raises(PilotRefusal, match="ledger_io_failure"):
            ledger.reserve("claude:position", "claude")
        assert ledger.summary()["active_attempt"] is None
        assert ledger.summary()["halted"] is True
    finally:
        with pytest.raises(PilotRefusal, match="ledger_io_failure"):
            ledger.close()


def test_integrity_check_detects_tampering(tmp_path):
    run = tmp_path / "run"
    with RunLedger(run, MANIFEST, REQUIRED_LIMITS):
        pass
    path = run / "ledger.jsonl"
    path.write_text(path.read_text().replace("initial", "tampered", 1))
    with pytest.raises(PilotRefusal, match="ledger_integrity_invalid"):
        read_ledger_summary(run)


@pytest.mark.parametrize("suffix", [
    b',"extra":1}',
    b',"extra":NaN}',
    b',"extra":1e999}',
    b',"sequence":1}',
])
def test_integrity_check_rejects_strict_json_and_outer_field_tampering(tmp_path, suffix):
    run = tmp_path / "run"
    with RunLedger(run, MANIFEST, REQUIRED_LIMITS):
        pass
    path = run / "ledger.jsonl"
    first = path.read_bytes().splitlines()[0]
    path.write_bytes(first[:-1] + suffix + b"\n")
    with pytest.raises(PilotRefusal, match="ledger_integrity_invalid"):
        read_ledger_summary(run)


def test_exact_total_budget_stops_the_next_reservation(tmp_path):
    limits = {**REQUIRED_LIMITS, "total_tokens": 10}
    with RunLedger(tmp_path / "run", MANIFEST, limits) as ledger:
        ledger.finish(_dispatched(ledger), _receipt(input_tokens=1, output_tokens=2,
                                                     cache_creation=3, cache_read=4), accepted=True)
        assert ledger.summary()["accounting_complete"] is True
        with pytest.raises(PilotRefusal, match="total_token_budget_exceeded"):
            ledger.reserve("claude:position", "claude")


def test_exact_helper_budget_stops_the_next_reservation(tmp_path):
    limits = {**REQUIRED_LIMITS, "haiku_input_tokens": 10}
    with RunLedger(tmp_path / "run", MANIFEST, limits) as ledger:
        ledger.finish(_dispatched(ledger), _receipt(haiku=(1, 1, 9, 0)), accepted=True)
        with pytest.raises(PilotRefusal, match="haiku_input_budget_exceeded"):
            ledger.reserve("claude:position", "claude")


def test_context_run_limits_accept_exact_and_retain_one_token_overage(tmp_path):
    limits = {**REQUIRED_LIMITS,
              "total_tokens": CONTEXT_TOTAL_TOKENS_PER_RUN,
              "haiku_input_tokens": CONTEXT_HAIKU_INPUT_PER_RUN,
              "haiku_output_tokens": CONTEXT_HAIKU_OUTPUT_PER_RUN}
    with RunLedger(tmp_path / "exact", MANIFEST, limits) as ledger:
        ledger.finish(_dispatched(ledger), _receipt(
            input_tokens=CONTEXT_HAIKU_INPUT_PER_RUN, output_tokens=0,
            cache_creation=0, cache_read=0,
            haiku=(CONTEXT_HAIKU_INPUT_PER_RUN, 0, 0, 0)), accepted=True)
        assert ledger.summary()["haiku_input_tokens"] == CONTEXT_HAIKU_INPUT_PER_RUN
        with pytest.raises(PilotRefusal, match="haiku_input_budget_exceeded"):
            ledger.reserve("claude:position", "claude")
    over_run = tmp_path / "over"
    with RunLedger(over_run, MANIFEST, limits) as ledger:
        with pytest.raises(PilotRefusal, match="haiku_input_budget_exceeded"):
            ledger.finish(_dispatched(ledger), _receipt(
                input_tokens=CONTEXT_HAIKU_INPUT_PER_RUN + 1, output_tokens=0,
                cache_creation=0, cache_read=0,
                haiku=(CONTEXT_HAIKU_INPUT_PER_RUN + 1, 0, 0, 0)), accepted=True)
    assert str(CONTEXT_HAIKU_INPUT_PER_RUN + 1) in (over_run / "ledger.jsonl").read_text()


def test_missing_helper_map_halts_and_active_interrupt_is_visible(tmp_path):
    with RunLedger(tmp_path / "missing-helper", MANIFEST, REQUIRED_LIMITS) as ledger:
        receipt = {"usage": _receipt()["usage"]}
        with pytest.raises(PilotRefusal, match="helper_usage_unknown"):
            ledger.finish(_dispatched(ledger), receipt, accepted=True)
        assert ledger.summary()["accounting_complete"] is False
        assert ledger.summary()["usage"] is None
        assert ledger.summary()["known_usage"] == _receipt()["usage"]
    with RunLedger(tmp_path / "interrupted", MANIFEST, REQUIRED_LIMITS) as ledger:
        attempt = ledger.reserve("claude:position", "claude")
        ledger.halt("interrupted")
        summary = ledger.summary()
        assert summary["active_attempt"]["id"] == attempt
        assert summary["accounting_complete"] is False


def test_traversal_path_refuses(tmp_path):
    with pytest.raises(PilotRefusal, match="ledger_path_invalid"):
        RunLedger(tmp_path / "base" / ".." / "run", MANIFEST, REQUIRED_LIMITS)
