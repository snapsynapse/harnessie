"""Eval scenarios are validated per kind, so no assertion can be ignored.

SEC-20261118-018: a misspelled or unsupported `expect_*` key, a wrong type, a
duplicate scenario ID, or an empty assertion must fail the case instead of
producing a green result that never tested anything. The mutation tests prove
every supported assertion on every kind can turn a passing case red.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from harness.evals import SCENARIO_KINDS, run_eval_suite, run_scenario


ROOT = Path(__file__).resolve().parents[1]
MUTATED = "__mutated__"


def _shipped() -> list[dict]:
    scenarios = []
    for path in sorted((ROOT / "evals").glob("*.yaml")):
        scenarios.extend(yaml.safe_load(path.read_text(encoding="utf-8"))["scenarios"])
    return scenarios


SHIPPED = _shipped()
BASE_BY_KIND = {}
for _scenario in SHIPPED:
    BASE_BY_KIND.setdefault(_scenario["kind"], _scenario)

# Assertions no shipped fixture exercises get a passing supplemental fixture,
# so the mutation sweep still reaches every supported (kind, assertion) pair.
_WORKFLOW_SCRIPT = next(s for s in SHIPPED
                        if s["id"] == "golden_workflow_all_phases_pass")["script"]
SUPPLEMENTAL = [
    {"id": "supplemental_workflow_events_absent", "kind": "workflow",
     "script": _WORKFLOW_SCRIPT, "expect_statuses": ["passed", "passed", "passed"],
     "expect_events_absent": ["AKIACANARY0SUPPLEMENT"]},
    {"id": "supplemental_loop_file_and_absent", "kind": "loop",
     "script": [{"tool": "write_file", "args": {"path": "a.txt", "content": "alpha"}},
                {"tool": "task_complete", "args": {"report": "done"}}],
     "expect_stop": "complete",
     "expect_file": {"path": "a.txt", "contains": "alpha"},
     "expect_file_absent": "b.txt"},
]


def _invalid_codes(result) -> list[str]:
    observed = result.observed
    assert isinstance(observed, dict) and "invalid_scenario" in observed, observed
    return observed["invalid_scenario"]


def _assertion_keys(scenario: dict) -> list[str]:
    return sorted(k for k in scenario
                  if k in SCENARIO_KINDS[scenario["kind"]]["assertions"])


def _mutate(kind: str, key: str, value):
    """Return a value for `key` that the observed run cannot satisfy."""
    if isinstance(value, bool):
        return not value
    if key == "expect_status":
        return {"exported": "refused", "refused": "exported"}[value]
    if key == "expect_file_absent":
        return "."  # the workspace itself always exists
    if key == "expect_root_absent" or (kind == "blast_radius" and key == "expect_absent"):
        return [*value, "."]
    if key in ("expect_events_absent", "deny_contains", "expect_markdown_absent") or (
            kind == "canary_leak" and key == "expect_absent"):
        return [*value, " "]  # every event line, document and narrative has a space
    if key == "expect_elapsed_lt":
        return 0
    if key == "expect_file":
        return {**value, "path": f"{MUTATED}/missing.txt"}
    if key == "expect_refusal":
        return {**value, "error": MUTATED}
    if isinstance(value, str):
        return value + MUTATED
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, list):
        return [*value, MUTATED]
    if isinstance(value, dict):
        def scalar(item):
            if item is None:
                return MUTATED
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                return item + 1
            return f"{item}{MUTATED}"
        return {k: scalar(v) for k, v in value.items()}
    raise AssertionError(f"no mutation for {kind}.{key}={value!r}")


MUTATION_CASES = [
    pytest.param(scenario, key, id=f"{scenario['id']}::{key}")
    for scenario in [*SHIPPED, *SUPPLEMENTAL]
    for key in _assertion_keys(scenario)
]


def test_every_kind_declares_assertions_and_is_dispatched():
    assert set(SCENARIO_KINDS) == {s["kind"] for s in SHIPPED}
    for kind, spec in SCENARIO_KINDS.items():
        assert spec["assertions"], kind
        assert not set(spec["assertions"]) & set(spec["inputs"]), kind


def test_all_shipped_suites_validate_and_pass():
    scorecard = run_eval_suite(ROOT)
    assert scorecard["total"] == len(SHIPPED) > 0
    failing = [r for r in scorecard["results"] if not r["passed"]]
    assert failing == []


@pytest.mark.parametrize("scenario", SUPPLEMENTAL, ids=lambda s: s["id"])
def test_supplemental_fixtures_pass(scenario):
    result = run_scenario(scenario, root=ROOT)
    assert result.passed, result.observed


def test_mutation_sweep_reaches_every_supported_assertion():
    reached = {(s["kind"], k) for s in [*SHIPPED, *SUPPLEMENTAL] for k in _assertion_keys(s)}
    supported = {(kind, key) for kind, spec in SCENARIO_KINDS.items()
                 for key in spec["assertions"]}
    assert supported - reached == set()


@pytest.mark.parametrize("scenario,key", MUTATION_CASES)
def test_every_assertion_can_fail(scenario, key):
    mutated = {**scenario, key: _mutate(scenario["kind"], key, scenario[key])}
    result = run_scenario(mutated, root=ROOT)
    assert not result.passed
    # The failure is the assertion firing, not the validator rejecting the
    # mutated value: the mutation keeps the scenario well formed.
    assert not (isinstance(result.observed, dict)
                and "invalid_scenario" in result.observed), result.observed


@pytest.mark.parametrize("kind", sorted(BASE_BY_KIND))
def test_unknown_expectation_is_rejected_for_every_kind(kind):
    result = run_scenario({**BASE_BY_KIND[kind], "expect_not_a_real_property": True},
                          root=ROOT)
    assert not result.passed
    assert "unknown_key:expect_not_a_real_property" in _invalid_codes(result)


@pytest.mark.parametrize("kind", sorted(BASE_BY_KIND))
def test_unknown_input_is_rejected_for_every_kind(kind):
    result = run_scenario({**BASE_BY_KIND[kind], "tampr": True}, root=ROOT)
    assert not result.passed
    assert "unknown_key:tampr" in _invalid_codes(result)


@pytest.mark.parametrize("kind", sorted(BASE_BY_KIND))
def test_assertion_from_another_kind_is_rejected(kind):
    foreign = "expect_stop" if kind != "loop" else "expect_statuses"
    result = run_scenario({**BASE_BY_KIND[kind], foreign: "complete"}, root=ROOT)
    assert not result.passed
    assert f"unknown_key:{foreign}" in _invalid_codes(result)


def test_loop_scenario_with_impossible_security_property_fails():
    # The exact evidence from the finding: this used to pass unchanged.
    scenario = {**BASE_BY_KIND["loop"], "expect_impossible_security_property": True}
    assert "unknown_key:expect_impossible_security_property" in _invalid_codes(
        run_scenario(scenario, root=ROOT))


@pytest.mark.parametrize("kind,key,value", [
    ("verdict", "expect_passed", "false"),
    ("workflow", "expect_statuses", "passed"),
    ("loop", "expect_stop", 1),
    ("loop", "expect_refusal", ["refusal"]),
    ("loop", "expect_file", {"path": "a.txt", "contians": "typo"}),
    ("plugin", "expect_admitted", "yes"),
    ("parallel", "expect_elapsed_lt", "fast"),
    ("observer", "expect_phase_count", True),
])
def test_wrong_assertion_type_is_rejected(kind, key, value):
    result = run_scenario({**BASE_BY_KIND[kind], key: value}, root=ROOT)
    assert not result.passed
    assert f"wrong_type:{key}" in _invalid_codes(result)


@pytest.mark.parametrize("kind,key,value", [
    ("loop", "expect_events_absent", []),
    ("loop", "expect_refusal", {}),
    ("loop", "expect_trace", {}),
    ("workflow", "expect_events_contain", []),
    ("canary_leak", "expect_absent", []),
    ("parallel", "expect_files", {}),
    ("audit", "expect_timeline_kinds", []),
    ("repo_hygiene", "require_contains", []),
    ("triage", "expect_fact", None),
])
def test_empty_assertion_is_rejected_as_vacuous(kind, key, value):
    result = run_scenario({**BASE_BY_KIND[kind], key: value}, root=ROOT)
    assert not result.passed
    assert f"vacuous:{key}" in _invalid_codes(result)


@pytest.mark.parametrize("kind,key", [
    ("verdict", "expect_passed"),
    ("loop", "expect_stop"),
    ("workflow", "expect_statuses"),
    ("plugin", "expect_admitted"),
    ("aidr_export", "expect_status"),
    ("canary_leak", "expect_absent"),
    ("blast_radius", "limits"),
    ("repo_hygiene", "paths"),
])
def test_missing_required_key_is_rejected(kind, key):
    scenario = {k: v for k, v in BASE_BY_KIND[kind].items() if k != key}
    result = run_scenario(scenario, root=ROOT)
    assert not result.passed
    assert f"missing_required:{key}" in _invalid_codes(result)


@pytest.mark.parametrize("kind", ["observer", "ownership", "audit", "repo_hygiene"])
def test_scenario_without_any_assertion_is_rejected(kind):
    spec = SCENARIO_KINDS[kind]
    scenario = {k: v for k, v in BASE_BY_KIND[kind].items() if k not in spec["assertions"]}
    result = run_scenario(scenario, root=ROOT)
    assert not result.passed
    assert "no_assertions" in _invalid_codes(result)


def test_audit_expect_after_without_tamper_is_rejected():
    scenario = {"id": "a", "kind": "audit", "expect_after": False}
    assert "conflict:expect_after" in _invalid_codes(run_scenario(scenario, root=ROOT))


def test_adversarial_mixing_single_and_arbitrated_expectations_is_rejected():
    base = next(s for s in SHIPPED
                if s["kind"] == "adversarial" and "arbitration_text" in s)
    result = run_scenario({**base, "expect_statuses": ["needs_arbitration"]}, root=ROOT)
    assert "conflict:expect_statuses" in _invalid_codes(result)


def test_missing_or_non_string_id_is_rejected():
    result = run_scenario({"kind": "verdict", "report": "{}", "expect_passed": False})
    assert result.id == "(missing-id)"
    assert "missing_required:id" in _invalid_codes(result)
    result = run_scenario({"id": 7, "kind": "verdict", "report": "{}",
                           "expect_passed": False})
    assert "wrong_type:id" in _invalid_codes(result)


def test_repo_hygiene_paths_matching_nothing_fail(tmp_path):
    scenario = {"id": "h", "kind": "repo_hygiene", "paths": ["nothing/*.md"],
                "deny_contains": ["/Users/"]}
    result = run_scenario(scenario, root=tmp_path)
    assert not result.passed


def _write_suite(path: Path, payload) -> Path:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_duplicate_scenario_ids_fail_the_suite(tmp_path):
    verdict = {"id": "same", "kind": "verdict",
               "report": '{"passed": true, "reasons": "ok"}', "expect_passed": True}
    suite = _write_suite(tmp_path / "dup.yaml", {"name": "dup", "scenarios": [verdict, verdict]})
    scorecard = run_eval_suite(tmp_path, suite)
    assert scorecard["passed"] < scorecard["total"]
    duplicates = [r for r in scorecard["results"]
                  if isinstance(r["observed"], dict)
                  and "duplicate_id:same" in r["observed"].get("invalid_scenario", [])]
    assert len(duplicates) == 1


def test_duplicate_ids_across_suite_files_fail(tmp_path):
    (tmp_path / "evals").mkdir()
    verdict = {"id": "same", "kind": "verdict",
               "report": '{"passed": true, "reasons": "ok"}', "expect_passed": True}
    for name in ("a.yaml", "b.yaml"):
        _write_suite(tmp_path / "evals" / name, {"name": name, "scenarios": [verdict]})
    scorecard = run_eval_suite(tmp_path)
    assert scorecard["passed"] == 1 and scorecard["total"] == 2


@pytest.mark.parametrize("payload,code", [
    ({"name": "typo", "scenario": [{"id": "x"}]}, "unknown_suite_key:scenario"),
    ({"name": "empty", "scenarios": []}, "vacuous:scenarios"),
    ({"name": "shape", "scenarios": {"id": "x"}}, "wrong_type:scenarios"),
    ({"name": "item", "scenarios": ["not-a-mapping"]}, "wrong_type:scenario"),
])
def test_malformed_suite_fails_instead_of_running_nothing(tmp_path, payload, code):
    suite = _write_suite(tmp_path / "bad.yaml", payload)
    scorecard = run_eval_suite(tmp_path, suite)
    assert scorecard["total"] >= 1
    assert scorecard["passed"] < scorecard["total"]
    codes = [c for r in scorecard["results"] if isinstance(r["observed"], dict)
             for c in r["observed"].get("invalid_scenario", [])]
    assert code in codes
