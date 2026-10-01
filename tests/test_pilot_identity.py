"""Offline contract tests for local Qwen identity receipts."""
from __future__ import annotations

import copy
import io
import json

import pytest
from urllib.error import HTTPError

from scripts.pilot_contract import PilotRefusal
import scripts.pilot_identity as pilot_identity
from scripts.pilot_identity import assert_same_identity, capture_identity

PARSER_VERSION = pilot_identity.EXPECTED_PARSER_VERSION


HASH = "a" * 64
FROM_A = "b" * 64
FROM_B = "c" * 64


def harness(**changes):
    value = {"provider": "openai-compat", "model_id": "qwen3.8:latest", "endpoint": "http://127.0.0.1:11434/v1",
             "prompt_sha256": HASH, "parser_version": PARSER_VERSION, "sampling": {"temperature": 0}}
    value.update(changes)
    return value


def fetcher(*, version="0.12.4", digest=HASH, models=None, show=None):
    tag_models = models if models is not None else [{"name": "qwen3.8:latest", "digest": "sha256:" + digest, "size": 27_300_000_000}]
    shown = show if show is not None else {"details": {"family": "qwen"}, "model_info": {"parameter_size": "27.3B"},
                                           "capabilities": ["completion"],
                                           "modelfile": 'FROM "/models/blobs/sha256-' + FROM_A + '"\nFROM sha256-' + FROM_B}
    def fetch(method, path, payload=None):
        if path == "/api/version": return {"version": version}
        if path == "/api/tags": return {"models": tag_models}
        assert method == "POST" and path == "/api/show" and payload == {"name": "qwen3.8:latest"}
        return shown
    return fetch


def receipt(**kwargs):
    return capture_identity(client_version="client-1", harness_identity=harness(), fetch_json=fetcher(**kwargs))


def test_receipt_pins_complete_sanitized_metadata_and_multiple_from_digests():
    result = receipt()
    assert result["model"]["digest"] == "sha256:" + HASH
    assert result["model"]["from_digests"] == ["sha256:" + FROM_A, "sha256:" + FROM_B]
    assert "modelfile" not in json.dumps(result)
    assert len(result["fingerprint"]) == 64


def test_bare_ollama_tag_digest_is_normalized_to_canonical_sha256_form():
    result = capture_identity(
        client_version="client-1", harness_identity=harness(),
        fetch_json=fetcher(models=[{"name": "qwen3.8:latest", "digest": HASH, "size": 27_300_000_000}]),
    )
    assert result["model"]["digest"] == "sha256:" + HASH


@pytest.mark.parametrize("change", [
    lambda: receipt(version="0.12.5"), lambda: receipt(digest="d" * 64),
    lambda: capture_identity(client_version="client-1", harness_identity=harness(prompt_sha256="d" * 64), fetch_json=fetcher()),
    lambda: capture_identity(client_version="client-1", harness_identity=harness(sampling={"temperature": 1}), fetch_json=fetcher()),
])
def test_identity_changes_are_drift(change):
    with pytest.raises(PilotRefusal, match="identity_drift"):
        assert_same_identity(receipt(), change())


def test_mutable_tag_with_same_name_and_different_hash_drifts():
    with pytest.raises(PilotRefusal, match="identity_drift"):
        assert_same_identity(receipt(), receipt(digest="d" * 64))


@pytest.mark.parametrize("models,show", [
    ([], None), ([{"name": "qwen3.8:latest", "digest": "sha256:" + HASH, "size": 1}] * 2, None),
    (None, {"details": {}, "model_info": {}, "capabilities": [], "modelfile": "FROM qwen:latest"}),
])
def test_missing_or_ambiguous_metadata_refuses(models, show):
    with pytest.raises(PilotRefusal):
        capture_identity(client_version="client-1", harness_identity=harness(), fetch_json=fetcher(models=models, show=show))


