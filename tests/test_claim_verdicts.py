import json

from harness.verify import CLAIM_STATUSES, PARSER_VERSION, parse_verdict


def structured(*claims, **extra):
    return json.dumps({"version": 2, "claims": list(claims), **extra})


def test_legacy_contract_remains_compatible():
    passed = parse_verdict('{"passed": true, "reasons": "checked"}')
    failed = parse_verdict('{"passed": false, "reasons": "broken"}')

    assert PARSER_VERSION == "2"
    assert passed.passed is True
    assert passed.overall_status == "verified"
    assert passed.reasons == "checked"
    assert passed.claims == ()
    assert failed.passed is False
    assert failed.overall_status == "failed"


def test_all_required_claims_reproduced_is_verified():
    verdict = parse_verdict(structured(
        {"id": "parser", "status": "reproduced",
         "evidence": ["pytest.log", "diff.patch"]},
        {"claim_id": "message", "status": "reproduced",
         "reason": "exact text matched"},
    ))

    assert CLAIM_STATUSES == {"reproduced", "refuted", "not_verifiable"}
    assert verdict.passed is True
    assert verdict.overall_status == "verified"
    assert verdict.reasons == "all required claims reproduced"
    assert [claim.claim_id for claim in verdict.claims] == ["parser", "message"]
    assert verdict.claims[0].evidence == ("pytest.log", "diff.patch")


def test_any_required_refutation_deterministically_fails():
    verdict = parse_verdict(structured(
        {"id": "works", "status": "reproduced"},
        {"id": "safe", "status": "not_verifiable"},
        {"id": "bounded", "status": "refuted", "reason": "escaped root"},
    ))

    assert verdict.passed is False
    assert verdict.overall_status == "failed"
    assert "bounded: refuted (escaped root)" in verdict.reasons


def test_unverifiable_required_claim_without_refutation_cannot_verify():
    verdict = parse_verdict(structured(
        {"id": "implementation", "status": "reproduced"},
        {"id": "historical-run", "status": "not_verifiable",
         "evidence": "missing.log"},
        reasons="historical execution evidence was not retained",
    ))

    assert verdict.passed is False
    assert verdict.overall_status == "cannot_verify"
    assert verdict.reasons == "historical execution evidence was not retained"
    assert verdict.claims[1].evidence == ("missing.log",)


def test_optional_claims_are_retained_but_do_not_control_overall_status():
    verdict = parse_verdict(structured(
        {"id": "required", "status": "reproduced"},
        {"id": "nice-to-have", "status": "refuted", "required": False},
        {"id": "history", "status": "not_verifiable", "required": False},
    ))

    assert verdict.passed is True
    assert verdict.overall_status == "verified"
    assert [claim.required for claim in verdict.claims] == [True, False, False]


def test_structured_verdict_ignores_supplied_passed_and_derives_result():
    verdict = parse_verdict(json.dumps({
        "passed": True,
        "claims": [{"id": "security", "status": "refuted"}],
    }))

    assert verdict.passed is False
    assert verdict.overall_status == "failed"


def test_last_legacy_or_structured_verdict_object_wins():
    report = (
        'Example: {"passed": true}.\n'
        + structured({"id": "actual", "status": "not_verifiable"})
    )
    verdict = parse_verdict(report)

    assert verdict.overall_status == "cannot_verify"
    assert verdict.claims[0].claim_id == "actual"


def test_malformed_structured_verdicts_fail_closed():
    malformed = [
        {"claims": []},
        {"claims": ["not-an-object"]},
        {"claims": [{"status": "reproduced"}]},
        {"claims": [{"id": "x", "status": "unknown"}]},
        {"claims": [{"id": "x", "status": "reproduced", "required": "yes"}]},
        {"claims": [{"id": "x", "status": "reproduced", "reason": 3}]},
        {"claims": [{"id": "x", "status": "reproduced", "evidence": [3]}]},
        {"claims": [
            {"id": "x", "status": "reproduced"},
            {"id": "x", "status": "reproduced"},
        ]},
        {"claims": [
            {"id": "optional", "status": "reproduced", "required": False},
        ]},
        {"claims": [{"id": "x", "status": "reproduced"}], "reasons": []},
    ]

    for payload in malformed:
        verdict = parse_verdict(json.dumps(payload))
        assert verdict.passed is False, payload
        assert verdict.overall_status == "cannot_verify", payload
        assert "failing closed" in verdict.reasons, payload


def test_absent_verdict_fails_closed_as_cannot_verify():
    verdict = parse_verdict("review complete, looks fine")

    assert verdict.passed is False
    assert verdict.overall_status == "cannot_verify"
    assert verdict.claims == ()
