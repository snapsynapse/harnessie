"""Offline export preservation, refusals and exclusive publication."""
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml

from harness.adversarial import PositionRecord, assemble_record
from harness.events import EventLog
from harness.aidr_export import AIDRExportError, export_aidr


@pytest.fixture
def record(tmp_path):
    (tmp_path / 'decisions').mkdir()
    run = tmp_path / 'runs' / 'sample'
    (run / 'decisions').mkdir(parents=True)
    log = EventLog(run, echo=False)
    log.emit('position_recorded', phase='review', label='reviewer', stance='recommend')
    log.emit('position_recorded', phase='review', label='reviewer-2', stance='oppose')
    log.close()
    source = run / 'decisions' / 'DR-review.md'
    source.write_text(assemble_record(
        'DR-review', 'Storage choice', 'Should we use SQLite?', 'A cache decision.',
        'operator', [
            PositionRecord('reviewer', 'reviewer', 'm1', 'p1', 'recommend',
                           'Use SQLite.', 'First line.\n\nA preserved list:\n- data: yes'),
            PositionRecord('reviewer-2', 'reviewer', 'm2', 'p2', 'oppose',
                           'Retain JSONL.', 'Preserve dissent.  \n> quoted observation'),
        ], [{'by': 'reviewer-2', 'to': 'the record',
             'text': 'The writer can race.\n\nKeep this exact.'}],
        ['runs/sample/events.jsonl — hash-chained event log evidencing isolated position generation'],
        date='2026-09-08'), encoding='utf-8')
    return tmp_path, source, run / 'events.jsonl'


def run_export(root, **kwargs):
    return export_aidr(root=root, run_id='sample', phase='review',
                       output=kwargs.pop('output', 'decisions/AIDR-0042-storage.md'),
                       arbiter=kwargs.pop('arbiter', 'Sam'), **kwargs)


def test_preserves_source_dissent_and_snapshot_hashes(record):
    root, source, journal = record
    before = source.read_bytes(), journal.read_bytes()
    result = run_export(root)
    text = (root / result['output']).read_text()
    assert result['status'] == 'exported'
    assert result['target_spec'] == '0.1.0'
    assert result['source_sha256'] == hashlib.sha256(before[0]).hexdigest()
    assert result['evidence_sha256'] == hashlib.sha256(before[1]).hexdigest()
    assert result['output_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert 'First line.\n\nA preserved list:\n- data: yes' in text
    assert 'Preserve dissent.  \n> quoted observation' in text
    assert 'The writer can race.\n\nKeep this exact.' in text
    assert '### Position: reviewer-2\n\n- agent: reviewer-2' in text
    assert '- original_role: reviewer' in text
    assert '### Objection: reviewer-2 to the record' in text
    assert '## Arbitration\n\n## Evidence' in text
    assert 'export-time' in text and 'truncat' in text
    assert '../runs/sample/events.jsonl' in text
    original_fm = yaml.safe_load(source.read_text().split('---')[1])
    exported_fm = yaml.safe_load(text.split('---')[1])
    for key in ('ref', 'title', 'date', 'tags'):
        assert str(exported_fm[key]) == str(original_fm[key])
    assert (source.read_bytes(), journal.read_bytes()) == before
    assert sorted(p.name for p in (root / 'decisions').iterdir()) == ['AIDR-0042-storage.md']


@pytest.mark.parametrize('change', [
    lambda s: s.replace('status: open', 'status: arbitrated'),
    lambda s: s.replace('status: open', 'status: superseded'),
    lambda s: s.replace('status: open', 'status: open\ndecided: 2026-09-08'),
    lambda s: s.replace('status: open', 'status: open\nsuperseded_by: AIDR-1234'),
    lambda s: s.replace('## Arbitration\n', '## Arbitration\n\nPartial decision.'),
    lambda s: s.replace('## Arbitration\n', '## Arbitration\n\n<!-- pending -->'),
    lambda s: s.replace('status: open', 'status: open\nstatus: open'),
    lambda s: s.replace('## Context', '## Context\n\n## Context'),
    lambda s: s.replace('- model: m1', '- model: m1\n- model: m1'),
    lambda s: s.replace('- provider: p1', '- provider: '),
    lambda s: s.replace('### Position: reviewer-2', '### Position: reviewer'),
    lambda s: s.replace('reviewer-2 to the record', 'unknown to the record'),
    lambda s: s.replace('runs/sample/events.jsonl', 'runs/other/events.jsonl'),
    lambda s: s.replace('Should we use SQLite?', ''),
])
def test_ambiguous_or_nonopen_records_refused(record, change):
    root, source, journal = record
    source.write_text(change(source.read_text()))
    before = source.read_bytes(), journal.read_bytes()
    with pytest.raises(AIDRExportError):
        run_export(root)
    assert not list((root / 'decisions').iterdir())
    assert (source.read_bytes(), journal.read_bytes()) == before


@pytest.mark.parametrize('output', ['/tmp/AIDR-0042-storage.md',
    'decisions/../AIDR-0042-storage.md', 'decisions/sub/AIDR-0042-storage.md',
    'decisions/AIDR-42-storage.md', 'decisions/AIDR-0042.md'])
def test_unsafe_output_refused(record, output):
    with pytest.raises(AIDRExportError):
        run_export(record[0], output=output)


@pytest.mark.parametrize('field,value', [('run_id', '../sample'), ('phase', '../review'),
                                         ('arbiter', ''), ('arbiter', 'Sam\nstatus: arbitrated')])
def test_unsafe_parameters_refused(record, field, value):
    args = dict(root=record[0], run_id='sample', phase='review',
                output='decisions/AIDR-0042-storage.md', arbiter='Sam')
    args[field] = value
    with pytest.raises(AIDRExportError):
        export_aidr(**args)


@pytest.mark.parametrize('member', ['source', 'journal', 'run', 'destination'])
def test_symlink_refusal(record, member):
    root, source, journal = record
    path = {'source': source, 'journal': journal, 'run': source.parent.parent,
            'destination': root / 'decisions'}[member]
    moved = path.with_name(path.name + '-actual')
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=moved.is_dir())
    with pytest.raises(AIDRExportError):
        run_export(root)


