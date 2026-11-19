"""SEC-20261118-004: concurrent conversations on one openai-responses tier
must never share replay state. Offline: the transport is a fake opener, no
socket is opened, and every marker is synthetic."""

import io
import json
import textwrap
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from harness.models import Message, ModelSpec, OpenAIResponsesModel
from harness.models.base import MockModel
from harness.routing import Route
from harness.runner import WorkflowRunner

WAIT = 10


class _Response:
    status = 200
    code = 200

    def __init__(self, payload: dict) -> None:
        self._body = io.BytesIO(json.dumps(payload).encode())
        self.headers = {"content-type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return self._body.read(*args)

    def getcode(self):
        return 200

    def info(self):
        return self.headers

    def geturl(self):
        return "https://origin.invalid/responses"

    def close(self):
        pass


def _payload(output: list[dict]) -> dict:
    return {"status": "completed", "output": output,
            "usage": {"input_tokens": 1, "output_tokens": 1}}


def _text(label: str) -> dict:
    return _payload([{"type": "message", "role": "assistant",
                      "content": [{"type": "output_text", "text": label}]}])


def _call(name: str, call_id: str, args: dict) -> dict:
    return _payload([{"type": "function_call", "name": name,
                      "call_id": call_id, "arguments": json.dumps(args)}])


def _body(request) -> dict:
    data = request.data if hasattr(request, "data") else request
    return json.loads(data)


def _spec() -> ModelSpec:
    return ModelSpec(name="mid", provider="openai-responses",
                     model_id="synthetic", base_url="https://origin.invalid")


# -- runner: each loop owns its adapter ------------------------------------------

def _scaffold(root):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "verifiers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "alpha.md").write_text("# Alpha\nSYS_ALPHA_ONLY")
    (root / "agents" / "workers" / "beta.md").write_text("# Beta\nSYS_BETA_ONLY")
    (root / "config").mkdir()
    (root / "config" / "models.yaml").write_text(textwrap.dedent("""
        tiers:
          mid:
            provider: openai-responses
            model_id: synthetic
            base_url: https://origin.invalid
        routing:
          default: { tier: mid, effort: medium }
        budget:
          max_usd: 5.0
          max_tokens: 100000
    """))
    (root / "workflows").mkdir()
    (root / "workflows" / "par.yaml").write_text(textwrap.dedent("""
        name: par
        phases:
          - name: left
            parallel: workers
            agent: alpha
            consent: false
            task: "PRIV_ALPHA_INPUT {goal}"
            verify: { max_attempts: 1 }
          - name: right
            parallel: workers
            agent: beta
            consent: false
            task: "PRIV_BETA_INPUT {goal}"
            verify: { max_attempts: 1 }
    """))


def test_each_loop_gets_its_own_responses_adapter(tmp_path):
    _scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="iso", echo=False)
    route = Route("mid", "medium")
    first = runner._loop_for("worker", route)
    second = runner._loop_for("worker", route)
    assert isinstance(first.model, OpenAIResponsesModel)
    assert first.model is not second.model


def test_injected_test_model_is_still_shared(tmp_path):
    _scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="inject", echo=False)
    brain = MockModel(ModelSpec(name="mid", provider="mock", model_id="mock"))
    runner._models["mid"] = brain
    route = Route("mid", "medium")
    assert runner._loop_for("worker", route).model is brain
    assert runner._loop_for("worker", route).model is brain


