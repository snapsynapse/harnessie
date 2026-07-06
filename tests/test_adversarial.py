"""Adversarial contested phases: positions -> objections -> record -> arbitration.

Modeled on AIDR's record lifecycle (positions with metadata, preserved dissent,
human-only arbitration, structurally earned claims) and Turnfile's bounded
rebuttal rounds. The harness assembles the record; no agent and no harness
code path ever writes the Arbitration section.
"""

import textwrap
import re

from harness.adversarial import (
    PositionRecord,
    assemble_record,
    converged,
    lint_record,
    parse_objection_response,
    parse_stance,
)
from harness.ids import verify_check_digit
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall
from harness.runner import WorkflowRunner


# -- stance / objection parsing (fail closed) ----------------------------------

def test_parse_stance_last_object_wins():
    report = ('I considered {"stance": "oppose", "summary": "early quote"} but '
              'concluded:\n{"stance": "recommend", "summary": "Do it."}')
    st = parse_stance(report)
    assert st["stance"] == "recommend" and st["summary"] == "Do it."


def test_parse_stance_unknown_value_fails_closed():
    assert parse_stance('{"stance": "maybe", "summary": "eh"}') is None


def test_parse_stance_missing_fails_closed():
    assert parse_stance("no json here at all") is None


def test_parse_objection_response():
    out = parse_objection_response('{"objections": ["breaks resume"], '
                                   '"no_new_objection": false}')
    assert out["objections"] == ["breaks resume"]


def test_parse_objection_garbage_fails_closed():
    assert parse_objection_response("sure, sounds fine") is None


# -- convergence rule ----------------------------------------------------------

def _pos(label, stance, provider="mock", model_id="mock"):
    return PositionRecord(label=label, agent=label, model_id=model_id,
                          provider=provider, stance=stance,
                          summary=f"{label} says {stance}", prose="prose")


def test_unanimous_recommend_no_objections_converges():
    assert converged([_pos("a", "recommend"), _pos("b", "recommend")], [])


def test_any_oppose_blocks_convergence():
    assert not converged([_pos("a", "recommend"), _pos("b", "oppose")], [])


def test_any_objection_blocks_convergence():
    assert not converged([_pos("a", "recommend"), _pos("b", "recommend")],
                         [{"by": "b", "to": "a", "text": "risk"}])


def test_unparsed_stance_blocks_convergence():
    # fail closed: uncertainty forces arbitration, never silent convergence
    assert not converged([_pos("a", "recommend"), _pos("b", "unparsed")], [])


# -- record assembly + structural lint + earned claims ---------------------------

def test_assembled_record_lints_clean_and_earns_independence():
    text = assemble_record(
        record_id="DR-choose", title="Choose the storage layer",
        question="SQLite or JSONL?", context="Cache layer decision.",
        arbiter="operator",
        positions=[_pos("analyst", "recommend", provider="anthropic",
                        model_id="claude-fable-5"),
                   _pos("skeptic", "oppose", provider="openai-compat",
                        model_id="qwen3.6:35b-mlx")],
        objections=[{"by": "skeptic", "to": "analyst", "text": "JSONL diffable"}],
        evidence=["runs/x/events.jsonl - hash-chained event log"])
    lint = lint_record(text)
    assert lint["errors"] == []
    assert lint["status"] == "open"
    assert "independent-positions" in lint["claims"]
    assert "human-arbitrated" not in lint["claims"]
    ref = re.search(r"^ref: DR-([0-9ACDFGHJKMNPRUWY]{6})$", text, re.MULTILINE)
    assert ref and verify_check_digit(ref.group(1))


def test_same_provider_earns_no_independence_claim():
    text = assemble_record(
        record_id="DR-x", title="T", question="Q?", context="C",
        arbiter="operator",
        positions=[_pos("a", "recommend"), _pos("b", "recommend")],
        objections=[], evidence=[])
    assert "independent-positions" not in lint_record(text)["claims"]


def test_human_arbitration_flips_claims():
    text = assemble_record(
        record_id="DR-x", title="T", question="Q?", context="C",
        arbiter="operator",
        positions=[_pos("a", "recommend", provider="p1"),
                   _pos("b", "oppose", provider="p2")],
        objections=[{"by": "b", "to": "a", "text": "risk"}], evidence=[])
    # simulate the HUMAN editing the record file (never harness code)
    text = text.replace("status: open", "status: arbitrated")
    text = text.replace("date: ", "decided: 2026-07-06\ndate: ", 1)
    text = text.replace(
        "## Arbitration\n",
        textwrap.dedent("""\
        ## Arbitration

        - decided_by: operator
        - date: 2026-07-06
        - decision: Ship the analyst approach; skeptic objection deferred to 0.3.

        Rationale addressing the objection.
        """))
    lint = lint_record(text)
    assert lint["errors"] == []
    assert "human-arbitrated" in lint["claims"]
    assert "dissent-preserved" in lint["claims"]
    assert "Ship the analyst approach" in lint["decision"]


