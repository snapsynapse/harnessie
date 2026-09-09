"""Red-first falsifiers for bid rounds (AIDR-0009, open).

Tests carry per-test strict expected failures grouped by delivery slice.
Remove a marker only when its approved contract is implemented and verified.
Selection tests remain expected failures independently of record mode.

The contracts asserted here are the spec. Where the design draft was vague,
these tests choose: anchors derive only from declared workflow structure,
a `yes` without a pre-mortem is `no_bid`, `criterion:` entries score
`not_verifiable` until the in-run gate emits per-criterion verdicts.
"""

from __future__ import annotations

import json
import textwrap

import pytest

from harness import sandbox
from harness.models.base import AssistantTurn, MockModel, ModelSpec, ToolCall

bid_record_pending = pytest.mark.xfail(strict=True, reason="AIDR-0009: bid record and parsing pending")
bid_select_pending = pytest.mark.xfail(strict=True, reason="AIDR-0009: select requires separate decision")
bid_scorecard_pending = pytest.mark.xfail(strict=True, reason="bid calibration scorecard not yet implemented")


def _bidding():
    from harness import bidding
    return bidding


def turn_tool(name, args, call_id="c1"):
    return AssistantTurn(content="", stop_reason="tool_use",
                         tool_calls=[ToolCall(id=call_id, name=name, arguments=args)])


PHASE = {
    "name": "implement",
    "agent": "implementer",
    "task_class": "implement",
    "task": "Do this plan: {plan}",
    "writes": ["src/"],
    "deny_tools": ["run_shell"],
    "verify": {
        "checks": [{"name": "tests", "command": "pytest -q"}],
        "criteria": "Tests pass.\nNothing outside src/ changes.\n",
    },
}


def bid_report(bid="yes", confidence=0.7, premortem=None, needs=None,
               effort="medium"):
    obj = {"bid": bid, "confidence": confidence, "why": "fits", "effort": effort}
    if premortem is not None:
        obj["premortem"] = premortem
    if needs is not None:
        obj["needs"] = needs
    return "prose first\n" + json.dumps(obj)


CITED = [{"failure": "tests fail on fixture layout", "cites": ["check:tests"],
          "mitigation": "read conftest first"}]


# -- anchors: declared structure only ------------------------------------------

@bid_record_pending
def test_anchors_derive_only_from_declared_workflow_structure():
    anchors = _bidding().packet_anchors(PHASE)
    assert anchors == frozenset({
        "check:tests", "criterion:1", "criterion:2", "write:src/",
        "deny:run_shell", "input:plan"})


@bid_record_pending
def test_anchor_block_lists_every_anchor_for_the_bidder():
    block = _bidding().render_anchors(PHASE)
    for anchor in _bidding().packet_anchors(PHASE):
        assert anchor in block


# -- parsing and normalization: fail closed ---------------------------------------

@bid_record_pending
def test_unparseable_report_is_no_bid():
    b = _bidding()
    assert b.parse_bid("I can totally do this, trust me") is None
    bid = b.normalize_bid(None, b.packet_anchors(PHASE))
    assert bid.bid == "no_bid"


@bid_record_pending
def test_last_json_object_with_valid_bid_wins():
    b = _bidding()
    report = ('{"bid": "yes"} was an example; final: '
              + json.dumps({"bid": "no", "why": "cannot"}))
    parsed = b.parse_bid(report)
    assert parsed["bid"] == "no"


@bid_record_pending
def test_invalid_bid_value_is_no_bid():
    b = _bidding()
    parsed = b.parse_bid(bid_report(bid="maybe", premortem=CITED))
    bid = b.normalize_bid(parsed, b.packet_anchors(PHASE))
    assert bid.bid == "no_bid"


@bid_record_pending
def test_yes_without_premortem_is_no_bid():
    b = _bidding()
    bid = b.normalize_bid(b.parse_bid(bid_report(bid="yes")),
                          b.packet_anchors(PHASE))
    assert bid.bid == "no_bid"
    assert "premortem" in bid.reason


@bid_record_pending
def test_no_needs_no_premortem():
    b = _bidding()
    bid = b.normalize_bid(b.parse_bid(bid_report(bid="no")),
                          b.packet_anchors(PHASE))
    assert bid.bid == "no"


