"""Deterministic offline export of the generated, open contested-record subset.

Validation profile: AIDR SPEC 0.1.0, reference revision a67c41d. Structural
validation cannot authenticate people, authorship or independent review. Inputs
and the destination directory must be operator-controlled. Directory flock
coordinates cooperating exporters; this is not a sandbox for concurrent OS
writers. No runner, provider, registry or model is initialized by this module.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

import yaml

try:
    import fcntl
except ImportError:  # Native Windows has no POSIX advisory directory locking.
    fcntl = None

# Preserve capability identities independently of instrumentation wrappers.
_DIR_FD_FUNCTIONS = tuple(getattr(os, name, None) for name in ('link', 'unlink'))
_LINK_FUNCTION = getattr(os, 'link', None)

TARGET_SPEC = '0.1.0'
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
_COMPONENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
_FILENAME = re.compile(r'(AIDR-[0-9]{4,})-[a-z0-9]+(?:-[a-z0-9]+)*\.md\Z')
_LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.@/-]{0,127}\Z')
_SECTIONS = ('Context', 'Question', 'Positions', 'Objections', 'Arbitration', 'Evidence')
_KEYS = ('agent', 'model', 'provider', 'stance', 'summary')
_STANCES = {'recommend', 'oppose', 'alternative', 'abstain'}


class AIDRExportError(ValueError):
    """Stable, content-free diagnostic suitable for a CLI refusal."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise AIDRExportError(code)


def _require_platform() -> None:
    """Refuse unsupported primitives before reading or writing project data."""
    if (os.name != 'posix' or fcntl is None
            or not callable(getattr(fcntl, 'flock', None))
            or not isinstance(getattr(fcntl, 'LOCK_EX', None), int)
            or any(not isinstance(getattr(os, name, None), int)
                   for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK'))
            or any(not callable(getattr(os, name, None))
                   for name in ('open', 'link', 'unlink', 'fstat', 'fsync', 'close'))
            or not all(fn in getattr(os, 'supports_dir_fd', ()) for fn in _DIR_FD_FUNCTIONS)
            or _LINK_FUNCTION not in getattr(os, 'supports_follow_symlinks', ())):
        _fail('unsupported_platform')


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _plain(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip())
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _safe_path(path: Path, directory: bool = False) -> None:
    """Reject links and special files including intermediate components."""
    for part in reversed((path, *path.parents)):
        mode = part.lstat().st_mode
        if stat.S_ISLNK(mode):
            _fail('unsafe_path')
        if part != path or directory:
            if not stat.S_ISDIR(mode):
                _fail('unsafe_path')
        elif not stat.S_ISREG(mode):
            _fail('unsafe_path')


def _read(path: Path, limit: int) -> bytes:
    _safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            _fail('unsafe_path')
        if info.st_size > limit:
            _fail('input_too_large')
        data = stream.read(limit + 1)
        if len(data) > limit:
            _fail('input_too_large')
        return data


def _decode(data: bytes, code: str) -> str:
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        _fail(code)
    if (any(ord(c) < 32 and c not in '\n\t' for c in text)
            or any(c in text for c in ('\x7f', '\x85', '\u2028', '\u2029'))):
        _fail(code)
    return text


def _prose_boundaries(text: str) -> None:
    """Reject Markdown that can impersonate or consume record boundaries.

    This is a bounded subset, not a general Markdown parser. In particular,
    unquoted headings (including setext), fences and raw HTML are unsupported.
    Quote-prefixed headings/fences remain prose, as emitted by _fence_prose.
    Raw HTML is checked across the complete record separately because a comment
    or raw tag in metadata can hide later sections too.
    """
    for line in text.split('\n'):
        content = line.lstrip(' \t')
        # Also reject headings/fences nested in lists; preserve quoted examples.
        while True:
            marker = re.match(r'(?:[-+*]|[0-9]{1,9}[.)])[ \t]+', content)
            if not marker:
                break
            content = content[marker.end():].lstrip(' \t')
        if content.startswith('>'):
            continue
        if (re.match(r'#{1,6}(?:[ \t]|$)', content)
                or re.fullmatch(r'(?:=+|-+)[ \t]*', content)
                or re.match(r'(?:`{3,}|~{3,})', content)):
            _fail('invalid_record')


def _frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        _fail('invalid_record')
    # The producer writes a flat mapping with one entry per line. Refusing
    # aliases, merges and multiline YAML avoids ambiguous alternate parsings.
    names = []
    for line in match[1].splitlines():
        item = re.fullmatch(r'([a-z_]+): (.+)', line)
        if not item or item[1] in names:
            _fail('invalid_record')
        names.append(item[1])
    try:
        # Token inspection also rejects aliases inside otherwise flat lists.
        for token in yaml.scan(match[1]):
            if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken,
                                  yaml.tokens.TagToken)):
                _fail('invalid_record')
        fm = yaml.safe_load(match[1])
    except (yaml.YAMLError, ValueError, RecursionError):
        _fail('invalid_record')
    if not isinstance(fm, dict) or len(fm) != len(names):
        _fail('invalid_record')
    return fm, text[match.end():]


