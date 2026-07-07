from pathlib import Path

from harness.events import EventLog
from harness.loop import LoopResult
from harness.memory import ProofStore
from harness.models.base import ModelSpec
from harness.routing import Budget, Route, Router
from harness import sandbox
from harness.verify import Check, VerificationGate, parse_verdict


def test_route_table_and_default():
    router = Router(tiers={"mid": ModelSpec("mid", "mock", "m")},
                    table={"plan": {"tier": "frontier", "effort": "high"}})
    assert router.route("plan") == Route("frontier", "high")
    assert router.route("unknown") == Route("mid", "medium")


def test_escalation_ladder_effort_then_tier_then_none():
    r = Route("cheap", "high")
    r = r.escalate()
    assert r == Route("cheap", "xhigh")        # effort bumps first
    r = r.escalate()
    assert r == Route("cheap", "max")
    r = r.escalate()
    assert r == Route("mid", "medium")         # then tier, effort resets
    top = Route("frontier", "max")
    assert top.escalate() is None              # ladder ends at human


def test_spec_fallback_to_most_capable():
    router = Router(tiers={"cheap": ModelSpec("cheap", "mock", "m")})
    try:
        router.spec_for(Route("frontier", "high"))
    except ValueError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("missing tier should fail early")


def test_budget_accounting():
    b = Budget(max_usd=0.01, max_tokens=10_000)
    spec = ModelSpec("x", "mock", "m", cost_per_mtok_in=5.0, cost_per_mtok_out=25.0)
    b.charge(spec, tokens_in=1000, tokens_out=200)
    assert round(b.spent_usd, 6) == round((1000 * 5 + 200 * 25) / 1e6, 6)
    assert b.exhausted   # 0.01 ceiling crossed


def test_child_budget_is_headroom_seeded_and_charges_through():
    spec = ModelSpec("x", "mock", "m", cost_per_mtok_in=5.0, cost_per_mtok_out=25.0)
    parent = Budget(max_usd=1.0, max_tokens=10_000)
    parent.add_spend(0.4, 4_000)

    child = parent.child()
    assert round(child.max_usd, 6) == 0.6          # remaining headroom, not the run ceiling
    assert child.max_tokens == 6_000
    assert child.spent_usd == 0.0

    child.charge(spec, tokens_in=1000, tokens_out=200)
    charged = (1000 * 5 + 200 * 25) / 1e6
    assert round(child.spent_usd, 6) == round(charged, 6)
    # the same charge landed on the parent live, no merge step needed
    assert round(parent.spent_usd, 6) == round(0.4 + charged, 6)
    assert parent.spent_tokens == 4_000 + 1200


def test_child_budget_sees_sibling_spend_via_parent_exhaustion():
    parent = Budget(max_usd=1.0, max_tokens=10_000)
    a = parent.child()
    b = parent.child()
    assert not a.exhausted and not b.exhausted
    # sibling a spends the run to its ceiling; b must stop even though b
    # itself has spent nothing (this was the 0.6 known-limit overshoot)
    a.add_spend(1.0, 0)
    assert parent.exhausted
    assert b.exhausted


def test_child_of_exhausted_budget_starts_exhausted():
    parent = Budget(max_usd=0.5, max_tokens=10_000)
    parent.add_spend(0.5, 0)
    child = parent.child()
    assert child.max_usd == 0.0
    assert child.exhausted


def test_parse_verdict_last_object_wins_and_fails_closed():
    ok = parse_verdict('All good.\n```json\n{"passed": true, "reasons": "fine"}\n```')
    assert ok.passed
    # prose-only verdicts fail closed: the contract demands a JSON object
    assert not parse_verdict("... after review, verdict: PASS").passed
    assert not parse_verdict("lgtm 👍").passed
    # a quoted example object earlier must not override the real final verdict
    example_then_fail = parse_verdict(
        'Rule: emit {"passed": true} only when done. '
        'greeting.txt is MISSING: {"passed": false, "reasons": "file missing"}')
    assert not example_then_fail.passed
    # scratch braces before a legitimate trailing verdict must not break parsing
    scratch_then_pass = parse_verdict(
        'notes {"step": 1} and pytest output {...} then '
        '{"passed": true, "reasons": "all criteria reproduced"}')
    assert scratch_then_pass.passed
    # string booleans: "true" tolerated, "false" and other junk fail closed
    assert parse_verdict('{"passed": "true", "reasons": "y"}').passed
    assert not parse_verdict('{"passed": "false", "reasons": "n"}').passed
    assert not parse_verdict('{"passed": 1, "reasons": "n"}').passed


def make_gate(tmp_path) -> VerificationGate:
    run_dir = tmp_path / "run"
    return VerificationGate(workspace=tmp_path, proofs=ProofStore(run_dir),
                            events=EventLog(run_dir, echo=False), max_attempts=3)


def ok_loop(report="did it"):
    return LoopResult(stop="complete", report=report, steps=1)


def test_gate_passes_on_green_checks_and_verifier(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "wrap",
                        lambda argv, workspace, allow_network=False: argv)
    gate = make_gate(tmp_path)
    res = gate.run(
        task="do the thing",
        attempt_fn=lambda t, r: ok_loop(),
        verify_fn=lambda rep: ok_loop('{"passed": true, "reasons": "checked"}'),
        checks=[Check(name="true", command="python3 -c pass")],
        route=Route("cheap", "low"))
    assert res.status == "passed" and res.attempts == 1
    assert (tmp_path / "run" / "proofs").exists()   # check output saved as proof


def test_gate_reformulates_and_escalates(tmp_path):
    gate = make_gate(tmp_path)
    seen: list[tuple[str, Route]] = []

    def attempt(task, route):
        seen.append((task, route))
        return ok_loop()

    res = gate.run(
        task="original task",
        attempt_fn=attempt,
        verify_fn=lambda rep: ok_loop('{"passed": false, "reasons": "bad output"}'),
        checks=[],
        route=Route("cheap", "low"))
    assert res.status == "needs_human"
    assert len(seen) == 3
    # attempt 2: same route, task reformulated with failure evidence
    assert seen[1][0] != "original task" and "FAILED" in seen[1][0]
    assert seen[1][1] == Route("cheap", "low")
    # attempt 3: escalated route
    assert seen[2][1] == Route("cheap", "medium")


def test_gate_deterministic_check_failure_blocks_verifier(tmp_path):
    gate = make_gate(tmp_path)
    verifier_ran = []
    res = gate.run(
        task="task",
        attempt_fn=lambda t, r: ok_loop(),
        verify_fn=lambda rep: (verifier_ran.append(1),
                               ok_loop('{"passed": true, "reasons": "y"}'))[1],
        checks=[Check(name="fail", command='python3 -c "raise SystemExit(1)"')],
        route=Route("cheap", "low"))
    assert res.status == "needs_human"
    assert not verifier_ran   # model verifier never wastes tokens on red checks
