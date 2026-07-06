"""Project memory and proof artifacts.

Two distinct stores, deliberately file-based (inspectable, diffable, portable
across brains and across harnesses):

1. Facts — memory/facts/<slug>.md, one fact per file with YAML frontmatter
   carrying provenance (source, run, date). memory/MEMORY.md is a one-line-per-
   fact index that gets injected into orchestrator context at run start. Small,
   scoped, provenance-aware; memory without provenance is how stale context
   starts dominating runs.

2. Proofs — runs/<run_id>/proofs/: test reports, lint output, diffs, fetched
   evidence. A task is not "done" because an agent said so; it is done because
   a proof artifact exists and a verifier checked it.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

FACT_TYPES = ("decision", "constraint", "reference", "lesson")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "fact"


@dataclass
class ProjectMemory:
    root: Path  # the memory/ directory

    @property
    def index_path(self) -> Path:
        return self.root / "MEMORY.md"

    @property
    def facts_dir(self) -> Path:
        return self.root / "facts"

    def save_fact(self, title: str, body: str, fact_type: str = "lesson",
                  source: str = "unspecified") -> Path:
        if fact_type not in FACT_TYPES:
            raise ValueError(f"fact_type must be one of {FACT_TYPES}")
        self.facts_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(title)
        path = self.facts_dir / f"{slug}.md"
        date = time.strftime("%Y-%m-%d")
        path.write_text(
            f"---\nname: {slug}\ntype: {fact_type}\nsource: {source}\n"
            f"date: {date}\n---\n\n# {title}\n\n{body.strip()}\n",
            encoding="utf-8")
        self._index_add(slug, title, fact_type)
        return path

    def _index_add(self, slug: str, title: str, fact_type: str) -> None:
        line = f"- [{title}](facts/{slug}.md) `{fact_type}`"
        existing = self.index_path.read_text(encoding="utf-8") if self.index_path.exists() else "# Project memory index\n"
        if f"(facts/{slug}.md)" in existing:
            existing = "\n".join(
                line if f"(facts/{slug}.md)" in old else old
                for old in existing.splitlines())
        else:
            existing = existing.rstrip("\n") + "\n" + line
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(existing.rstrip("\n") + "\n", encoding="utf-8")

    def context_block(self, max_chars: int = 4000) -> str:
        """What gets injected into orchestrator context at run start: the index
        only. Agents read individual fact files on demand via read_file —
        recall is cheap, preloading everything is how context bloats."""
        if not self.index_path.exists():
            return "(no project memory yet)"
        return self.index_path.read_text(encoding="utf-8")[:max_chars]


@dataclass
class ProofStore:
    run_dir: Path

    @property
    def proofs_dir(self) -> Path:
        return self.run_dir / "proofs"

    def save(self, name: str, content: str) -> Path:
        self.proofs_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        path = self.proofs_dir / safe
        path.write_text(content, encoding="utf-8")
        return path

    def listing(self) -> list[str]:
        if not self.proofs_dir.exists():
            return []
        return sorted(p.name for p in self.proofs_dir.iterdir())
