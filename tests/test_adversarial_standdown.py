"""SEC-20261118-013: a quiet objection round converges only when every
participant returns a valid empty objection list AND literal boolean
no_new_objection true. Anything else is dissent that reaches arbitration."""

import json
import textwrap

import pytest

from harness.adversarial import parse_objection_response
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner

RECOMMEND = '{"stance": "recommend", "summary": "Yes."}'
STAND_DOWN = '{"objections": [], "no_new_objection": true}'


@pytest.mark.parametrize("marker", ['"no_new_objection": false', "",
                                    '"no_new_objection": "true"',
                                    '"no_new_objection": null',
                                    '"no_new_objection": 1'])
def test_non_literal_true_is_not_a_stand_down(marker):
    body = '{"objections": []' + (", " + marker if marker else "") + "}"
    parsed = parse_objection_response(body)
    assert parsed is not None and parsed["no_new_objection"] is False


def test_literal_true_is_a_stand_down():
    assert parse_objection_response(STAND_DOWN)["no_new_objection"] is True


@pytest.mark.parametrize("items", ['[{"text": "x"}]', "[3]", "[null]", '[""]',
                                   '["ok", ["nested"]]'])
def test_malformed_objection_items_fail_closed(items):
    body = '{"objections": ' + items + ', "no_new_objection": true}'
    assert parse_objection_response(body) is None


def _scaffold(root, rounds=1):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock
        routing:
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    (root / "workflows" / "adv.yaml").write_text(textwrap.dedent(f"""
        name: adv
        phases:
          - name: decide
            mode: adversarial
            task: "Decide: {{goal}}"
            rebuttal_rounds: {rounds}
            positions:
              - {{ agent: implementer }}
              - {{ agent: implementer }}
    """))


def _complete(report, idx):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=f"c{idx}", name="task_complete",
                                              arguments={"report": report})])


def _run(root, reports):
    runner = WorkflowRunner(project_root=root, run_id="standdown", echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"),
        script=[_complete(r, i) for i, r in enumerate(reports, 1)])
    outcomes = runner.run_workflow(root / "workflows" / "adv.yaml", goal="x")
    events = [json.loads(line) for line in
              (runner.run_dir / "events.jsonl").read_text().splitlines()
              if line.strip()]
    return [o.status for o in outcomes], events


@pytest.mark.parametrize("second", [
    '{"objections": [], "no_new_objection": false}',
    '{"objections": []}',
    '{"objections": [], "no_new_objection": "true"}',
    '{"objections": [], "no_new_objection": null}',
    '{"objections": ["a real risk"], "no_new_objection": true}',
    '{"objections": [42], "no_new_objection": true}',
])
def test_missing_or_false_stand_down_reaches_arbitration(tmp_path, second):
    _scaffold(tmp_path)
    statuses, events = _run(tmp_path, [RECOMMEND, RECOMMEND, STAND_DOWN, second])
    assert statuses == ["needs_arbitration"]
    assert not any(e["kind"] == "decision_converged" for e in events)
    assert any(e["kind"] == "objection_recorded" and e["by"] == "implementer-2"
               for e in events)


def test_unanimous_literal_stand_down_converges(tmp_path):
    _scaffold(tmp_path)
    statuses, events = _run(tmp_path,
                            [RECOMMEND, RECOMMEND, STAND_DOWN, STAND_DOWN])
    assert statuses == ["passed"]
    assert any(e["kind"] == "decision_converged" for e in events)
    assert not any(e["kind"] == "objection_recorded" for e in events)


def test_non_stand_down_round_continues_within_bounds(tmp_path):
    """A round without explicit stand-down is not quiet: the next bounded
    round still runs, and the recorded dissent forces arbitration."""
    _scaffold(tmp_path, rounds=2)
    statuses, events = _run(tmp_path, [
        RECOMMEND, RECOMMEND,
        STAND_DOWN, '{"objections": []}',
        STAND_DOWN, STAND_DOWN,
    ])
    assert statuses == ["needs_arbitration"]
    roles = [e for e in events if e["kind"] == "role_start"]
    assert len(roles) == 6