def _parse(text: str, identifier: str, *, exported: bool = False) -> tuple[dict, dict, list]:
    # Raw tags/comments may suppress rendered governance metadata even when
    # embedded in a metadata value or a blockquote. Autolinks remain allowed.
    if re.search(r'<(?:!--|!\[CDATA\[|\?|![A-Z]|/?[A-Za-z][A-Za-z0-9-]*(?=[\s/>]|$))', text):
        _fail('invalid_record')
    fm, body = _frontmatter(text)
    if fm.get('status') != 'open' or any(k in fm for k in ('decided', 'superseded_by', 'supersedes')):
        _fail('record_not_open')
    required = {'id', 'ref', 'title', 'status', 'date', 'arbiter', 'tags'}
    allowed = required | ({'source_id', 'source_arbiter', 'target_spec'} if exported else set())
    if set(fm) - allowed or not required <= set(fm):
        _fail('invalid_record')
    if fm['id'] != identifier or any(not _plain(fm[k]) for k in ('id', 'ref', 'title', 'arbiter')):
        _fail('invalid_record')
    if not re.fullmatch(r'DR-[A-Za-z0-9-]+', fm['ref']):
        _fail('invalid_record')
    date = str(fm['date'])
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            _fail('invalid_record')
        datetime.date.fromisoformat(date)
    except ValueError:
        _fail('invalid_record')
    if not isinstance(fm['tags'], list) or any(not _plain(v) for v in fm['tags']):
        _fail('invalid_record')
    title_line = f"# {identifier}: {fm['title']}\n"
    if not body.startswith(title_line):
        _fail('invalid_record')
    marks = list(re.finditer(r'^## (.*)\n', body, re.M))
    if [m[1] for m in marks] != list(_SECTIONS):
        _fail('invalid_record')
    if body[len(title_line):marks[0].start()].strip():
        _fail('invalid_record')
    sections = {m[1]: body[m.end():marks[i+1].start() if i+1 < len(marks) else len(body)]
                for i, m in enumerate(marks)}
    if sections['Arbitration'].strip():
        _fail('arbitration_present')
    for name in ('Context', 'Question'):
        if not sections[name].strip():
            _fail('invalid_record')
        _prose_boundaries(sections[name])
    positions = []
    pos_body = sections['Positions']
    pos_marks = list(re.finditer(r'^### Position: (.+)\n', pos_body, re.M))
    if not pos_marks or pos_body[:pos_marks[0].start()].strip():
        _fail('invalid_record')
    labels = set()
    for i, mark in enumerate(pos_marks):
        label = mark[1]
        if not _LABEL.fullmatch(label) or label in labels:
            _fail('invalid_record')
        labels.add(label)
        block = pos_body[mark.end():pos_marks[i+1].start() if i+1 < len(pos_marks) else len(pos_body)]
        metadata_keys = _KEYS + (('original_role',) if exported else ())
        pattern = r'\A\n' + ''.join(r'- ' + key + r': ([^\n]+)\n' for key in metadata_keys) + r'\n'
        match = re.match(pattern, block)
        if not match:
            _fail('invalid_record')
        meta = dict(zip(metadata_keys, match.groups()))
        if any(not _plain(v) for v in meta.values()) or meta['stance'] not in _STANCES:
            _fail('invalid_record')
        if exported and meta['agent'] != label:
            _fail('invalid_record')
        prose = block[match.end():]
        if not prose.strip():
            _fail('invalid_record')
        _prose_boundaries(prose)
        if re.search(r'^- (?:agent|model|provider|stance|summary|original_role):', prose, re.M):
            _fail('invalid_record')
        positions.append((label, block, meta))
    obj_body = sections['Objections']
    obj_marks = list(re.finditer(r'^### Objection: (.+?) to (.+)\n', obj_body, re.M))
    if (obj_body[:obj_marks[0].start()].strip() if obj_marks else obj_body.strip()):
        _fail('invalid_record')
    for i, mark in enumerate(obj_marks):
        if mark[1] not in labels or mark[2] not in labels | {'the record'}:
            _fail('invalid_record')
        prose = obj_body[mark.end():obj_marks[i+1].start() if i+1 < len(obj_marks) else len(obj_body)]
        if not prose.strip():
            _fail('invalid_record')
        _prose_boundaries(prose)
    return fm, sections, positions


