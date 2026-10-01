"""Read-only metadata checks. Never invokes model inference or changes settings."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shlex
import tempfile
import stat
import re

from harness.models.base import ModelSpec
from scripts.pilot_claude_code import AUTH_CONTRACT_ID, ClaudeCodePilot
from scripts.pilot_contract import CLAUDE_MODEL, QWEN_MODEL, CallAllowance, PilotLimits, PilotRefusal
from scripts.pilot_execution import require, utc_now
from scripts.pilot_identity import capture_identity, _default_fetch_json


def claude_metadata(executable: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='harnessie-metadata-') as directory:
        adapter = ClaudeCodePilot(ModelSpec('frontier', 'pilot', CLAUDE_MODEL), executable,
            Path(directory), CallAllowance(PilotLimits(max_calls=0, timeout_s=20, max_output_bytes=64_000)))
        version = adapter._run([str(executable), '--version'], b'')
        require(version.failure is None and version.returncode == 0 and version.output is not None, 'cli_version_unavailable')
        value = version.output.decode('utf-8').strip()
        require(bool(value) and len(value) < 200, 'cli_version_unavailable')
        auth = adapter._run([str(executable), 'auth', 'status', '--json'], b'')
        auth_class = adapter._auth_class(adapter._json_object(auth.output))
        require(auth.failure is None and auth.returncode == 0 and auth_class is not None, 'auth_ineligible')
        return {'model_id': CLAUDE_MODEL, 'auth_contract': AUTH_CONTRACT_ID,
                'auth_class': auth_class, 'cli_version': value,
                'executable': str(executable.resolve()), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                'checked_at': utc_now().isoformat(),
                'billing_route': 'requires_separate_account_evidence'}


def local_qwen_identity(harness_identity: dict, client_version: str) -> dict:
    """Reject cloud/remote model metadata and require local FROM blob files."""
    base = 'http://127.0.0.1:11434'
    def local_only(value):
        if isinstance(value, dict):
            for k, v in value.items():
                require(not (('remote' in k.lower() or 'cloud' in k.lower()) and v), 'qwen_remote_model')
                local_only(v)
        elif isinstance(value, list):
            for item in value:
                local_only(item)
    def fetch(method, path, payload=None):
        data = _default_fetch_json(base, method, path, payload)
        candidates = [data]
        if path == '/api/tags':
            candidates += [m for m in data.get('models', []) if isinstance(m, dict) and m.get('name') == QWEN_MODEL]
        for candidate in candidates:
            # Only the selected tag is relevant in a multi-model tags inventory.
            local_only({k: v for k, v in candidate.items() if k != 'models'})
        if path == '/api/show':
            lines = data.get('modelfile', '').splitlines()
            from_paths = []
            for line in lines:
                # Other directives can contain multiline template text with
                # unbalanced quotes on an individual line. Only FROM is a path.
                if re.match(r'^\s*FROM(?:\s|$)', line, re.IGNORECASE):
                    try:
                        parts = shlex.split(line)
                    except ValueError as exc:
                        raise PilotRefusal('qwen_local_blobs_unavailable') from exc
                    require(len(parts) == 2, 'qwen_local_blobs_unavailable')
                    p = Path(parts[1])
                    require(p.is_absolute() and not p.is_symlink()
                            and all(not x.is_symlink() for x in p.parents)
                            and p.is_file() and stat.S_ISREG(p.stat().st_mode) and p.stat().st_size > 0
                            and re.fullmatch(r'sha256-[a-f0-9]{64}', p.name) is not None,
                            'qwen_local_blobs_unavailable')
                    from_paths.append(p)
            require(bool(from_paths), 'qwen_local_blobs_unavailable')
        return data
    return capture_identity(base_url=base, model=QWEN_MODEL, client_version=client_version,
                            harness_identity=harness_identity, fetch_json=fetch)
