"""Containment boundary: strip/rehydrate determinism, secret egress halt,
strip-map lifecycle (fail-closed resume), and deny-all rehydration grants.
Canary values are fake; a passing run proves they land only where intended.
"""

import json

import pytest

from harness.boundary import (
    Boundary,
    COVERAGE,
    RehydrationGrants,
    SecretEgressHalt,
    StripMap,
    scrub_tool_result,
)


EMAIL = "casey@example.com"
PHONE = "415-555-0187"
SSN_TEXT = "ssn: 078-05-1120"


def test_strip_replaces_pii_with_stable_placeholders():
    b = Boundary()
    r = b.strip(f"Contact {EMAIL} or {PHONE} about the {SSN_TEXT} record")
    assert EMAIL not in r.stripped
    assert PHONE not in r.stripped
    assert "078-05-1120" not in r.stripped
    assert "[EMAIL_1]" in r.stripped
    assert r.mapping["[EMAIL_1]"] == EMAIL
    kinds = {k for k, _ in r.found}
    assert {"EMAIL", "PHONE", "SSN"} <= kinds


def test_same_value_same_placeholder_across_calls():
    b = Boundary()
    r1 = b.strip(f"first: {EMAIL}")
    r2 = b.strip(f"again: {EMAIL} and new: other@example.org", r1.mapping)
    assert "[EMAIL_1]" in r2.stripped        # continuity for the repeat
    assert "[EMAIL_2]" in r2.stripped        # counter continues, no collision
    assert r2.mapping["[EMAIL_1]"] == EMAIL
    assert r2.mapping["[EMAIL_2]"] == "other@example.org"


def test_multilingual_kinds_catch():
    b = Boundary()
    r = b.strip("CNIC 12345-1234567-1 and CURP GOMC900514HDFRRL09")
    kinds = {k for k, _ in r.found}
    assert "PK_CNIC" in kinds
    assert "MX_CURP" in kinds


def test_contextual_kinds_skipped_by_default_included_on_request():
    text = "routing: 021000021 on file"
    assert not Boundary().strip(text).has_pii
    r = Boundary(include_contextual=True).strip(text)
    assert ("ROUTING_NUMBER", "[ROUTING_NUMBER_1]") in r.found
    assert "021000021" not in r.stripped


def test_guard_egress_halts_on_secret_with_kinds_only():
    b = Boundary()
    payload = f"send {EMAIL} the key AKIACANARY0BOUNDARYT00"
    with pytest.raises(SecretEgressHalt) as exc:
        b.guard_egress(payload)
    assert "aws_access_key" in str(exc.value)
    assert "AKIACANARY0BOUNDARYT00" not in str(exc.value)   # never the value
    # and the secret never entered any mapping
    clean = b.strip(payload)
    assert "AKIACANARY0BOUNDARYT00" not in clean.mapping.values()


def test_guard_egress_passes_clean_payloads_stripped():
    r = Boundary().guard_egress(f"reach me at {EMAIL}")
    assert EMAIL not in r.stripped
    assert r.mapping["[EMAIL_1]"] == EMAIL


def test_rehydrate_round_trip_and_fail_closed_unknowns():
    b = Boundary()
    r = b.strip(f"email {EMAIL} phone {PHONE}")
    restored = Boundary.rehydrate(r.stripped, r.mapping)
    assert EMAIL in restored and PHONE in restored
    # an unknown placeholder is never guessed
    text = "see [EMAIL_9]"
    assert Boundary.rehydrate(text, r.mapping) == text
    assert Boundary.unrehydrated(text)
    assert not Boundary.unrehydrated(restored)


def test_strip_map_lives_outside_run_artifacts(tmp_path):
    m = StripMap.open(tmp_path, "run1")
    m.mapping["[EMAIL_1]"] = EMAIL
    m.save()
    assert m.path.exists()
    assert ".boundary" in str(m.path)
    assert "runs" not in m.path.parts and "workspace" not in m.path.parts
    assert (m.path.stat().st_mode & 0o777) == 0o600


