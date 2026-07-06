from harness.memory import ProjectMemory
from harness.state import RunState


def test_journal_resume_skips_completed(tmp_path):
    s1 = RunState.open(tmp_path / "run")
    assert not s1.has("phase:plan")
    s1.record("phase:plan", {"status": "passed", "report": "the plan"})

    s2 = RunState.open(tmp_path / "run")     # fresh object, same journal
    assert s2.has("phase:plan")
    assert s2.result("phase:plan")["report"] == "the plan"


def test_memory_fact_has_provenance_and_index(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    path = mem.save_fact("Use replace not format", "str.format eats braces.",
                         fact_type="lesson", source="run 20260706-1")
    content = path.read_text()
    assert "source: run 20260706-1" in content and "date:" in content
    index = mem.index_path.read_text()
    assert "use-replace-not-format.md" in index

    # saving again updates in place, no duplicate index lines
    mem.save_fact("Use replace not format", "updated body", source="run 2")
    index = mem.index_path.read_text()
    assert index.count("use-replace-not-format.md") == 1


def test_context_block_is_index_only(tmp_path):
    mem = ProjectMemory(tmp_path / "memory")
    mem.save_fact("A big fact", "x" * 10_000)
    block = mem.context_block()
    assert "a-big-fact.md" in block
    assert "xxxx" not in block      # bodies never preloaded into context