def test_parallel_same_tier_conversations_never_cross(tmp_path):
    """Delayed first response for alpha lands after beta's first turn has
    committed; beta's follow-up tool turn then starts. Every request must
    carry only its own conversation's input, output and instructions."""
    _scaffold(tmp_path)
    runner = WorkflowRunner(project_root=tmp_path, run_id="race", echo=False)

    lock = threading.Lock()
    bodies: list[tuple[str, dict]] = []
    per_thread: dict[int, list[str]] = {}
    alpha_in_flight = threading.Event()
    beta_first_done = threading.Event()
    alpha_first_done = threading.Event()
    counts = {"alpha": 0, "beta": 0}
    original = OpenAIResponsesModel.complete

    def conv_of(messages) -> str:
        return "alpha" if "PRIV_ALPHA_INPUT" in messages[1].content else "beta"

    def gated_complete(self, messages, tools=None, effort="medium"):
        conv = conv_of(messages)
        with lock:
            counts[conv] += 1
            n = counts[conv]
        if conv == "beta" and n == 1:
            assert alpha_in_flight.wait(WAIT), "fixture deadline"
        if conv == "beta" and n == 2:
            assert alpha_first_done.wait(WAIT), "fixture deadline"
        turn = original(self, messages, tools, effort)
        if conv == "alpha" and n == 1:
            alpha_first_done.set()
        if conv == "beta" and n == 1:
            beta_first_done.set()
        return turn

    def fake_open(self, request, data=None, timeout=None):
        body = _body(request)
        ident = threading.get_ident()
        with lock:
            history = per_thread.setdefault(ident, [])
            if not history:
                text = json.dumps(body)
                history.append("alpha" if "PRIV_ALPHA_INPUT" in text else "beta")
            conv = history[0]
            history.append("call")
            n = len(history) - 1
            bodies.append((conv, body))
        if conv == "alpha" and n == 1:
            alpha_in_flight.set()
            assert beta_first_done.wait(WAIT), "fixture deadline"
        if n == 1:
            return _Response(_call("list_files", f"{conv}-1", {}))
        return _Response(_call("task_complete", f"{conv}-2",
                               {"report": f"REPORT_{conv.upper()}"}))

    with patch.object(OpenAIResponsesModel, "complete", gated_complete), \
            patch.object(urllib.request.OpenerDirector, "open", fake_open):
        outcomes = runner.run_workflow(tmp_path / "workflows" / "par.yaml",
                                       goal="g")

    assert sorted(o.phase for o in outcomes) == ["left", "right"]
    assert counts["alpha"] >= 2 and counts["beta"] >= 2
    other = {"alpha": "beta", "beta": "alpha"}
    for conv, body in bodies:
        text = json.dumps(body)
        foreign = other[conv]
        assert f"PRIV_{foreign.upper()}_INPUT" not in text
        assert f"REPORT_{foreign.upper()}" not in text
        assert f"{foreign}-1" not in text
        assert f"PRIV_{conv.upper()}_INPUT" in text
        assert f"SYS_{conv.upper()}_ONLY" in body.get("instructions", "")
        assert f"SYS_{foreign.upper()}_ONLY" not in body.get("instructions", "")


# -- adapter: a shared object still never commits a foreign history -----------

def test_shared_adapter_interleaving_never_leaks_foreign_history():
    model = OpenAIResponsesModel(_spec())
    a = [Message("system", "SYS_A"), Message("user", "PRIV_A")]
    b = [Message("system", "SYS_B"), Message("user", "PRIV_B")]
    a_entered = threading.Event()
    b_finished = threading.Event()
    calls: list[dict] = []
    lock = threading.Lock()

    def fake_open(self, request, data=None, timeout=None):
        body = _body(request)
        with lock:
            calls.append(body)
            index = len(calls)
        if index == 1:
            a_entered.set()
            assert b_finished.wait(WAIT), "fixture deadline"
        return _Response(_text(f"OUT_{index}"))

    def run_b():
        try:
            return model.complete(b)
        finally:
            b_finished.set()

    with patch.object(urllib.request.OpenerDirector, "open", fake_open):
        with ThreadPoolExecutor(max_workers=2) as pool:
            fa = pool.submit(model.complete, a)
            assert a_entered.wait(WAIT), "fixture deadline"
            fb = pool.submit(run_b)
            fa.result(timeout=WAIT)
            fb.result(timeout=WAIT)
        b.append(Message("user", "B_FOLLOWUP"))
        model.complete(b)

    followup = json.dumps(calls[2])
    assert "PRIV_A" not in followup
    assert "OUT_1" not in followup
    assert "PRIV_B" in followup and "B_FOLLOWUP" in followup
    assert calls[2]["instructions"] == "SYS_B"


def test_for_conversation_starts_clean_and_keeps_spec():
    model = OpenAIResponsesModel(_spec())
    a = [Message("system", "SYS_A"), Message("user", "PRIV_A")]
    calls: list[dict] = []

    def fake_open(self, request, data=None, timeout=None):
        calls.append(_body(request))
        return _Response(_text("OUT_A"))

    with patch.object(urllib.request.OpenerDirector, "open", fake_open):
        model.complete(a)
        fresh = model.for_conversation()
        assert fresh is not model
        assert fresh.spec == model.spec
        fresh.complete([Message("system", "SYS_C"), Message("user", "PRIV_C")])
    second = json.dumps(calls[1])
    assert "PRIV_A" not in second and "OUT_A" not in second
    assert calls[1]["instructions"] == "SYS_C"


def test_failed_turn_commits_no_replay_state():
    model = OpenAIResponsesModel(_spec())
    conv = [Message("system", "SYS_A"), Message("user", "PRIV_A")]
    calls: list[dict] = []

    def fake_open(self, request, data=None, timeout=None):
        calls.append(_body(request))
        if len(calls) == 1:
            return _Response({"status": "completed", "output": "not-a-list"})
        return _Response(_text("OUT_OK"))

    with patch.object(urllib.request.OpenerDirector, "open", fake_open):
        bad = model.complete(conv)
        assert bad.stop_reason == "error"
        conv.append(Message("user", "RETRY"))
        model.complete(conv)
    retry = calls[1]
    users = [item for item in retry["input"] if item.get("role") == "user"]
    assert [item["content"] for item in users] == ["PRIV_A", "RETRY"]
