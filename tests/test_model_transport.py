"""Provider HTTP transport: redirects are refused and reads are bounded.

Every test is offline. The urllib handler chain runs for real, but the lowest
http/https open is replaced by an in-process router, so no socket is opened.
Credentials are synthetic literals.
"""

import email.message
import io
import json
import urllib.request

import pytest

from harness.models.anthropic import AnthropicModel
from harness.models.base import ModelSpec
from harness.models.openai_compat import OpenAICompatModel
from harness.models.openai_responses import OpenAIResponsesModel

_KEY_ENV = "HARNESSIE_SYNTHETIC_TEST_KEY"
_SYNTHETIC = "synthetic-only"


class _WireResponse(io.BytesIO):
    """Just enough of http.client.HTTPResponse for urllib's handler chain."""

    def __init__(self, code, body=b"", headers=None, url=""):
        super().__init__(body)
        self.code = self.status = code
        self.msg = self.reason = "synthetic"
        self.url = url
        self.headers = email.message.Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def info(self):
        return self.headers

    def geturl(self):
        return self.url

    def getcode(self):
        return self.code


def _ok_body(cls):
    if cls is OpenAICompatModel:
        return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    if cls is AnthropicModel:
        return {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1}}
    return {"status": "completed", "output": [], "usage": {"input_tokens": 1,
                                                          "output_tokens": 1}}


@pytest.fixture
def wire(monkeypatch):
    """Route every urllib http(s) open through an in-process table."""
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                 "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)
    seen: list[tuple[str, dict]] = []
    routes: dict[str, object] = {}

    def _open(handler, req):
        seen.append((req.full_url, {k.lower(): v for k, v in req.header_items()}))
        route = routes.get(req.full_url)
        if route is None:
            return _WireResponse(599, b"unrouted", url=req.full_url)
        return route(req) if callable(route) else route

    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", _open)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", _open)
    return seen, routes


def _model(cls):
    if cls is AnthropicModel:
        return cls(ModelSpec(name="mid", provider="anthropic", model_id="t",
                             api_key_env=_KEY_ENV, supports_effort=False))
    provider = "openai-compat" if cls is OpenAICompatModel else "openai-responses"
    return cls(ModelSpec(name="mid", provider=provider, model_id="t",
                         base_url="https://origin.invalid/v1", api_key_env=_KEY_ENV,
                         supports_effort=False))


def _endpoint(cls):
    if cls is AnthropicModel:
        return "https://api.anthropic.com/v1/messages"
    if cls is OpenAICompatModel:
        return "https://origin.invalid/v1/chat/completions"
    return "https://origin.invalid/v1/responses"


ADAPTERS = [OpenAICompatModel, AnthropicModel, OpenAIResponsesModel]
REDIRECTS = [301, 302, 303, 307, 308]


def _targets(origin):
    scheme, rest = origin.split("://", 1)
    host = rest.split("/", 1)[0]
    return {
        "cross_origin": "https://other.invalid/collect",
        "https_downgrade": f"http://{host}/collect",
        "same_origin": f"{scheme}://{host}/v1/elsewhere",
    }


@pytest.mark.parametrize("cls", ADAPTERS)
@pytest.mark.parametrize("code", REDIRECTS)
@pytest.mark.parametrize("target", ["cross_origin", "https_downgrade", "same_origin"])
def test_adapter_never_follows_a_redirect(monkeypatch, wire, cls, code, target):
    seen, routes = wire
    monkeypatch.setenv(_KEY_ENV, _SYNTHETIC)
    origin = _endpoint(cls)
    location = _targets(origin)[target]
    routes[origin] = _WireResponse(code, b"moved", {"Location": location}, origin)
    routes[location] = _WireResponse(200, json.dumps(_ok_body(cls)).encode(),
                                     url=location)

    turn = _model(cls).complete([])

    assert [url for url, _ in seen] == [origin]
    assert turn.stop_reason == "error"
    assert turn.tool_calls == []


@pytest.mark.parametrize("cls", ADAPTERS)
def test_adapter_sends_credentials_only_to_configured_origin(monkeypatch, wire, cls):
    seen, routes = wire
    monkeypatch.setenv(_KEY_ENV, _SYNTHETIC)
    origin = _endpoint(cls)
    routes[origin] = _WireResponse(200, json.dumps(_ok_body(cls)).encode(), url=origin)

    turn = _model(cls).complete([])

    assert turn.stop_reason == "end_turn"
    assert len(seen) == 1
    url, headers = seen[0]
    assert url == origin
    assert _SYNTHETIC in (headers.get("authorization", "") + headers.get("x-api-key", ""))


@pytest.mark.parametrize("code", REDIRECTS)
@pytest.mark.parametrize("header", ["Authorization", "x-api-key", "api-key"])
def test_transport_refuses_redirect_for_custom_credential_headers(wire, code, header):
    seen, routes = wire
    origin = "https://origin.invalid/v1/x"
    routes[origin] = _WireResponse(code, b"", {"Location": "https://other.invalid/"},
                                   origin)
    req = urllib.request.Request(origin, data=b"{}", headers={header: _SYNTHETIC})

    reply = _tx().post(req)

    assert not reply.ok
    assert reply.failure == "redirect_refused"
    assert reply.code == code
    assert [url for url, _ in seen] == [origin]


