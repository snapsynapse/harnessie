import pytest

from harness.write_safety import (
    WriteDeclarationError,
    overlap,
    parallel_write_conflicts,
    parse_write_path,
)


def test_exact_files_are_disjoint_but_equal_files_conflict():
    assert not overlap(parse_write_path("left.txt"), parse_write_path("right.txt"))
    assert overlap(parse_write_path("same.txt"), parse_write_path("same.txt"))


def test_directory_roots_conflict_with_descendants():
    assert overlap(parse_write_path("dist/"), parse_write_path("dist/app.js"))
    assert overlap(parse_write_path("dist/"), parse_write_path("dist/assets/"))
    assert not overlap(parse_write_path("dist/"), parse_write_path("docs/index.html"))


@pytest.mark.parametrize("value", [
    "", ".", "/tmp/x", "../x", "a/../b", "a/./b", "a//b",
    "*.txt", "a\\b", " x", "a\x00b", "a\tb",
])
def test_ambiguous_or_escaping_declarations_fail_closed(value):
    with pytest.raises(WriteDeclarationError):
        parse_write_path(value)


def test_partial_group_opt_in_fails_closed():
    phases = [
        {"name": "left", "writes": []},
        {"name": "right"},
    ]
    with pytest.raises(WriteDeclarationError, match="every phase"):
        parallel_write_conflicts(phases)


def test_conflict_result_names_both_phases_and_paths():
    conflicts = parallel_write_conflicts([
        {"name": "left", "writes": ["dist/"]},
        {"name": "right", "writes": ["dist/app.js"]},
    ])
    assert len(conflicts) == 1
    assert conflicts[0].left_phase == "left"
    assert conflicts[0].right_phase == "right"


def test_portable_comparison_catches_case_and_unicode_aliases():
    assert overlap(parse_write_path("Dist/"), parse_write_path("dist/app.js"))
    assert overlap(parse_write_path("café.txt"), parse_write_path("cafe\u0301.txt"))


def test_legitimate_similar_prefixes_do_not_false_positive():
    assert not overlap(parse_write_path("dist/"), parse_write_path("distribution/app.js"))
    assert not overlap(parse_write_path("src/a.py"), parse_write_path("src/a.py.bak"))


def test_legacy_group_without_declarations_is_unchanged():
    assert parallel_write_conflicts([
        {"name": "left"},
        {"name": "right"},
    ]) == []
