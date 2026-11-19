"""The whole-call deadline bounds header and chunk-line parsing, and a
connection failure after the request was sent is usage-unknown.

Offline: every server is an in-process 127.0.0.1 IP-literal loopback socket,
proxies are disabled on the opener and in the environment, and no DNS lookup
is made. Deadlines are short so the suite stays fast.
"""

import json
import socket
import struct
import threading
import time
import urllib.request

import pytest

from harness.events import EventLog
from harness.loop import AgentLoop
from harness.models import _transport
from harness.models.base import ModelSpec
from harness.models.openai_compat import OpenAICompatModel
from harness.routing import Budget
from harness.tools.registry import ToolRegistry

_OK = json.dumps({"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()
DEADLINE = 0.5
SLACK = 0.75   # scheduling slack; the trickles below run for 3 seconds


@pytest.fixture(autouse=True)
def _no_proxy_env(monkeypatch):
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                 "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(_transport, "_OPENER", _opener())


def _opener():
    return _transport.build_opener(urllib.request.ProxyHandler({}))


class _Server:
    """One-connection-at-a-time loopback server running `script(conn, stop)`."""

    def __init__(self, script):
        self.script = script
        self.stop = threading.Event()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.connections = 0
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.stop.is_set():
            try:
                conn, _ = self.listener.accept()
            except (TimeoutError, OSError):
                continue
            self.connections += 1
            try:
                _read_request(conn)
                self.script(conn, self.stop)
            except OSError:
                pass
            finally:
                conn.close()

    def url(self, path="/v1/x"):
        return f"http://127.0.0.1:{self.port}{path}"

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        self.listener.close()


@pytest.fixture
def serve():
    servers = []

    def _start(script):
        server = _Server(script)
        servers.append(server)
        return server

    yield _start
    for server in servers:
        server.close()


def _read_request(conn):
    conn.settimeout(2.0)
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            return
        data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    length = 0
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            length = int(value.strip())
    while len(body) < length:
        chunk = conn.recv(4096)
        if not chunk:
            return
        body += chunk


def _trickle(conn, stop, prefix, unit, interval=0.1, seconds=3.0):
    conn.sendall(prefix)
    end = time.monotonic() + seconds
    while not stop.is_set() and time.monotonic() < end:
        conn.sendall(unit)
        time.sleep(interval)


def _post(url, deadline_s=DEADLINE):
    req = urllib.request.Request(url, data=b"{}",
                                 headers={"content-type": "application/json"})
    started = time.monotonic()
    reply = _transport.post(req, opener=_opener(), deadline_s=deadline_s)
    return reply, time.monotonic() - started


# -- SEC-20261118-012: the deadline bounds status, header and chunk-line reads


@pytest.mark.parametrize("prefix,unit", [
    (b"", b"H"),                                   # status line trickle
    (b"HTTP/1.1 200 OK\r\nX-Slow: ", b"a"),        # header value trickle
    (b"HTTP/1.1 200 OK\r\n", b"X-H: v\r\n"),       # endless header lines
], ids=["status_line", "header_value", "header_lines"])
def test_header_trickle_is_bounded_by_whole_call_deadline(serve, prefix, unit):
    server = serve(lambda conn, stop: _trickle(conn, stop, prefix, unit))
    reply, elapsed = _post(server.url())
    assert not reply.ok
    assert reply.failure == "deadline_exceeded"
    assert reply.usage_known is False
    assert elapsed < DEADLINE + SLACK


def test_chunk_size_line_trickle_is_bounded_by_whole_call_deadline(serve):
    head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
    server = serve(lambda conn, stop: _trickle(conn, stop, head, b"0"))
    reply, elapsed = _post(server.url())
    assert not reply.ok
    assert reply.failure == "deadline_exceeded"
    assert reply.usage_known is False
    assert elapsed < DEADLINE + SLACK


def test_silent_server_after_send_is_bounded_and_usage_unknown(serve):
    server = serve(lambda conn, stop: stop.wait(3.0))
    reply, elapsed = _post(server.url())
    assert reply.failure == "deadline_exceeded"
    assert reply.usage_known is False
    assert elapsed < DEADLINE + SLACK


def test_slow_but_timely_response_is_accepted(serve):
    response = (b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(_OK)).encode()
                + b"\r\n\r\n" + _OK)

    def script(conn, stop):
        for i in range(0, len(response), 16):
            conn.sendall(response[i:i + 16])
            time.sleep(0.005)

    server = serve(script)
    reply, _ = _post(server.url(), deadline_s=5.0)
    assert reply.ok
    assert reply.body == _OK


def test_watchdog_never_fires_after_the_call_returns(serve, monkeypatch):
    calls = []

    class _Recording(_transport._Call):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            calls.append(self)

    monkeypatch.setattr(_transport, "_Call", _Recording)
    response = (b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(_OK)).encode()
                + b"\r\n\r\n" + _OK)
    server = serve(lambda conn, stop: conn.sendall(response))
    reply, _ = _post(server.url(), deadline_s=0.3)
    assert reply.ok
    time.sleep(0.5)
    assert len(calls) == 1
    assert calls[0].fired is False
    assert calls[0].timer_alive() is False


# -- SEC-20261118-011: post-send failures are usage-unknown, pre-send are not


def _close_without_response(conn, stop):
    pass


def _reset(conn, stop):
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))


@pytest.mark.parametrize("script", [_close_without_response, _reset],
                         ids=["remote_disconnected", "connection_reset"])
def test_failure_after_request_sent_is_usage_unknown(serve, script):
    server = serve(script)
    reply, _ = _post(server.url(), deadline_s=5.0)
    assert not reply.ok
    assert reply.failure == "network_error"
    assert reply.usage_known is False


def _refused_url():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return f"http://127.0.0.1:{port}/v1/x"


def test_connection_refused_before_send_is_known_zero():
    reply, _ = _post(_refused_url(), deadline_s=5.0)
    assert not reply.ok
    assert reply.failure == "network_error"
    assert reply.usage_known is True


def test_proxy_connect_failure_before_provider_request_is_known_zero(serve):
    server = serve(lambda conn, stop: conn.sendall(
        b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"))
    proxy = f"http://127.0.0.1:{server.port}"
    opener = _transport.build_opener(
        urllib.request.ProxyHandler({"https": proxy}))
    req = urllib.request.Request("https://127.0.0.1:9/v1/x", data=b"{}")

    reply = _transport.post(req, opener=opener, deadline_s=5.0)

    assert not reply.ok
    assert reply.failure == "network_error"
    assert reply.usage_known is True
    assert server.connections == 1


def _compat(base_url):
    return OpenAICompatModel(ModelSpec(
        name="mid", provider="openai-compat", model_id="t", base_url=base_url,
        supports_effort=False))


def _loop(tmp_path, model):
    return AgentLoop(role="worker", model=model, registry=ToolRegistry(),
                     events=EventLog(tmp_path / "run", echo=False),
                     budget=Budget(max_usd=10, max_tokens=10_000), max_steps=4)


def test_metered_loop_stops_rather_than_retrying_a_post_send_failure(serve, tmp_path):
    server = serve(_close_without_response)
    result = _loop(tmp_path, _compat(server.url("/v1"))).run("system", "task")
    assert result.stop == "budget"
    assert result.detail.get("accounting") == "unknown"
    assert server.connections == 1


def test_metered_loop_retries_a_pre_send_failure(tmp_path):
    base = _refused_url().rsplit("/", 1)[0]
    result = _loop(tmp_path, _compat(base)).run("system", "task")
    assert result.stop == "model_error"