def _tx():
    """Imported late so the redirect tests above stay meaningful on code
    that predates the shared transport module."""
    import importlib
    return importlib.import_module("harness.models._transport")


class _Trickle:
    """Fake response: yields scripted chunks and advances a fake clock."""

    def __init__(self, chunks, clock=None, step=0.0, headers=None):
        self.chunks = list(chunks)
        self.clock = clock
        self.step = step
        self.headers = email.message.Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value
        self.sizes: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def close(self):
        pass

    def read(self, n=-1):
        self.sizes.append(n)
        if self.clock is not None:
            self.clock.now += self.step
        if not self.chunks:
            return b""
        chunk = self.chunks.pop(0)
        if n is not None and n >= 0 and len(chunk) > n:
            self.chunks.insert(0, chunk[n:])
            chunk = chunk[:n]
        return chunk


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _post(response, **kwargs):
    req = urllib.request.Request("https://origin.invalid/v1/x", data=b"{}")
    return _tx().post(req, opener=_FixedOpener(response), **kwargs)


class _FixedOpener:
    def __init__(self, response):
        self.response = response

    def open(self, req, timeout=None):
        return self.response


def test_body_at_exact_limit_is_accepted():
    reply = _post(_Trickle([b"a" * 10]), max_bytes=10)
    assert reply.ok
    assert reply.body == b"a" * 10


def test_body_one_byte_over_limit_is_refused_without_reading_further():
    response = _Trickle([b"a" * 11, b"b" * 1000])
    reply = _post(response, max_bytes=10)
    assert not reply.ok
    assert reply.failure == "response_too_large"
    assert reply.usage_known is False
    assert all(0 <= n <= 11 for n in response.sizes)
    assert response.chunks == [b"b" * 1000]


def test_declared_content_length_over_limit_refuses_before_reading():
    response = _Trickle([b"a"], headers={"Content-Length": "11"})
    reply = _post(response, max_bytes=10)
    assert reply.failure == "response_too_large"
    assert response.sizes == []


def test_false_small_content_length_still_bounded():
    response = _Trickle([b"a" * 4] * 10, headers={"Content-Length": "2"})
    reply = _post(response, max_bytes=10)
    assert reply.failure == "response_too_large"
    assert sum(min(n, 4) for n in response.sizes) <= 12


def test_body_shorter_than_content_length_is_incomplete():
    # A clean close before the declared length is a truncated reply, not a
    # complete one: the usage it reports cannot be trusted.
    response = _Trickle([b'{"ok": true}'], headers={"Content-Length": "512"})
    reply = _post(response, max_bytes=10_000)
    assert not reply.ok
    assert reply.failure == "incomplete_response"
    assert reply.usage_known is False


def test_body_matching_content_length_is_accepted_control():
    body = b'{"ok": true}'
    response = _Trickle([body], headers={"Content-Length": str(len(body))})
    reply = _post(response, max_bytes=10_000)
    assert reply.ok
    assert reply.body == body


def test_slow_trickle_hits_whole_call_deadline():
    clock = _Clock()
    response = _Trickle([b"a"] * 1000, clock=clock, step=1.0)
    reply = _post(response, max_bytes=10_000, deadline_s=5.0, clock=clock)
    assert not reply.ok
    assert reply.failure == "deadline_exceeded"
    assert reply.usage_known is False
    assert len(response.sizes) <= 6


def test_fast_body_inside_deadline_is_accepted():
    clock = _Clock()
    response = _Trickle([b"ab", b"cd"], clock=clock, step=0.5)
    reply = _post(response, max_bytes=100, deadline_s=5.0, clock=clock)
    assert reply.ok
    assert reply.body == b"abcd"


def test_error_body_read_is_bounded(wire):
    seen, routes = wire
    origin = "https://origin.invalid/v1/x"
    body = b"e" * (_tx().MAX_ERROR_BYTES * 4)
    routes[origin] = _WireResponse(500, body, url=origin)
    reply = _tx().post(urllib.request.Request(origin, data=b"{}"))
    assert reply.failure == "http_error"
    assert reply.code == 500
    assert reply.usage_known is True
    assert len(reply.detail) <= 500


@pytest.mark.parametrize("cls", ADAPTERS)
def test_adapter_oversize_success_body_is_error_with_unknown_usage(monkeypatch, cls):
    big = b" " * 64 + json.dumps(_ok_body(cls)).encode()
    monkeypatch.setattr(_tx(), "MAX_RESPONSE_BYTES", 32)
    monkeypatch.setattr(_tx(), "_open",
                        lambda req, timeout=None: _Trickle([big]))
    turn = _model(cls).complete([])
    assert turn.stop_reason == "error"
    assert turn.usage_known is False
    assert turn.tool_calls == []
