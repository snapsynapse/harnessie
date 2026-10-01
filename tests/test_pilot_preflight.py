from pathlib import Path
import json
import sys
import pytest

from scripts.pilot_contract import PilotRefusal, QWEN_MODEL
from scripts.pilot_claude_code import AUTH_CONTRACT_ID, ClaudeCodePilot, _RunResult
from scripts.pilot_preflight import claude_metadata, local_qwen_identity
from harness.verify import PARSER_VERSION


def test_current_oauth_metadata_is_route_evidence_not_billing_proof(monkeypatch):
    calls = []
    def fake_run(self, argv, stdin):
        calls.append(argv[1:])
        if argv[1:] == ["--version"]:
            return _RunResult(b"2.1.261 (Claude Code)\n", 0, None)
        return _RunResult(json.dumps({"loggedIn": True, "authMethod": "oauth_token",
                                     "apiProvider": "firstParty"}).encode(), 0, None)
    monkeypatch.setattr(ClaudeCodePilot, "_run", fake_run)
    value = claude_metadata(Path(sys.executable))
    assert value["auth_contract"] == AUTH_CONTRACT_ID
    assert value["auth_class"] == "claude.ai:oauth:firstParty"
    assert value["billing_route"] == "requires_separate_account_evidence"
    assert calls == [["--version"], ["auth", "status", "--json"]]


def fixture(tmp_path):
    blob = tmp_path / ('sha256-' + 'a' * 64)
    blob.write_bytes(b'synthetic local model blob')
    identity = {'provider': 'openai-compat', 'model_id': QWEN_MODEL,
                'endpoint': 'http://127.0.0.1:11434/v1', 'prompt_sha256': 'b' * 64,
                'parser_version': PARSER_VERSION, 'sampling': {'temperature': 0.0}}
    data = {'/api/version': {'version': 'fixture'},
            '/api/tags': {'models': [{'name': QWEN_MODEL, 'digest': 'c' * 64, 'size': 1}]},
            '/api/show': {'details': {}, 'model_info': {}, 'capabilities': [], 'modelfile': 'FROM ' + str(blob)}}
    return blob, identity, data


def test_local_metadata_only_check_binds_local_blob_digest(tmp_path, monkeypatch):
    blob, identity, data = fixture(tmp_path)
    calls = []
    monkeypatch.setattr('scripts.pilot_preflight._default_fetch_json', lambda base, method, path, payload: calls.append((method,path)) or data[path])
    value = local_qwen_identity(identity, 'fixture')
    assert value['model']['from_digests'] == ['sha256:' + 'a' * 64]
    assert calls == [('GET','/api/version'),('GET','/api/tags'),('POST','/api/show')]


def test_multiline_template_quotes_do_not_break_local_blob_check(tmp_path, monkeypatch):
    blob, identity, data = fixture(tmp_path)
    data['/api/show']['modelfile'] += '\nTEMPLATE """\n{{ if .System }}\nuser\'s text\n"""\n'
    monkeypatch.setattr('scripts.pilot_preflight._default_fetch_json', lambda base, method, path, payload: data[path])
    value = local_qwen_identity(identity, 'fixture')
    assert value['model']['from_digests'] == ['sha256:' + 'a' * 64]


def test_malformed_from_quotes_refuse_with_typed_failure(tmp_path, monkeypatch):
    blob, identity, data = fixture(tmp_path)
    data['/api/show']['modelfile'] = 'FROM "' + str(blob)
    monkeypatch.setattr('scripts.pilot_preflight._default_fetch_json', lambda base, method, path, payload: data[path])
    with pytest.raises(PilotRefusal, match='qwen_local_blobs_unavailable'):
        local_qwen_identity(identity, 'fixture')


@pytest.mark.parametrize('failure', ['nested_cloud', 'symlink', 'empty_blob'])
def test_cloud_or_nonlocal_blob_evidence_refuses(tmp_path, monkeypatch, failure):
    blob, identity, data = fixture(tmp_path)
    if failure == 'nested_cloud': data['/api/show']['details']['cloud'] = True
    if failure == 'empty_blob': blob.write_bytes(b'')
    if failure == 'symlink':
        target = tmp_path / 'other'; target.write_bytes(b'x'); blob.unlink(); blob.symlink_to(target)
    monkeypatch.setattr('scripts.pilot_preflight._default_fetch_json', lambda base, method, path, payload: data[path])
    with pytest.raises(PilotRefusal):
        local_qwen_identity(identity, 'fixture')