@bid_record_pending
def test_conditional_without_needs_degrades_to_no():
    b = _bidding()
    bid = b.normalize_bid(
        b.parse_bid(bid_report(bid="conditional", premortem=CITED)),
        b.packet_anchors(PHASE))
    assert bid.bid == "no"


@bid_record_pending
def test_premortem_with_zero_resolvable_citations_voids_the_bid():
    b = _bidding()
    generic = [{"failure": "tests might fail", "cites": ["vibes", "check:nope"],
                "mitigation": "try harder"}]
    bid = b.normalize_bid(b.parse_bid(bid_report(premortem=generic)),
                          b.packet_anchors(PHASE))
    assert bid.bid == "no_bid"
    assert "cite" in bid.reason


@bid_record_pending
def test_unresolvable_citations_are_dropped_but_resolvable_ones_keep_the_bid():
    b = _bidding()
    mixed = [{"failure": "x", "cites": ["check:tests", "check:nope"],
              "mitigation": "m"}]
    bid = b.normalize_bid(b.parse_bid(bid_report(premortem=mixed)),
                          b.packet_anchors(PHASE))
    assert bid.bid == "yes"
    assert bid.premortem[0].cites == ["check:tests"]


@bid_record_pending
def test_unmitigated_entry_degrades_yes_to_conditional():
    b = _bidding()
    entries = CITED + [{"failure": "src/ fence blocks the setting",
                        "cites": ["write:src/"]}]
    bid = b.normalize_bid(b.parse_bid(bid_report(premortem=entries)),
                          b.packet_anchors(PHASE))
    assert bid.bid == "conditional"
    assert bid.needs  # the unmitigated failure becomes a stated need


@bid_record_pending
def test_confidence_and_effort_are_recorded_not_validated_away():
    b = _bidding()
    bid = b.normalize_bid(
        b.parse_bid(bid_report(confidence=0.9, effort="xhigh", premortem=CITED)),
        b.packet_anchors(PHASE))
    assert bid.confidence == 0.9
    assert bid.effort == "xhigh"
    bid2 = b.normalize_bid(
        b.parse_bid(bid_report(confidence="high", premortem=CITED)),
        b.packet_anchors(PHASE))
    assert bid2.confidence is None   # unscoreable, never coerced


# -- ranking (select mode): harness code over declared config ----------------------

def _spec(name, cost_in, cost_out=0.0, provider="mock"):
    return ModelSpec(name=name, provider=provider, model_id=f"m-{name}",
                     cost_per_mtok_in=cost_in, cost_per_mtok_out=cost_out)


def _rec(tier, bid="yes", confidence=0.5, provider="mock"):
    b = _bidding()
    return b.BidRecord(tier=tier, model_id=f"m-{tier}", provider=provider,
                       bid=b.Bid(bid=bid, confidence=confidence))


@bid_select_pending
def test_select_orders_yes_bids_by_cost_then_calibration():
    b = _bidding()
    tiers = {"local": _spec("local", 0.0), "cheap": _spec("cheap", 1.0),
             "mid": _spec("mid", 3.0)}
    records = [_rec("mid"), _rec("cheap"), _rec("local")]
    sel = b.rank_bids(records, candidates=["local", "cheap", "mid"], tiers=tiers)
    assert sel.tier == "local"
    # same cost: calibration breaks the tie, confidence never does
    tiers["cheap2"] = _spec("cheap2", 1.0)
    records = [_rec("cheap", confidence=0.99), _rec("cheap2", confidence=0.1)]
    sel = b.rank_bids(records, candidates=["cheap", "cheap2"], tiers=tiers,
                      calibration={"cheap": 0.2, "cheap2": 0.9})
    assert sel.tier == "cheap2"


@bid_select_pending
def test_select_is_bounded_by_candidates_and_treats_conditional_as_no():
    b = _bidding()
    tiers = {"local": _spec("local", 0.0), "mid": _spec("mid", 3.0)}
    records = [_rec("local", bid="yes"), _rec("mid", bid="conditional")]
    sel = b.rank_bids(records, candidates=["mid"], tiers=tiers)
    assert sel.tier is None
    assert "no eligible" in sel.reason


@bid_select_pending
def test_select_contained_filters_exposed_tiers_before_ranking():
    b = _bidding()
    tiers = {"local": _spec("local", 0.0), "cheap": _spec("cheap", 1.0)}
    records = [_rec("cheap"), _rec("local")]
    sel = b.rank_bids(records, candidates=["cheap", "local"], tiers=tiers,
                      contained=True)
    assert sel.tier == "local"
    assert "cheap" in sel.reason and "exposed" in sel.reason