def test_strip_map_resume_reloads_before_rehydration(tmp_path):
    m = StripMap.open(tmp_path, "run1")
    b = Boundary()
    r = b.strip(f"contact {EMAIL}", m.mapping)
    m.mapping = r.mapping
    m.save()

    resumed = StripMap.open(tmp_path, "run1", expect_existing=True)
    assert resumed.status == "loaded"
    assert resumed.rehydration_available
    assert Boundary.rehydrate("[EMAIL_1]", resumed.mapping) == EMAIL
    # continuity survives the resume: the same value keeps its placeholder
    r2 = b.strip(f"again {EMAIL}", resumed.mapping)
    assert "[EMAIL_1]" in r2.stripped


def test_strip_map_missing_on_resume_fails_closed(tmp_path):
    m = StripMap.open(tmp_path, "gone", expect_existing=True)
    assert m.status == "missing"
    assert not m.rehydration_available
    notice = m.degradation_notice()
    assert "fail-closed" in notice and "placeholders remain" in notice


def test_strip_map_corrupt_fails_closed_and_refuses_overwrite(tmp_path):
    directory = tmp_path / ".boundary"
    directory.mkdir()
    (directory / "run1.json").write_text("{not json")
    m = StripMap.open(tmp_path, "run1", expect_existing=True)
    assert m.status == "corrupt"
    assert not m.rehydration_available
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        m.save()
    # the corrupt file is preserved as evidence
    assert (directory / "run1.json").read_text() == "{not json"


def test_rehydration_grants_start_deny_all(tmp_path):
    grants = RehydrationGrants.load(tmp_path / "absent.yaml")
    m = StripMap.open(tmp_path, "run1")
    m.mapping["[EMAIL_1]"] = EMAIL
    out = grants.rehydrate_for_tool("send_email", "deliver", "[EMAIL_1]", m)
    assert out == "[EMAIL_1]"            # nothing granted, nothing rehydrated


def test_rehydration_grants_follow_approval_grammar(tmp_path):
    policy = tmp_path / "rehydrate.yaml"
    policy.write_text(
        "allow:\n  - tool: send_email\n    phase: deliver\n"
        "deny:\n  - tool: send_email\n    phase: triage\n")
    grants = RehydrationGrants.load(policy)
    m = StripMap.open(tmp_path, "run1")
    m.mapping["[EMAIL_1]"] = EMAIL

    granted = grants.rehydrate_for_tool("send_email", "deliver", "[EMAIL_1]", m)
    assert granted == EMAIL
    denied_phase = grants.rehydrate_for_tool("send_email", "triage", "[EMAIL_1]", m)
    assert denied_phase == "[EMAIL_1]"   # explicit deny wins
    unmatched = grants.rehydrate_for_tool("write_file", "deliver", "[EMAIL_1]", m)
    assert unmatched == "[EMAIL_1]"      # no match denies closed


def test_grant_plus_corrupt_map_still_returns_placeholders(tmp_path):
    policy = tmp_path / "rehydrate.yaml"
    policy.write_text("allow:\n  - tool: send_email\n")
    directory = tmp_path / ".boundary"
    directory.mkdir()
    (directory / "run1.json").write_text("[]")
    m = StripMap.open(tmp_path, "run1", expect_existing=True)
    grants = RehydrationGrants.load(policy)
    out = grants.rehydrate_for_tool("send_email", "deliver", "[EMAIL_1]", m)
    assert out == "[EMAIL_1]"            # grant alone is not enough


def test_scrub_tool_result_strips_pii_before_context():
    b = Boundary()
    r = scrub_tool_result(b, f"file contents: owner {EMAIL}, backup {PHONE}")
    assert EMAIL not in r.stripped and PHONE not in r.stripped


def test_coverage_table_names_the_unstructured_residual():
    rows = {row["data_class"]: row for row in COVERAGE}
    assert rows["structured PII"]["caught_by_filter"] is True
    assert rows["secrets"]["caught_by_filter"] is True
    assert rows["unstructured free-text PII"]["caught_by_filter"] is False
    assert "contained routing" in rows["unstructured free-text PII"]["mechanism"]