def _journal(data: bytes) -> None:
    text = _decode(data, 'invalid_evidence')
    if not text or not text.endswith('\n'):
        _fail('invalid_evidence')
    previous = 'genesis'
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('invalid_evidence')
            result[key] = value
        return result
    for seq, line in enumerate(text.splitlines(), 1):
        try:
            event = json.loads(line, object_pairs_hook=pairs,
                               parse_constant=lambda _: _fail('invalid_evidence'))
        except (ValueError, RecursionError):
            _fail('invalid_evidence')
        if (not isinstance(event, dict) or type(event.get('seq')) is not int
                or event['seq'] != seq or event.get('prev') != previous
                or not _plain(event.get('kind'))):
            _fail('invalid_evidence')
        previous = _digest(line.encode('utf-8'))


def _render(fm: dict, sections: dict, positions: list, identifier: str,
            arbiter: str, source_rel: str, evidence_rel: str,
            source_hash: str, evidence_hash: str) -> bytes:
    output_fm = dict(fm, id=identifier, arbiter=arbiter, source_id=fm['id'],
                     source_arbiter=fm['arbiter'], target_spec=TARGET_SPEC)
    output_fm['date'] = str(fm['date'])
    # JSON scalars/lists are a deliberately small, portable YAML subset.
    lines = ['---'] + [f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in output_fm.items()]
    lines += ['---', f"# {identifier}: {fm['title']}", '']
    text = '\n'.join(lines) + '\n'
    qualifications = (
        'Export provenance and limits: participant headings are retained as unique '
        'agent labels; original_role retains each recorded role. Model/provider '
        'identities and the original arbiter are source-reported, not authenticated. '
        'The destination arbiter is an operator declaration of human authority, not '
        'identity verification. Source independence statements are retained as '
        'reported claims: a valid hash chain does not prove isolation, evidence '
        'access, authorship, or independence. Initial positions and subsequent '
        'objections remain separate; objection rounds had access to other positions. '
        'The runtime truncates objection strings to 500 characters and event '
        'objection text to 200; this export preserves only the text that exists '
        'and cannot recover omitted text or infer round boundaries. The question '
        'is retained verbatim; its semantic decidability requires human review. '
        'Hashes identify the source and journal consumed at export-time, not '
        'original authorship or an immutable original review packet. Mutable '
        'references embedded in prose are retained as prose, not certified '
        'evidence snapshots. No arbitration is authored by this export.\n\n')
    for name in _SECTIONS:
        text += f'## {name}\n'
        if name == 'Positions':
            text += '\n'
            for label, block, meta in positions:
                old = f"\n- agent: {meta['agent']}\n"
                block = block.replace(old, f'\n- agent: {label}\n', 1)
                marker = f"- summary: {meta['summary']}\n"
                block = block.replace(marker, marker + f"- original_role: {meta['agent']}\n", 1)
                text += f'### Position: {label}\n' + block
        elif name == 'Evidence':
            description = sections[name].strip().split(' — ', 1)[1]
            text += (f'\n- [Source record](../{source_rel}); SHA-256: `{source_hash}`. '
                     'Consumed source snapshot.\n'
                     f'- [Run event journal](../{evidence_rel}) — {description}; '
                     f'SHA-256: `{evidence_hash}`. Chain verified at export-time; '
                     'the source description is a reported claim.\n')
        else:
            text += sections[name]
            if name == 'Context':
                text += qualifications
    return text.encode('utf-8')