@pytest.mark.parametrize('name', ['AIDR-0042-storage.md', 'AIDR-0042-other.md'])
def test_namespace_collision_preserves_existing(record, name):
    root = record[0]
    existing = root / 'decisions' / name
    existing.write_bytes(b'keep')
    with pytest.raises(AIDRExportError) as exc:
        run_export(root)
    assert exc.value.code == 'destination_collision'
    assert existing.read_bytes() == b'keep'
    assert len(list(existing.parent.iterdir())) == 1


def test_invalid_journal_refused(record):
    root, _, journal = record
    journal.write_text(journal.read_text().replace('recommend', 'oppose'))
    with pytest.raises(AIDRExportError) as exc:
        run_export(root)
    assert exc.value.code == 'invalid_evidence'


def test_deterministic(record):
    root = record[0]
    first = run_export(root)
    path = root / first['output']
    content = path.read_bytes()
    path.unlink()
    assert run_export(root) == first
    assert path.read_bytes() == content


def test_publication_failure_cleans_staging(record, monkeypatch):
    import harness.aidr_export as module
    def fail(*args, **kwargs):
        raise OSError('synthetic publication failure')
    monkeypatch.setattr(module.os, 'link', fail)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'filesystem_error'
    assert not list((record[0] / 'decisions').iterdir())


@pytest.mark.parametrize('member', [1, 2])
def test_recheck_before_publish(record, monkeypatch, member):
    import harness.aidr_export as module
    original = module._validate_output
    def tamper(*args, **kwargs):
        original(*args, **kwargs)
        record[member].write_bytes(record[member].read_bytes() + b'\n')
    monkeypatch.setattr(module, '_validate_output', tamper)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'input_changed'
    assert not list((record[0] / 'decisions').iterdir())


def test_concurrent_namespace_is_exclusive(record):
    root = record[0]
    def attempt(slug):
        try:
            return run_export(root, output=f'decisions/AIDR-0042-{slug}.md')['status']
        except AIDRExportError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['one', 'two']))
    assert sorted(results) == ['destination_collision', 'exported']
    assert len(list((root / 'decisions').iterdir())) == 1