# -- workflow integration --------------------------------------------------------

def _scaffold(root):
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
    (root / "workflows" / "adv.yaml").write_text(textwrap.dedent("""
        name: adv
        phases:
          - name: decide
            mode: adversarial
            task: "Decide: {goal}"
            positions:
              - { agent: implementer }
              - { agent: implementer }
    """))


def _complete(report, idx):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=f"c{idx}", name="task_complete",
                                              arguments={"report": report})])


def _run(root, run_id, script):
    runner = WorkflowRunner(project_root=root, run_id=run_id, echo=False)
    runner._models["mid"] = MockModel(
        ModelSpec(name="mid", provider="mock", model_id="mock"), script=script)
    outcomes = runner.run_workflow(root / "workflows" / "adv.yaml", goal="the thing")
    return runner, outcomes


NO_OBJ = '{"objections": [], "no_new_objection": true}'


def test_convergence_passes_and_writes_record(tmp_path):
    _scaffold(tmp_path)
    _, outcomes = _run(tmp_path, "r1", [
        _complete('{"stance": "recommend", "summary": "Yes."}', 1),
        _complete('{"stance": "recommend", "summary": "Also yes."}', 2),
        _complete(NO_OBJ, 3),
        _complete(NO_OBJ, 4),
    ])
    assert [o.status for o in outcomes] == ["passed"]
    record = tmp_path / "runs" / "r1" / "decisions" / "DR-decide.md"
    assert record.exists()
    lint = lint_record(record.read_text())
    assert lint["errors"] == [] and lint["status"] == "open"


def test_dissent_halts_needs_arbitration(tmp_path):
    _scaffold(tmp_path)
    _, outcomes = _run(tmp_path, "r2", [
        _complete('{"stance": "recommend", "summary": "Yes."}', 1),
        _complete('{"stance": "oppose", "summary": "No: it breaks resume."}', 2),
        _complete(NO_OBJ, 3),
        _complete('{"objections": ["resume regression"], "no_new_objection": false}', 4),
    ])
    assert [o.status for o in outcomes] == ["needs_arbitration"]
    record = tmp_path / "runs" / "r2" / "decisions" / "DR-decide.md"
    text = record.read_text()
    assert "oppose" in text and "resume regression" in text   # dissent preserved
    assert re.search(r"^ref: DR-[0-9ACDFGHJKMNPRUWY]{6}$", text, re.MULTILINE)


def test_position_agents_are_read_only(tmp_path):
    _scaffold(tmp_path)
    write = AssistantTurn(content="", stop_reason="tool_use",
                          tool_calls=[ToolCall(id="w", name="write_file",
                                               arguments={"path": "sneak.txt",
                                                          "content": "x"})])
    _run(tmp_path, "r3", [
        write,   # position agent attempts a side effect: refused
        _complete('{"stance": "recommend", "summary": "Yes."}', 1),
        _complete('{"stance": "recommend", "summary": "Yes."}', 2),
        _complete(NO_OBJ, 3),
        _complete(NO_OBJ, 4),
    ])
    assert not (tmp_path / "workspace" / "sneak.txt").exists()


def test_human_arbitration_resumes_phase_to_passed(tmp_path):
    _scaffold(tmp_path)
    _run(tmp_path, "r4", [
        _complete('{"stance": "recommend", "summary": "Yes."}', 1),
        _complete('{"stance": "oppose", "summary": "No."}', 2),
        _complete(NO_OBJ, 3),
        _complete('{"objections": ["cost"], "no_new_objection": false}', 4),
    ])
    record = tmp_path / "runs" / "r4" / "decisions" / "DR-decide.md"
    # the HUMAN arbitrates by editing the file directly
    text = record.read_text()
    text = text.replace("status: open", "status: arbitrated")
    text = text.replace("date: ", "decided: 2026-07-06\ndate: ", 1)
    text = text.replace(
        "## Arbitration\n",
        "## Arbitration\n\n- decided_by: operator\n- date: 2026-07-06\n"
        "- decision: Proceed; cost objection accepted as a budget line.\n\n"
        "Rationale.\n")
    record.write_text(text)
    _, outcomes = _run(tmp_path, "r4", [])   # resume: lint only, no model calls
    assert [o.status for o in outcomes] == ["passed"]
    assert "Proceed; cost objection accepted" in outcomes[0].report


def test_unarbitrated_resume_stays_halted(tmp_path):
    _scaffold(tmp_path)
    _run(tmp_path, "r5", [
        _complete('{"stance": "recommend", "summary": "Yes."}', 1),
        _complete('{"stance": "oppose", "summary": "No."}', 2),
        _complete(NO_OBJ, 3),
        _complete(NO_OBJ, 4),
    ])
    _, outcomes = _run(tmp_path, "r5", [])
    assert [o.status for o in outcomes] == ["needs_arbitration"]
