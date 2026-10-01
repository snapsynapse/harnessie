"""Fail-closed, local-only identity receipts for the Qwen pilot.

This module reads Ollama metadata only.  It intentionally has no generation,
pull, or model-management route. ``harness_identity`` records declared client
configuration (sealed prompt hash, parser, and sampling); it is not evidence
that the serving process observed or applied those values.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from scripts.pilot_contract import PilotRefusal, QWEN_MODEL, RECEIPT_VERSION, digest_json
from harness.verify import PARSER_VERSION as EXPECTED_PARSER_VERSION

_MAX_RESPONSE_BYTES = 1_000_000
_TIMEOUT_S = 5.0
_DIGEST = re.compile(r"^(?:sha256:|sha256-)?([0-9a-fA-F]{64})$")
_FROM_LINE = re.compile(r"^\s*FROM(?:\s+|$)(.*)$", re.IGNORECASE)
_FROM_VALUE = re.compile(r'^(?:"([^"]+)"|\'([^\']+)\'|(\S+))(?:\s+#.*)?$')
_SAMPLING_KEY = re.compile(r"^[a-z][a-z0-9_-]*$")
_REQUIRED_HARNESS_FIELDS = (
    "provider", "model_id", "endpoint", "prompt_sha256", "parser_version", "sampling",
)


def _refuse(code: str) -> None:
    raise PilotRefusal(code)


def _loopback_base_url(base_url: str) -> str:
    if not isinstance(base_url, str):
        _refuse("invalid_base_url")
    parsed = urlparse(base_url)
    if (parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment):
        _refuse("invalid_base_url")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        _refuse("invalid_base_url")
    try:
        port = parsed.port
    except ValueError:
        _refuse("invalid_base_url")
    host = parsed.hostname.lower()
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc += f":{port}"
    return f"http://{netloc}"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _default_fetch_json(base_url: str, method: str, path: str, payload: object | None = None) -> dict:
    """Fetch one bounded JSON object from the validated local Ollama origin."""
    origin = _loopback_base_url(base_url)
    if (method, path) not in {
        ("GET", "/api/version"), ("GET", "/api/tags"), ("POST", "/api/show"),
    }:
        _refuse("invalid_metadata_route")
    url = urljoin(origin + "/", path.lstrip("/"))
    if urlparse(url).netloc != urlparse(origin).netloc:
        _refuse("invalid_base_url")
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=_TIMEOUT_S) as response:
            length = response.headers.get("Content-Length")
            if length is not None and (not length.isdigit() or int(length) > _MAX_RESPONSE_BYTES):
                _refuse("invalid_metadata_response")
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except PilotRefusal:
        raise
    except (HTTPError, URLError, OSError, ValueError):
        _refuse("metadata_unavailable")
    if len(raw) > _MAX_RESPONSE_BYTES:
        _refuse("invalid_metadata_response")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _refuse("invalid_metadata_response")
    if type(decoded) is not dict:
        _refuse("invalid_metadata_response")
    return decoded


def _full_digest(value: object) -> str:
    if not isinstance(value, str):
        _refuse("missing_model_metadata")
    match = _DIGEST.fullmatch(value)
    if not match:
        _refuse("missing_model_metadata")
    return "sha256:" + match.group(1).lower()


def _nonempty_string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _refuse("missing_model_metadata")
    return value


def _validate_sampling(value: object) -> dict:
    """Require finite, explicit declared sampling configuration."""
    if type(value) is not dict or not value:
        _refuse("invalid_harness_identity")
    normalized: dict[str, int | float] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not _SAMPLING_KEY.fullmatch(key):
            _refuse("invalid_harness_identity")
        if type(item) not in (int, float) or not math.isfinite(item):
            _refuse("invalid_harness_identity")
        normalized[key] = item
    return normalized


def _validate_harness_identity(value: object, *, model: str, base_url: str) -> dict:
    """Validate declared client configuration, never serving-side observations."""
    if type(value) is not dict or set(value) != set(_REQUIRED_HARNESS_FIELDS):
        _refuse("invalid_harness_identity")
    identity: dict[str, Any] = {}
    for key in _REQUIRED_HARNESS_FIELDS[:-1]:
        field = value[key]
        if not isinstance(field, str) or not field.strip():
            _refuse("invalid_harness_identity")
        identity[key] = field
    if not re.fullmatch(r"[0-9a-f]{64}", identity["prompt_sha256"]):
        _refuse("invalid_harness_identity")
    if identity["provider"] != "openai-compat" or identity["model_id"] != model:
        _refuse("invalid_harness_identity")
    if identity["endpoint"] != base_url + "/v1":
        _refuse("invalid_harness_identity")
    if identity["parser_version"] != EXPECTED_PARSER_VERSION:
        _refuse("invalid_harness_identity")
    identity["sampling"] = _validate_sampling(value["sampling"])
    return identity


def _from_digests(modelfile: object) -> list[str]:
    if not isinstance(modelfile, str):
        _refuse("missing_model_metadata")
    found: list[str] = []
    for line in modelfile.splitlines():
        directive = _FROM_LINE.match(line)
        if directive is None:
            continue
        match = _FROM_VALUE.fullmatch(directive.group(1))
        if match is None:
            _refuse("missing_model_metadata")
        path = next(part for part in match.groups() if part is not None)
        # Ollama may emit absolute blob paths such as /.../blobs/sha256-<hash>.
        leaf = path.rsplit("/", 1)[-1]
        found.append(_full_digest(leaf))
    if not found:
        _refuse("missing_model_metadata")
    return found


def _fingerprint_payload(receipt: dict) -> dict:
    return {key: receipt[key] for key in (
        "receipt_version", "client_version", "ollama_base_url", "server_version", "model", "harness_identity",
    )}


def _validate_receipt(receipt: object) -> dict:
    if type(receipt) is not dict or set(receipt) != {
        "receipt_version", "client_version", "ollama_base_url", "server_version", "model", "harness_identity", "fingerprint",
    }:
        _refuse("invalid_receipt")
    if receipt["receipt_version"] != RECEIPT_VERSION:
        _refuse("invalid_receipt")
    _nonempty_string(receipt["client_version"])
    base_url = _loopback_base_url(receipt["ollama_base_url"])
    _nonempty_string(receipt["server_version"])
    model = receipt["model"]
    if type(model) is not dict or set(model) != {
        "tag", "digest", "size", "details", "model_info", "capabilities", "from_digests",
    }:
        _refuse("invalid_receipt")
    _nonempty_string(model["tag"])
    _full_digest(model["digest"])
    if type(model["size"]) is not int or model["size"] <= 0:
        _refuse("invalid_receipt")
    if type(model["details"]) is not dict or type(model["model_info"]) is not dict or type(model["capabilities"]) is not list:
        _refuse("invalid_receipt")
    if type(model["from_digests"]) is not list or not model["from_digests"]:
        _refuse("invalid_receipt")
    for digest in model["from_digests"]:
        _full_digest(digest)
    _validate_harness_identity(receipt["harness_identity"], model=model["tag"], base_url=base_url)
    if not isinstance(receipt["fingerprint"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["fingerprint"]):
        _refuse("invalid_receipt")
    if digest_json(_fingerprint_payload(receipt)) != receipt["fingerprint"]:
        _refuse("invalid_receipt")
    return receipt


def capture_identity(*, base_url: str = "http://127.0.0.1:11434", model: str = QWEN_MODEL,
                     client_version: str, harness_identity: dict,
                     fetch_json: Callable[[str, str, object | None], dict] | None = None) -> dict:
    """Capture a local, metadata-only identity receipt for one exact model tag."""
    if not isinstance(model, str) or not model.strip() or not isinstance(client_version, str) or not client_version.strip():
        _refuse("invalid_capture_request")
    normalized_base_url = _loopback_base_url(base_url)
    identity = _validate_harness_identity(harness_identity, model=model, base_url=normalized_base_url)
    fetch = fetch_json or (lambda method, path, payload=None: _default_fetch_json(normalized_base_url, method, path, payload))
    version = fetch("GET", "/api/version", None)
    tags = fetch("GET", "/api/tags", None)
    if type(version) is not dict or type(tags) is not dict:
        _refuse("invalid_metadata_response")
    server_version = _nonempty_string(version.get("version"))
    models = tags.get("models")
    if type(models) is not list:
        _refuse("missing_model_metadata")
    matches = [entry for entry in models if type(entry) is dict and entry.get("name") == model]
    if len(matches) != 1:
        _refuse("ambiguous_model_tag")
    tag = matches[0]
    digest = _full_digest(tag.get("digest"))
    size = tag.get("size")
    if type(size) is not int or size <= 0:
        _refuse("missing_model_metadata")
    show = fetch("POST", "/api/show", {"name": model})
    if type(show) is not dict or type(show.get("details")) is not dict or type(show.get("model_info")) is not dict or type(show.get("capabilities")) is not list:
        _refuse("missing_model_metadata")
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "client_version": client_version,
        "ollama_base_url": normalized_base_url,
        "server_version": server_version,
        "model": {"tag": model, "digest": digest, "size": size, "details": show["details"],
                  "model_info": show["model_info"], "capabilities": show["capabilities"],
                  "from_digests": _from_digests(show.get("modelfile"))},
        "harness_identity": identity,
    }
    receipt["fingerprint"] = digest_json(_fingerprint_payload(receipt))
    return _validate_receipt(receipt)


def assert_same_identity(before: dict, after: dict) -> None:
    """Reject forged or changed receipts; supplied digest fields are never trusted alone."""
    before_valid = _validate_receipt(before)
    after_valid = _validate_receipt(after)
    if before_valid["fingerprint"] != after_valid["fingerprint"]:
        _refuse("identity_drift")