@pytest.mark.parametrize("change", [
    {"provider": "ollama"}, {"model_id": "some-other-tag"},
    {"endpoint": "http://127.0.0.1:11434"}, {"parser_version": "not-" + PARSER_VERSION},
    {"sampling": {"temperature": float("nan")}}, {"sampling": "temperature=0"},
])
def test_harness_identity_is_declared_and_bound_to_capture(change):
    with pytest.raises(PilotRefusal, match="invalid_harness_identity"):
        capture_identity(client_version="client-1", harness_identity=harness(**change), fetch_json=fetcher())


def test_every_from_directive_must_parse_even_if_another_is_valid():
    bad = {"details": {}, "model_info": {}, "capabilities": [],
           "modelfile": "FROM sha256-" + FROM_A + "\nFROM qwen:latest"}
    with pytest.raises(PilotRefusal, match="missing_model_metadata"):
        capture_identity(client_version="client-1", harness_identity=harness(), fetch_json=fetcher(show=bad))


def test_receipt_fingerprint_is_revalidated_before_comparison():
    forged = copy.deepcopy(receipt())
    forged["model"]["digest"] = "sha256:" + "d" * 64
    with pytest.raises(PilotRefusal, match="invalid_receipt"):
        assert_same_identity(receipt(), forged)


@pytest.mark.parametrize("base_url", ["https://127.0.0.1:11434", "http://example.com", "http://localhost:11434"])
def test_default_transport_rejects_nonloopback_before_network(base_url):
    with pytest.raises(PilotRefusal, match="invalid_base_url"):
        capture_identity(base_url=base_url, client_version="client-1", harness_identity=harness())


class _Response:
    def __init__(self, payload, length=None):
        self.payload = payload
        self.headers = {} if length is None else {"Content-Length": str(length)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit):
        return self.payload


def test_default_transport_only_uses_read_only_metadata_routes(monkeypatch):
    calls = []
    responses = iter([
        json.dumps({"version": "0.12.4"}).encode(),
        json.dumps({"models": [{"name": "qwen3.8:latest", "digest": "sha256:" + HASH, "size": 1}]}).encode(),
        json.dumps({"details": {}, "model_info": {}, "capabilities": [], "modelfile": "FROM sha256-" + FROM_A}).encode(),
    ])

    class Opener:
        def open(self, request, timeout):
            calls.append((request.get_method(), request.full_url, request.data, timeout))
            return _Response(next(responses))

    monkeypatch.setattr(pilot_identity, "build_opener", lambda *args: Opener())
    capture_identity(client_version="client-1", harness_identity=harness())
    assert [(method, url.rsplit(":11434", 1)[1]) for method, url, _, _ in calls] == [
        ("GET", "/api/version"), ("GET", "/api/tags"), ("POST", "/api/show"),
    ]
    assert all(timeout == 5.0 for _, _, _, timeout in calls)


@pytest.mark.parametrize("method,path", [("POST", "/api/version"), ("GET", "/api/show"), ("POST", "/api/tags")])
def test_default_transport_rejects_wrong_method_for_metadata_route(method, path):
    with pytest.raises(PilotRefusal, match="invalid_metadata_route"):
        pilot_identity._default_fetch_json("http://127.0.0.1:11434", method, path)


@pytest.mark.parametrize("payload,length", [(b"not json", None), (b"x" * 1_000_001, None), (b"{}", 1_000_001)])
def test_default_transport_refuses_malformed_or_huge_responses(monkeypatch, payload, length):
    class Opener:
        def open(self, request, timeout):
            return _Response(payload, length)
    monkeypatch.setattr(pilot_identity, "build_opener", lambda *args: Opener())
    with pytest.raises(PilotRefusal, match="invalid_metadata_response"):
        pilot_identity._default_fetch_json("http://127.0.0.1:11434", "GET", "/api/version")


def test_default_transport_refuses_redirects(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 302, "redirect", {}, io.BytesIO())
    monkeypatch.setattr(pilot_identity, "build_opener", lambda *args: Opener())
    with pytest.raises(PilotRefusal, match="metadata_unavailable"):
        pilot_identity._default_fetch_json("http://127.0.0.1:11434", "GET", "/api/version")