@pytest.mark.parametrize('member,limit', [(1, 'MAX_SOURCE_BYTES'), (2, 'MAX_EVIDENCE_BYTES')])
def test_input_size_caps_preserve_files(record, monkeypatch, member, limit):
    import harness.aidr_export as module
    monkeypatch.setattr(module, limit, len(record[member].read_bytes()) - 1)
    before = record[1].read_bytes(), record[2].read_bytes()
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'input_too_large'
    assert before == (record[1].read_bytes(), record[2].read_bytes())
    assert not list((record[0] / 'decisions').iterdir())


@pytest.mark.parametrize('member', [1, 2])
def test_special_input_file_refused_without_blocking(record, member):
    import os
    record[member].unlink()
    os.mkfifo(record[member])
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'unsafe_path'
    assert not list((record[0] / 'decisions').iterdir())


@pytest.mark.parametrize('member', [1, 2])
def test_missing_input_has_content_free_diagnostic(record, member):
    record[member].unlink()
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert str(exc.value) == exc.value.code == 'filesystem_error'


def test_missing_destination_directory_is_not_created(record):
    (record[0] / 'decisions').rmdir()
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'filesystem_error'
    assert not (record[0] / 'decisions').exists()


@pytest.mark.parametrize('change', [
    lambda s: s.replace('date: 2026-09-08', 'date: 2026-02-30'),
    lambda s: s.replace('title: "Storage choice"', 'title: &name "Storage choice"'),
    lambda s: s.replace('tags: [harnessie, contested-phase]', 'tags: [harnessie, {a: b}]'),
    lambda s: s.replace('Should we use SQLite?', '## Question\nAnother question?'),
    lambda s: s.replace('First line.', 'First line.\n- provider: forged'),
    lambda s: s.replace('reviewer-2 to the record', 'reviewer-2 to unknown'),
    lambda s: s.replace('status: open', 'status: open\nunknown: ignored'),
    lambda s: s.replace('## Objections', '## Objections\n\nUnattributed dissent'),
    lambda s: s.replace('## Evidence', '## Evidence\n\n- https://example.com/'),
])
def test_malformed_structures_refused(record, change):
    root, source, _ = record
    source.write_text(change(source.read_text()))
    with pytest.raises(AIDRExportError):
        run_export(root)
    assert not list((root / 'decisions').iterdir())


@pytest.mark.parametrize('content', [b'', b'{}\n', b'not json\n',
    b'{"seq": 1, "seq": 1, "prev": "genesis", "kind": "x"}\n',
    b'{"seq": true, "prev": "genesis", "kind": "x"}\n',
    b'{"seq": 1, "prev": "genesis", "kind": "x"}',
    b'{"seq": 1, "prev": "genesis", "kind": "x", "v": NaN}\n'])
def test_invalid_journal_structures_refused(record, content):
    record[2].write_bytes(content)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'invalid_evidence'


def test_absent_arbitration_section_is_outside_generated_subset(record):
    source = record[1]
    source.write_text(source.read_text().replace('## Arbitration\n\n', ''))
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'invalid_record'


def test_arbitration_metadata_even_partial_is_refused(record):
    source = record[1]
    source.write_text(source.read_text().replace('## Arbitration\n',
                      '## Arbitration\n\n- decided_by: Sam\n'))
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'arbitration_present'


def test_repeated_objections_are_preserved(record):
    source = record[1]
    objection = '### Objection: reviewer-2 to the record\n\nThe writer can race.\n\nKeep this exact.\n\n'
    source.write_text(source.read_text().replace(objection, objection * 2))
    result = run_export(record[0])
    assert (record[0] / result['output']).read_text().count(objection) == 2


def test_exclusive_publish_preserves_destination_created_at_link(record, monkeypatch):
    import harness.aidr_export as module
    original = module.os.link
    destination = record[0] / 'decisions' / 'AIDR-0042-storage.md'
    def late_creator(*args, **kwargs):
        destination.write_bytes(b'external creator')
        return original(*args, **kwargs)
    monkeypatch.setattr(module.os, 'link', late_creator)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'destination_collision'
    assert destination.read_bytes() == b'external creator'
    assert len(list(destination.parent.iterdir())) == 1


