"""Shared HTTP transport for the provider adapters.

Three guarantees every adapter inherits:
  - redirects are refused, never followed: a credentialed POST cannot move to
    another origin, scheme or path (the pilot no-redirect design);
  - success and error bodies are read in chunks under a byte ceiling, with an
    overflow sentinel byte, so an oversized or lying Content-Length body is
    refused instead of buffered;
  - one deadline bounds the whole call: connect, send, status line, headers,
    chunk-size lines and body. A per-call watchdog shuts the connection's
    socket down when the deadline passes, so a trickle at any stage of the
    exchange cannot hold a run open past it; per-read socket timeouts are
    also tightened to the remaining budget between body chunks. The watchdog
    is cancelled before post() returns and can never act on a later call.

Usage accounting follows what the provider could have billed. A failure
before any request byte was sent (DNS, connection refused) is a known-zero,
retryable network error. Once the request has been sent, any failure that
leaves the response unread (reset, disconnect, header-wait timeout, the
deadline, an oversized or truncated body) means the provider may have
generated and billed output this harness cannot read, so usage is unknown.
"""

from __future__ import annotations

import http.client
import socket
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .base import AssistantTurn

MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024
CALL_DEADLINE_S = 600.0
# Largest usage counter accepted from a provider: far above any real call. A
# larger value is a malformed receipt (error turn, usage unknown), so a
# provider-controlled integer can never overflow float accounting.
MAX_USAGE_COUNT = 10**12
_CHUNK = 64 * 1024
_CALL_ATTR = "_harnessie_call"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _shutdown(sock) -> None:
    # The base-class method acts on the descriptor directly, so a TLS socket
    # blocked in a read wakes without its SSL state being torn down mid-read.
    try:
        socket.socket.shutdown(sock, socket.SHUT_RDWR)
    except (OSError, TypeError, ValueError):
        pass


class _Call:
    """Per-call deadline watchdog and request-sent tracker."""

    def __init__(self, deadline_s: float) -> None:
        self._lock = threading.Lock()
        self._socks: list = []
        self._done = False
        self.fired = False
        self.tracked = False   # a connection was made through _tracked
        self.sent = False      # a request byte was handed to the socket
        self._timer = threading.Timer(max(deadline_s, 0.0), self._fire)
        self._timer.daemon = True

    def start(self) -> None:
        self._timer.start()

    def register(self, sock) -> None:
        with self._lock:
            if self._done:
                return
            self._socks.append(sock)
            if self.fired:
                _shutdown(sock)

    def _fire(self) -> None:
        with self._lock:
            if self._done:
                return
            self.fired = True
            for sock in self._socks:
                _shutdown(sock)

    def finish(self) -> None:
        """After this returns the watchdog can never fire or touch a socket."""
        with self._lock:
            self._done = True
            self._socks.clear()
        self._timer.cancel()

    def timer_alive(self) -> bool:
        return self._timer.is_alive()


def _tracked(http_class, call: _Call):
    class _Tracked(http_class):
        def connect(self):
            call.tracked = True
            super().connect()
            call.register(self.sock)

        def send(self, data):
            if self.sock is None and self.auto_open:
                self.connect()
            call.sent = True
            super().send(data)

    return _Tracked


def _connection_class(http_class, req):
    call = getattr(req, _CALL_ATTR, None)
    return http_class if call is None else _tracked(http_class, call)


class _CallHTTPHandler(urllib.request.HTTPHandler):
    def do_open(self, http_class, req, **kwargs):
        return super().do_open(_connection_class(http_class, req), req, **kwargs)


class _CallHTTPSHandler(urllib.request.HTTPSHandler):
    def do_open(self, http_class, req, **kwargs):
        return super().do_open(_connection_class(http_class, req), req, **kwargs)


def build_opener(*handlers) -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect(), _CallHTTPHandler(),
                                       _CallHTTPSHandler(), *handlers)


_OPENER = build_opener()
_clock = time.monotonic


def _open(req: urllib.request.Request, timeout: float | None = None):
    return _OPENER.open(req, timeout=timeout)


class _Overflow(Exception):
    pass


class _Deadline(Exception):
    pass


@dataclass(frozen=True)
class Reply:
    ok: bool
    body: bytes = b""
    failure: str = ""   # redirect_refused | http_error | network_error |
                        # response_too_large | deadline_exceeded | incomplete_response
    code: int | None = None
    detail: str = ""
    usage_known: bool = True

    def error_turn(self) -> AssistantTurn:
        if self.failure == "redirect_refused":
            content = f"provider_error {self.code}: redirect refused"
        elif self.failure == "http_error":
            content = f"provider_error {self.code}: {self.detail}"
        elif self.failure == "network_error":
            content = f"network_error: {self.detail}"
        else:
            content = f"provider_response_error: {self.failure}"
        return AssistantTurn(content=content, stop_reason="error",
                             raw=self.detail if self.failure == "http_error" else None,
                             usage_known=self.usage_known)