# -- pre-mortem scoring as claims ----------------------------------------------------

def _entry(cite):
    return _bidding().PremortemEntry(failure="f", cites=[cite], mitigation="m")


@bid_record_pending
def test_check_entry_reproduced_when_that_check_failed():
    b = _bidding()
    events = [{"kind": "check", "name": "tests", "passed": False, "attempt": 1},
              {"kind": "check", "name": "tests", "passed": True, "attempt": 2}]
    assert b.score_premortem(_entry("check:tests"), events) == "reproduced"


@bid_record_pending
def test_check_entry_refuted_when_that_check_only_passed():
    b = _bidding()
    events = [{"kind": "check", "name": "tests", "passed": True, "attempt": 1}]
    assert b.score_premortem(_entry("check:tests"), events) == "refuted"


@bid_record_pending
def test_check_entry_not_verifiable_when_check_never_ran():
    b = _bidding()
    assert b.score_premortem(_entry("check:tests"), []) == "not_verifiable"


@bid_record_pending
def test_deny_entry_reproduced_on_refusal_of_that_tool():
    b = _bidding()
    events = [{"kind": "refusal", "tool": "run_shell", "error": "action_unsupported"}]
    assert b.score_premortem(_entry("deny:run_shell"), events) == "reproduced"


@bid_record_pending
def test_criterion_entries_are_not_verifiable_in_v1():
    # The in-run gate verdict is {passed, reasons} prose. Until it emits
    # per-criterion structured verdicts, a criterion prediction cannot be
    # decided from events, and the scorer must say so rather than guess.
    b = _bidding()
    events = [{"kind": "gate_verdict", "attempt": 1, "passed": False,
               "reasons": "criterion 1 failed"}]
    assert b.score_premortem(_entry("criterion:1"), events) == "not_verifiable"


# -- calibration metrics ---------------------------------------------------------

def _outcome(tier, bid, dispatched, status, confidence=None, premortem=()):
    return {"kind": "bid_outcome", "phase": "implement", "tier": tier,
            "bid": bid, "dispatched": dispatched, "status": status,
            "confidence": confidence, "premortem_scores": list(premortem)}


@bid_record_pending
def test_bid_metrics_count_overclaim_honored_declined_unscored():
    b = _bidding()
    events = [
        _outcome("mid", "yes", True, "needs_human"),
        _outcome("local", "no", False, "needs_human"),
        _outcome("cheap", "yes", False, "needs_human"),
    ]
    m = b.bid_metrics(events)
    assert m["overclaim"] == 1
    assert m["honored"] == 0
    assert m["declined_correctly"] == 1
    assert m["unscored"] == 1


@bid_record_pending
def test_bid_metrics_brier_over_dispatched_bids_with_confidence():
    b = _bidding()
    events = [
        _outcome("mid", "yes", True, "passed", confidence=1.0),
        _outcome("mid", "yes", True, "needs_human", confidence=0.5),
        _outcome("mid", "yes", True, "passed", confidence=None),   # excluded
        _outcome("local", "yes", False, "passed", confidence=0.9),  # excluded
    ]
    m = b.bid_metrics(events)
    assert m["brier_n"] == 2
    assert m["brier"] == pytest.approx(((1.0 - 1) ** 2 + (0.5 - 0) ** 2) / 2)


@bid_record_pending
def test_bid_metrics_premortem_hit_rate_ignores_not_verifiable():
    b = _bidding()
    events = [_outcome("mid", "yes", True, "needs_human",
                       premortem=["reproduced", "refuted", "not_verifiable"])]
    m = b.bid_metrics(events)
    assert m["premortem_scored"] == 2
    assert m["premortem_hit_rate"] == 0.5


# -- scorecard opt-in ------------------------------------------------------------

@bid_scorecard_pending
def test_bid_scorecard_skips_without_live_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("HARNESSIE_LIVE", raising=False)
    result = _bidding().run_bid_scorecard(tmp_path, env={})
    assert result["status"] == "skipped"
    assert "HARNESSIE_LIVE=1" in result["notes"]


# -- runner integration: record mode changes nothing about dispatch ----------------

