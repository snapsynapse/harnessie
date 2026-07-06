"""Project memory and proof artifacts.

Two distinct stores, deliberately file-based (inspectable, diffable, portable
across brains and across harnesses):

1. Facts — memory/facts/<slug>.md, one fact per file with YAML frontmatter
   carrying provenance (source, run, date) plus freshness dates: `verified`
   (when the fact was last confirmed true) and `verify_by` (when it goes
   stale — default 30 days out; a fact past verify_by is surfaced by the
   memory-triage workflow, never silently trusted). memory/MEMORY.md is a
   one-line-per-fact index injected into orchestrator context at run start.
   Memory without provenance and expiry is how stale context starts
   dominating runs.

   Facts are never deleted: archive_fact moves them to memory/archive/ with
   an archival stamp and prunes the index. Deletion does not exist as a
   capability at this layer.

2. Proofs — runs/<run_id>/proofs/: test reports, lint output, diffs, fetched
   evidence. A task is not "done" because an agent said so; it is done because
   a proof artifact exists and a verifier checked it.
"""

from __future__ import annotations

import datetime
import re
import time
from dataclasses import dataclass
from pathlib import Path

FACT_TYPES = ("decision", "constraint", "reference", "lesson")
DEFAULT_VERIFY_DAYS = 30


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "fact"


def _frontmatter_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not text.startswith("---"):
        return fields
    for line in text.split("\n---", 1)[0].splitlines()[1:]:
        key, _, val = line.partition(":")
        if key.strip() and val.strip():
            fields[key.strip()] = val.strip()
    return fields


@dataclass
class ProjectMemory:
    root: Path  # the memory/ directory

    @property
    def index_path(self) -> Path:
        return self.root / "MEMORY.md"

    @property
    def facts_dir(self) -> Path:
        return self.root / "facts"

    @property
    def archive_dir(self) -> Path:
        return self.root / "archive"

    def save_fact(self, title: str, body: str, fact_type: str = "lesson",
                  source: str = "unspecified",
                  verify_by: str | None = None) -> Path:
        if fact_type not in FACT_TYPES:
            raise ValueError(f"fact_type must be one of {FACT_TYPES}")
        self.facts_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(title)
        path = self.facts_dir / f"{slug}.md"
        date = time.strftime("%Y-%m-%d")
        verify_by = verify_by or (
            datetime.date.today()
            + datetime.timedelta(days=DEFAULT_VERIFY_DAYS)).isoformat()
        path.write_text(
            f"---\nname: {slug}\ntype: {fact_type}\nsource: {source}\n"
            f"date: {date}\nverified: {date}\nverify_by: {verify_by}\n---\n\n"
            f"# {title}\n\n{body.strip()}\n",
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

    def _index_remove(self, slug: str) -> None:
        if not self.index_path.exists():
            return
        kept = [l for l in self.index_path.read_text(encoding="utf-8").splitlines()
                if f"(facts/{slug}.md)" not in l]
        self.index_path.write_text("\n".join(kept).rstrip("\n") + "\n",
                                   encoding="utf-8")

    # -- freshness + disposal ----------------------------------------------------

    def stale_facts(self, today: str | None = None) -> list[dict[str, str]]:
        """Facts past their verify_by date. ISO dates compare lexically."""
        today = today or datetime.date.today().isoformat()
        out: list[dict[str, str]] = []
        if not self.facts_dir.exists():
            return out
        for path in sorted(self.facts_dir.glob("*.md")):
            fields = _frontmatter_fields(path.read_text(encoding="utf-8"))
            verify_by = fields.get("verify_by", "")
            if verify_by and verify_by < today:
                title = path.read_text(encoding="utf-8").split("\n# ", 1)
                out.append({
                    "slug": path.stem,
                    "title": title[1].splitlines()[0] if len(title) > 1 else path.stem,
                    "verify_by": verify_by,
                    "path": str(path),
                })
        return out

    def archive_fact(self, slug: str, reason: str = "") -> Path:
        """Move a fact to memory/archive/ and prune the index. Never deletes.

        The archival stamp (date + reason) is appended to frontmatter so the
        archive is self-explaining."""
        src = self.facts_dir / f"{slug}.md"
        if not src.exists():
            raise KeyError(f"no fact named {slug!r} under {self.facts_dir}")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        date = time.strftime("%Y-%m-%d")
        stamp = f"archived: {date}\n"
        if reason:
            stamp += f"archive_reason: {reason}\n"
        if text.startswith("---\n"):
            text = text.replace("---\n", f"---\n{stamp}", 1)
        else:
            text = f"---\n{stamp}---\n\n" + text
        dest = self.archive_dir / f"{slug}.md"
        dest.write_text(text, encoding="utf-8")
        src.unlink()
        self._index_remove(slug)
        return dest

    def lint(self) -> list[str]:
        """Structural consistency: every index line resolves to a fact file,
        every fact file is indexed, and provenance fields are present."""
        problems: list[str] = []
        indexed: set[str] = set()
        if self.index_path.exists():
            for line in self.index_path.read_text(encoding="utf-8").splitlines():
                m = re.search(r"\(facts/([^)]+)\.md\)", line)
                if not m:
                    continue
                indexed.add(m.group(1))
                if not (self.facts_dir / f"{m.group(1)}.md").exists():
                    problems.append(f"index points at missing fact: {m.group(1)}")
        if self.facts_dir.exists():
            for path in sorted(self.facts_dir.glob("*.md")):
                if path.stem not in indexed:
                    problems.append(f"fact not in index: {path.stem}")
                fields = _frontmatter_fields(path.read_text(encoding="utf-8"))
                for required in ("source", "verified", "verify_by"):
                    if required not in fields:
                        problems.append(f"fact {path.stem} missing {required}")
        return problems

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