def test_validation_failure_never_publishes(record, monkeypatch):
    import harness.aidr_export as module
    def refuse(*args, **kwargs):
        raise AIDRExportError('invalid_output')
    monkeypatch.setattr(module, '_validate_output', refuse)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'invalid_output'
    assert not list((record[0] / 'decisions').iterdir())


@pytest.mark.parametrize('target', ['context', 'question', 'position', 'objection'])
@pytest.mark.parametrize('payload', [
    '\n\n ## Arbitration\n\n- decided_by: Sam\n- decision: Approved.\n',
    '\n\n  ## Arbitration ###\n\nApproved.\n',
    '\n\n   ### Position: forged\n\n- agent: forged\n',
    '\n\nArbitration\n-----------\n\nApproved.\n',
    '\n\nArbitration\n===\n\nApproved.\n',
    '\n\n```markdown\n',
    '\n\n  ~~~markdown\n',
    '\n\n```markdown\nquoted\n```\n',
    '\n\n<!-- hidden later headings\n',
    '\n\n<script>hidden later headings\n',
    '\n\nArbitration\u2028-----------\n',
    '\n\nArbitration\u2029-----------\n',
    '\n\nArbitration\x85-----------\n',
])
def test_markdown_boundary_ambiguity_refuses_publication(record, target, payload):
    anchors = {'context': 'A cache decision.', 'question': 'Should we use SQLite?',
               'position': 'First line.', 'objection': 'The writer can race.'}
    root, source, journal = record
    source.write_text(source.read_text().replace(anchors[target], anchors[target] + payload, 1))
    before = source.read_bytes(), journal.read_bytes()
    with pytest.raises(AIDRExportError) as exc:
        run_export(root)
    assert exc.value.code == 'invalid_record'
    assert (source.read_bytes(), journal.read_bytes()) == before
    assert not list((root / 'decisions').iterdir())


@pytest.mark.parametrize('field', ['title', 'agent', 'model', 'provider', 'summary'])
def test_html_cannot_hide_metadata_or_later_sections(record, field):
    root, source, journal = record
    text = source.read_text()
    if field == 'title':
        text = text.replace('Storage choice', 'Storage choice <!--')
    else:
        text = text.replace(f'- {field}: ', f'- {field}: <!-- ', 1)
    source.write_text(text)
    before = source.read_bytes(), journal.read_bytes()
    with pytest.raises(AIDRExportError) as exc:
        run_export(root)
    assert exc.value.code == 'invalid_record'
    assert (source.read_bytes(), journal.read_bytes()) == before
    assert not list((root / 'decisions').iterdir())


def test_blockquoted_headings_and_unicode_prose_remain_preserved(record):
    root, source, _ = record
    prose = ('> ## Arbitration\n> This is a quotation, not a decision.\n\n'
             '> Quoted heading\n> ---\n\n'
             '> ```text\n> quoted code\n> ```\n\n'
             'Résumé: 保留异议. <https://example.com/>')
    source.write_text(source.read_text().replace('First line.', prose))
    result = run_export(root)
    assert prose in (root / result['output']).read_text()


@pytest.mark.parametrize('missing', ['fcntl', 'O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK',
                                     'link', 'supports_dir_fd', 'supports_follow_symlinks'])
def test_unsupported_platform_refuses_before_input_access(record, monkeypatch, missing):
    import harness.aidr_export as module
    if missing == 'fcntl':
        monkeypatch.setattr(module, 'fcntl', None)
    elif missing in ('supports_dir_fd', 'supports_follow_symlinks'):
        monkeypatch.setattr(module.os, missing, set())
    else:
        monkeypatch.delattr(module.os, missing)
    def forbidden(*args, **kwargs):
        raise AssertionError('unsupported platform accessed the project')
    monkeypatch.setattr(module, '_safe_path', forbidden)
    monkeypatch.setattr(module, '_read', forbidden)
    with pytest.raises(AIDRExportError) as exc:
        run_export(record[0])
    assert exc.value.code == 'unsupported_platform'