def post(req: urllib.request.Request, *, opener=None, clock=None,
         max_bytes: int | None = None, deadline_s: float | None = None) -> Reply:
    clock = clock or _clock
    max_bytes = MAX_RESPONSE_BYTES if max_bytes is None else max_bytes
    deadline_s = CALL_DEADLINE_S if deadline_s is None else deadline_s
    deadline = clock() + deadline_s
    open_ = opener.open if opener is not None else _open
    call = _Call(deadline_s)
    setattr(req, _CALL_ATTR, call)
    call.start()
    try:
        reply = _exchange(req, open_, call, deadline, deadline_s, clock, max_bytes)
    finally:
        call.finish()
        try:
            delattr(req, _CALL_ATTR)
        except AttributeError:
            pass
    expired = call.fired or clock() > deadline
    if expired and reply.failure not in {"redirect_refused", "http_error"}:
        # Whatever the cut read reported (EOF, reset, a parse error, a socket
        # timeout racing the watchdog), the deadline ended it, and a body that
        # "completed" may be truncated. Only a failure before any request
        # byte left keeps usage known.
        return Reply(False, failure="deadline_exceeded",
                     usage_known=not reply.ok and reply.usage_known)
    return reply


def _exchange(req, open_, call: _Call, deadline: float, deadline_s: float, clock,
              max_bytes: int) -> Reply:
    try:
        resp = open_(req, timeout=deadline_s)
    except urllib.error.HTTPError as e:
        try:
            detail = _read(e, MAX_ERROR_BYTES, deadline, clock, truncate=True)
        except (_Deadline, _Overflow, http.client.HTTPException, OSError):
            detail = b""
        finally:
            e.close()
        if 300 <= e.code < 400:
            return Reply(False, failure="redirect_refused", code=e.code)
        return Reply(False, failure="http_error", code=e.code,
                     detail=detail.decode(errors="replace")[:500])
    except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
        # The tracked connection records whether a request byte left. For an
        # opener that bypasses it, urllib's own split is the fallback: connect
        # and send failures arrive wrapped in URLError, status and header
        # failures arrive raw.
        sent = call.sent if call.tracked else not isinstance(e, urllib.error.URLError)
        return Reply(False, failure="network_error", detail=str(e)[:500],
                     usage_known=not sent)
    try:
        with resp:
            declared = _content_length(resp)
            if declared is not None and declared > max_bytes:
                raise _Overflow
            body = _read(resp, max_bytes, deadline, clock)
            # read1 returns b"" on a clean close without raising, so a reply
            # cut short of its declared length must be caught here.
            if declared is not None and len(body) != declared:
                return Reply(False, failure="incomplete_response",
                             usage_known=False)
    except _Overflow:
        return Reply(False, failure="response_too_large", usage_known=False)
    except (_Deadline, TimeoutError):
        return Reply(False, failure="deadline_exceeded", usage_known=False)
    except (http.client.HTTPException, OSError):
        return Reply(False, failure="incomplete_response", usage_known=False)
    return Reply(True, body=body)


def _content_length(resp) -> int | None:
    headers = getattr(resp, "headers", None)
    raw = headers.get("Content-Length") if headers is not None else None
    try:
        value = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return value if value is not None and value >= 0 else None


def _read(resp, limit: int, deadline: float, clock, truncate: bool = False) -> bytes:
    # read1 returns after at most one underlying recv, so the deadline is
    # checked between network reads rather than after a full buffer fills.
    read = getattr(resp, "read1", None) or resp.read
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise _Deadline
        _tighten(resp, remaining)
        chunk = read(min(_CHUNK, limit + 1 - total))
        if clock() > deadline:
            raise _Deadline
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        chunks.append(chunk)
        if total > limit:
            if truncate:
                return b"".join(chunks)[:limit]
            raise _Overflow


def _tighten(resp, remaining: float) -> None:
    """Best effort: cap the next socket wait at the remaining deadline. When
    the socket is not reachable the bound is the deadline plus one wait."""
    sock = getattr(getattr(getattr(resp, "fp", None), "raw", None), "_sock", None)
    settimeout = getattr(sock, "settimeout", None)
    if callable(settimeout):
        try:
            settimeout(max(remaining, 0.001))
        except OSError:
            pass


@dataclass(frozen=True)
class Usage:
    """Provider usage receipt. `known` is True only when every counter was
    reported as an integer in [0, MAX_USAGE_COUNT]; reported counters survive
    a partial or malformed receipt so accounting keeps what the provider did
    say. An out-of-range counter is malformed and is never kept."""

    input_tokens: int = 0
    output_tokens: int = 0
    known: bool = False
    malformed: bool = False


def parse_usage(data, input_field: str, output_field: str) -> Usage:
    raw = data.get("usage") if isinstance(data, dict) else None
    if raw is None:
        return Usage()
    if not isinstance(raw, dict):
        return Usage(malformed=True)
    counts: list[int] = []
    known, malformed = True, False
    for name in (input_field, output_field):
        value = raw.get(name)
        if value is None:
            known = False
            counts.append(0)
        elif (isinstance(value, bool) or not isinstance(value, int)
              or not 0 <= value <= MAX_USAGE_COUNT):
            known, malformed = False, True
            counts.append(0)
        else:
            counts.append(value)
    return Usage(counts[0], counts[1], known, malformed)


def malformed_turn(label: str, exc: BaseException, usage: Usage) -> AssistantTurn:
    return AssistantTurn(
        content=f"provider_response_error: malformed {label} response "
                f"({type(exc).__name__})",
        stop_reason="error", input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens, usage_known=usage.known)