def scaffold(root, bid_block: str):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\n")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\n")
    (root / "agents" / "verifiers" / "code-verifier.md").write_text("# Verifier\n")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: mock
            model_id: mock-mid
            cost_per_mtok_in: 3.0
          local:
            provider: mock
            model_id: mock-local
            cost_per_mtok_in: 0.0
        routing:
          implement: { tier: mid, effort: medium }
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    (root / "workflows" / "wf.yaml").write_text(textwrap.dedent(f"""
        name: wf
        phases:
          - name: plan
            agent: orchestrator
            task: "Plan for goal: {{goal}}"
          - name: implement
            agent: implementer
            task_class: implement
            task: "Do this plan: {{plan}}"
        {textwrap.indent(bid_block, '    ')}
            verify:
              max_attempts: 1
              checks:
                - name: file-exists
                  command: python3 -c "import pathlib,sys; sys.exit(0 if pathlib.Path('out.txt').exists() else 1)"
              verifier: code-verifier
              criteria: out.txt exists
    """))


def _events(root, run_id):
    path = root / "runs" / run_id / "events.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


@bid_record_pending
def test_record_mode_bids_every_candidate_and_dispatches_the_table_route(
        tmp_path, monkeypatch):
    from harness.runner import WorkflowRunner
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, "bid:\n  mode: record\n  candidates: [local, mid]\n")
    runner = WorkflowRunner(project_root=tmp_path, run_id="bidrun", echo=False)
    local = MockModel(ModelSpec(name="local", provider="mock", model_id="mock-local"),
                      script=[turn_tool("task_complete",
                                        {"report": bid_report(premortem=CITED)})])
    mid = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock-mid"), script=[
        turn_tool("task_complete", {"report": "PLAN: write out.txt"}),
        turn_tool("task_complete", {"report": bid_report(premortem=CITED)}),   # bid
        turn_tool("accept_task", {"note": "ok"}),
        turn_tool("write_file", {"path": "out.txt", "content": "x"}),
        turn_tool("task_complete", {"report": "wrote out.txt"}),
        turn_tool("task_complete", {"report": '{"passed": true, "reasons": "exists"}'}),
    ])
    runner._models["local"] = local
    runner._models["mid"] = mid

    outcomes = runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")
    assert [o.status for o in outcomes] == ["passed", "passed"]

    events = _events(tmp_path, "bidrun")
    recorded = [e for e in events if e["kind"] == "bid_recorded"]
    assert sorted(e["tier"] for e in recorded) == ["local", "mid"]
    assert all(e["bid"] == "yes" for e in recorded)
    assert not [e for e in events if e["kind"] == "bid_selected"]
    worker_routes = [e for e in events
                     if e["kind"] == "routing_trace" and e["agent"] == "implementer"]
    assert worker_routes and all(e["tier"] == "mid" for e in worker_routes)
    # the local bidder was called exactly once, read-only, and never dispatched
    assert len(local.calls) == 1
    outcomes_ev = {e["tier"]: e for e in events if e["kind"] == "bid_outcome"}
    assert outcomes_ev["mid"]["dispatched"] is True
    assert outcomes_ev["local"]["dispatched"] is False


@bid_record_pending
def test_bidders_receive_anchors_and_no_side_effect_tools(tmp_path, monkeypatch):
    from harness.runner import WorkflowRunner
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    scaffold(tmp_path, "bid:\n  mode: record\n  candidates: [local]\n")
    runner = WorkflowRunner(project_root=tmp_path, run_id="bidrun2", echo=False)
    local = MockModel(ModelSpec(name="local", provider="mock", model_id="mock-local"),
                      script=[turn_tool("task_complete", {"report": bid_report(bid="no")})])
    mid = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock-mid"), script=[
        turn_tool("task_complete", {"report": "PLAN"}),
        turn_tool("accept_task", {"note": "ok"}),
        turn_tool("write_file", {"path": "out.txt", "content": "x"}),
        turn_tool("task_complete", {"report": "wrote"}),
        turn_tool("task_complete", {"report": '{"passed": true, "reasons": "ok"}'}),
    ])
    runner._models["local"] = local
    runner._models["mid"] = mid
    runner.run_workflow(tmp_path / "workflows" / "wf.yaml", goal="g")

    call = local.calls[0]
    assert "check:file-exists" in call["messages"][1].content
    assert "criterion:1" in call["messages"][1].content
    offered = {t["name"] for t in (call["tools"] or [])}
    assert not offered & {"write_file", "run_shell", "accept_task"}