def _validate_output(data: bytes, identifier: str) -> None:
    """Strict open-record structural subset of the pinned 0.1.0 profile."""
    fm, _, _ = _parse(_decode(data, 'invalid_output'), identifier, exported=True)
    if fm['target_spec'] != TARGET_SPEC or not _plain(fm['source_arbiter']):
        _fail('invalid_output')


def _namespace(directory: Path, identifier: str) -> None:
    for member in directory.iterdir():
        if re.match(re.escape(identifier) + r'(?:[^0-9]|$)', member.name):
            _fail('destination_collision')


def export_aidr(root: Path, run_id: str, phase: str, output: str, arbiter: str) -> dict:
    """Export one generated open record to an unused explicitly reserved filename.

    All refusals use AIDRExportError.code without source content. No directories
    are created. The advisory directory lock serializes this exporter, while an
    exclusive hard link publishes a fully validated sibling file atomically.
    """
    _require_platform()
    stage = None
    directory_fd = None
    try:
        if any(not isinstance(v, str) or not _COMPONENT.fullmatch(v) for v in (run_id, phase)):
            _fail('unsafe_path')
        if not _plain(arbiter) or len(arbiter) > 200 or arbiter.strip() != arbiter:
            _fail('invalid_arbiter')
        if not isinstance(output, str) or not output.startswith('decisions/'):
            _fail('unsafe_path')
        filename = output[len('decisions/'):]
        match = _FILENAME.fullmatch(filename)
        if not match:
            _fail('unsafe_path')
        identifier = match[1]
        root = Path(root).absolute()
        if '..' in root.parts:
            _fail('unsafe_path')
        _safe_path(root, directory=True)
        directory = root / 'decisions'
        _safe_path(directory, directory=True)
        source_rel = f'runs/{run_id}/decisions/DR-{phase}.md'
        evidence_rel = f'runs/{run_id}/events.jsonl'
        source = root / source_rel
        evidence = root / evidence_rel
        source_bytes = _read(source, MAX_SOURCE_BYTES)
        fm, sections, positions = _parse(_decode(source_bytes, 'invalid_record'), f'DR-{phase}')
        expected = f'- {evidence_rel} — hash-chained event log evidencing isolated position generation'
        if sections['Evidence'].strip() != expected:
            _fail('unresolved_evidence')
        evidence_bytes = _read(evidence, MAX_EVIDENCE_BYTES)
        _journal(evidence_bytes)
        source_hash, evidence_hash = _digest(source_bytes), _digest(evidence_bytes)
        data = _render(fm, sections, positions, identifier, arbiter, source_rel,
                       evidence_rel, source_hash, evidence_hash)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        _namespace(directory, identifier)
        fd, stage_name = tempfile.mkstemp(prefix='.aidr-export-', suffix='.tmp', dir=directory)
        stage = Path(stage_name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        staged_bytes = _read(stage, MAX_SOURCE_BYTES * 2)
        if staged_bytes != data:
            _fail('input_changed')
        _validate_output(staged_bytes, identifier)
        # Recheck immediately before exclusive publication, including directory
        # identity. External writers must still respect the operator trust bound.
        if (_read(source, MAX_SOURCE_BYTES) != source_bytes
                or _read(evidence, MAX_EVIDENCE_BYTES) != evidence_bytes):
            _fail('input_changed')
        _safe_path(directory, directory=True)
        info, opened = directory.stat(), os.fstat(directory_fd)
        if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino):
            _fail('input_changed')
        _namespace(directory, identifier)
        os.link(stage.name, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
                follow_symlinks=False)
        return {'status': 'exported', 'output': output, 'source_sha256': source_hash,
                'evidence_sha256': evidence_hash, 'output_sha256': _digest(data),
                'target_spec': TARGET_SPEC}
    except FileExistsError:
        raise AIDRExportError('destination_collision') from None
    except (OSError, OverflowError):
        raise AIDRExportError('filesystem_error') from None
    finally:
        if stage is not None:
            try:
                # Descriptor-relative cleanup avoids following a replaced dir.
                os.unlink(stage.name, dir_fd=directory_fd)
            except OSError:
                pass
        if directory_fd is not None:
            os.close(directory_fd)
