#!/usr/bin/env python3
"""Generate the served HTML doc pages from the markdown in docs/.

The audience for harnessie.com includes people who will never open GitHub, so
every markdown doc in docs/ gets a styled, navigable HTML page on the site.
This is the generator: edit the markdown, run this script, commit source and
output together (the portfolio generated-surface rule). No dependencies; the
converter handles exactly the constructs these docs use (ATX headings, fenced
code, pipe tables, ul/ol lists, inline code/bold/links) and fails loudly on
anything else rather than guessing.

Usage: python3 scripts/build_docs_html.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = "https://harnessie.com"
GITHUB = "https://github.com/snapsynapse/harnessie/blob/main"

# source markdown -> (output name, nav label, meta description)
PAGES = {
    "quickstart.md": (
        "quickstart.html", "Quickstart",
        "The gentlest path into Harnessie: no git or shell fluency assumed, "
        "with a glossary and an honest Windows/WSL2 page."),
    "getting-started.md": (
        "getting-started.html", "Getting started",
        "The five-minute path: install Harnessie, prove it works offline, "
        "point it at a model, run a real job, and read the record it leaves."),
    "ladder.md": (
        "ladder.html", "Modes",
        "The ease-and-safety ladder: Harnessie's five run modes, from watching "
        "a mock harness to an agent-mediated run, each stating what is real and "
        "which risk you accept, with a human-only arbitration invariant across all."),
    "GUIDE.md": (
        "guide.html", "User guide",
        "The complete Harnessie user guide: concepts, CLI, workflow authoring, "
        "brain configuration, ownership, governance, and the halt-recovery table."),
    "brains.md": (
        "brains.html", "Brains",
        "The brain-agnostic receipt: the models actually run under the "
        "harness, each linked to the decision record that proves it."),
    "threat-model.md": (
        "threat-model.html", "Threat model",
        "A falsifiable comparison of Harnessie's structural properties against "
        "the failure modes of prevailing agent harnesses, each row citing the "
        "enforcing code and its test."),
    "compare.md": (
        "compare.html", "Compare",
        "Where Harnessie fits among AI agent frameworks and guardrail tools: "
        "a category map, an honest native-versus-build-it-yourself table, and "
        "when to reach for something else instead."),
    "ringer.md": (
        "ringer.html", "Ringer",
        "Harnessie and Ringer share one conviction and lean opposite ways: "
        "how they compose, wiring harnessie verify as a Ringer check, and "
        "the recipe for verifying agent-produced pull requests."),
}

# md link target -> served path, for links between the docs pages
LINK_MAP = {src: "/" + out for src, (out, _, _) in PAGES.items()}


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s]+", "-", text.strip())


def rewrite_href(href: str) -> str:
    """Map markdown link targets onto the served site or GitHub."""
    base, frag = (href.split("#", 1) + [""])[:2]
    frag = f"#{frag}" if frag else ""
    if not base:
        return href  # pure fragment
    if base.startswith(("http://", "https://", "mailto:")):
        return href
    name = base.lstrip("./")
    if name in LINK_MAP:
        return LINK_MAP[name] + frag
    if base.startswith("../"):
        return f"{GITHUB}/{base[3:]}{frag}"  # repo-root file
    return f"{GITHUB}/docs/{name}{frag}"     # docs file with no HTML page


def inline(text: str) -> str:
    """Inline markdown on already-HTML-escaped text: code, bold, links."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(f"<code>{part[1:-1]}</code>")
            continue
        part = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", part)
        part = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: f'<a href="{rewrite_href(m.group(2))}">{m.group(1)}</a>',
            part)
        out.append(part)
    return "".join(out)


def convert(md: str) -> tuple[str, str, list[tuple[int, str, str]]]:
    """Markdown -> (body html, page h1, [(level, slug, text) headings])."""
    lines = md.split("\n")
    out: list[str] = []
    headings: list[tuple[int, str, str]] = []
    title = ""
    i = 0
    para: list[str] = []

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            flush_para()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(html.escape(lines[i]))
                i += 1
            out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
            i += 1
            continue

        if re.match(r"^#{1,4} ", line):
            flush_para()
            level = len(line) - len(line.lstrip("#"))
            text = html.escape(line.lstrip("#").strip())
            if level == 1 and not title:
                title = text
                i += 1
                continue  # template renders the h1
            slug = slugify(text)
            headings.append((level, slug, text))
            out.append(f'<h{level} id="{slug}">{inline(text)}</h{level}>')
            i += 1
            continue

        if line.startswith("|"):
            flush_para()
            rows: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [
                [c.strip() for c in r.strip("|").split("|")]
                for r in rows
                if not re.match(r"^\|[\s:|-]+\|?$", r)
            ]
            if cells:
                thead = "".join(
                    f"<th>{inline(html.escape(c))}</th>" for c in cells[0])
                body_rows = "".join(
                    "<tr>" + "".join(
                        f"<td>{inline(html.escape(c))}</td>" for c in row)
                    + "</tr>"
                    for row in cells[1:])
                out.append(
                    '<div class="table-wrap"><table>'
                    f"<thead><tr>{thead}</tr></thead>"
                    f"<tbody>{body_rows}</tbody></table></div>")
            continue

        m = re.match(r"^(-|\d+\.) ", line)
        if m:
            flush_para()
            ordered = m.group(1) != "-"
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines):
                lm = re.match(r"^(-|\d+\.) (.*)$", lines[i])
                if lm and (lm.group(1) != "-") == ordered:
                    items.append(lm.group(2))
                    i += 1
                elif lines[i].startswith(("  ", "\t")) and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()  # continuation line
                    i += 1
                else:
                    break
            lis = "".join(
                f"<li>{inline(html.escape(item))}</li>" for item in items)
            out.append(f"<{tag}>{lis}</{tag}>")
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue

        para.append(html.escape(line.strip()))
        i += 1

    flush_para()
    return "\n".join(out), title, headings


# ---------------------------------------------------------------------------
# Presentation. STYLES and SCRIPT are passed to TEMPLATE.format() as VALUES,
# so their literal { } braces need no doubling; only the TEMPLATE string's own
# {placeholders} are substituted. Keep new CSS/JS here, not inline in TEMPLATE.
# ---------------------------------------------------------------------------

STYLES = """
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
      --bg: #f7f8fc; --bg-alt: #eceff4; --surface: #fff;
      --text: #17281a; --text-mid: #3a4a3d; --text-muted: #566458; --text-faint: #8a968b;
      --accent: #2f6b28; --accent-hover: #24571f; --border: #d6dce2; --border-soft: #e2e7ee;
      --code-bg: #16261a; --code-border: #24571f; --code-text: #e8ece4;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
    }
    html { scroll-behavior: smooth; }
    body { font-family: var(--font); color: var(--text); background: var(--bg); line-height: 1.65; -webkit-font-smoothing: antialiased; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { color: var(--accent-hover); text-decoration: underline; }
    .skip-link { position: absolute; left: -9999px; top: 0; background: var(--accent); color: var(--bg); padding: 0.5rem 1rem; z-index: 100; }
    .skip-link:focus { left: 0; }
    .container { max-width: 1180px; margin: 0 auto; padding: 0 1.5rem; }

    /* Nav: sticky, translucent, matches the landing page */
    nav.site { border-bottom: 1px solid var(--border); padding: 0.7rem 0; position: sticky; top: 0; background: rgba(247,248,252,0.9); backdrop-filter: saturate(1.4) blur(8px); -webkit-backdrop-filter: saturate(1.4) blur(8px); z-index: 40; }
    nav.site .container { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem 1rem; }
    nav.site .logo { display: flex; align-items: center; gap: 0.5rem; font-weight: 700; color: var(--text); font-size: 1.05rem; }
    nav.site .logo img { border-radius: 50%; object-fit: cover; border: 1px solid var(--border); }
    nav.site .links { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem 1.25rem; font-size: 0.9rem; }
    nav.site .links a { color: var(--text-muted); }
    nav.site .links a[aria-current="page"] { color: var(--accent); font-weight: 600; }
    nav.site .gh-star { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.35rem 0.75rem; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-alt); color: var(--text) !important; font-weight: 600; font-size: 0.8rem; }
    nav.site .gh-star:hover { border-color: var(--accent); text-decoration: none; }
    nav.site .gh-star svg { color: #eab308; }

    /* Two-column doc shell: sticky TOC rail + content */
    .doc-grid { max-width: 1180px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; display: grid; grid-template-columns: 230px 1fr; gap: 3.5rem; align-items: start; }
    .doc-grid.no-toc { grid-template-columns: 1fr; max-width: 820px; }
    .doc-grid.no-toc .doc-toc { display: none; }
    .doc-toc { position: sticky; top: 74px; align-self: start; max-height: calc(100vh - 96px); overflow-y: auto; border-right: 1px solid var(--border-soft); padding-right: 1.25rem; }
    .doc-toc .toc-title { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-faint); margin-bottom: 0.85rem; }
    .doc-toc .toc-nav { display: flex; flex-direction: column; gap: 0.1rem; }
    .doc-toc .toc-link { font-size: 0.86rem; color: var(--text-muted); padding: 0.32rem 0 0.32rem 0.8rem; border-left: 2px solid var(--border-soft); transition: color .15s, border-color .15s; }
    .doc-toc .toc-link:hover { color: var(--text); text-decoration: none; }
    .doc-toc .toc-link.active { color: var(--accent); font-weight: 600; border-left-color: var(--accent); }

    /* Content typography */
    .doc-content { min-width: 0; max-width: 760px; }
    .doc-content .crumb { font-size: 0.88rem; color: var(--text-faint); margin-bottom: 1.1rem; }
    .doc-content .crumb a { color: var(--text-faint); text-decoration: underline; text-decoration-color: var(--border); }
    .doc-content h1 { font-size: 2.2rem; line-height: 1.18; letter-spacing: -0.02em; font-weight: 800; margin-bottom: 0.9rem; }
    .doc-content h2 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.01em; margin: 2.5rem 0 0.9rem; scroll-margin-top: 84px; }
    .doc-content h3 { font-size: 1.15rem; font-weight: 600; margin: 1.7rem 0 0.5rem; scroll-margin-top: 84px; }
    .doc-content h4 { font-size: 1rem; font-weight: 600; margin: 1.3rem 0 0.4rem; scroll-margin-top: 84px; }
    .doc-content p { margin: 0 0 1rem; color: var(--text-mid); }
    .doc-content ul, .doc-content ol { margin: 0 0 1.1rem 1.3rem; color: var(--text-mid); }
    .doc-content li { margin-bottom: 0.4rem; }
    .doc-content strong { color: var(--text); }
    code { font-family: var(--mono); font-size: 0.85em; background: var(--bg-alt); border: 1px solid var(--border); border-radius: 4px; padding: 0.08em 0.35em; }
    pre { background: var(--code-bg); color: var(--code-text); border: 1px solid var(--code-border); border-radius: 10px; padding: 1.1rem 1.2rem; overflow-x: auto; margin: 0 0 1.2rem; font-size: 0.82rem; line-height: 1.6; }
    pre code { background: none; border: none; padding: 0; color: inherit; font-size: inherit; }
    .table-wrap { overflow-x: auto; margin: 0 0 1.2rem; border: 1px solid var(--border); border-radius: 10px; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
    th, td { padding: 0.6rem 0.85rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--border-soft); }
    th { background: var(--bg-alt); font-weight: 600; border-bottom: 1px solid var(--border); }
    tr:last-child td { border-bottom: none; }
    td code { color: var(--accent); background: none; border: none; padding: 0; white-space: nowrap; }

    /* Footer */
    footer { border-top: 1px solid var(--border); background: var(--bg-alt); padding: 2rem 0; font-size: 0.9rem; color: var(--text-muted); }
    footer .row { display: flex; flex-wrap: wrap; gap: 0.4rem 1.5rem; margin-bottom: 0.7rem; }
    footer .row a { color: var(--text-mid); }

    @media (max-width: 900px) {
      .doc-grid { grid-template-columns: 1fr; gap: 1.5rem; }
      .doc-toc { position: static; max-height: none; height: auto; border-right: none; border-bottom: 1px solid var(--border); padding-right: 0; padding-bottom: 1.25rem; }
      .doc-content h1 { font-size: 1.9rem; }
    }
"""

SCRIPT = """
<script>
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc-link'));
  if (!links.length) return;
  var map = {};
  links.forEach(function (l) { map[l.getAttribute('href').slice(1)] = l; });
  var heads = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  if (!heads.length) return;
  function setActive(id) { links.forEach(function (l) { l.classList.toggle('active', l === map[id]); }); }
  if (!('IntersectionObserver' in window)) { return; }
  var io = new IntersectionObserver(function (entries) {
    var vis = entries.filter(function (e) { return e.isIntersecting; })
      .sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top; });
    if (vis.length) setActive(vis[0].target.id);
  }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });
  heads.forEach(function (h) { io.observe(h); });
  setActive(heads[0].id);
})();
</script>
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
  <title>{title} &mdash; Harnessie</title>
  <meta name="description" content="{description}">
  <meta name="author" content="Sam Rogers">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
  <meta name="theme-color" content="#2f6b28">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="sitemap" type="application/xml" href="/sitemap.xml">
  <link rel="alternate" type="text/plain" href="https://harnessie.com/llms.txt" title="LLM-readable summary">
  <link rel="assistant-guide" href="https://harnessie.com/.well-known/assistant-guide.txt">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Harnessie">
  <meta property="og:title" content="{title} &mdash; Harnessie">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="https://harnessie.com/imgs/og.png">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} &mdash; Harnessie">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="https://harnessie.com/imgs/og.png">
  <style>{styles}</style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
<nav class="site" aria-label="Main navigation">
  <div class="container">
    <a href="/" class="logo" aria-label="Harnessie home">
      <img src="/imgs/harnessie-mark.png" width="28" height="28" alt="">
      <span>Harnessie</span>
    </a>
    <div class="links">
{navlinks}
      <a href="https://github.com/snapsynapse/harnessie" class="gh-star" target="_blank" rel="noopener" aria-label="Star snapsynapse/harnessie on GitHub"><svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg><span>GitHub</span></a>
    </div>
  </div>
</nav>
<div class="doc-grid{gridclass}">
  <aside class="doc-toc" aria-label="On this page">{toc}</aside>
  <main id="main-content" class="doc-content">
    <p class="crumb"><a href="/">harnessie.com</a> &nbsp;/&nbsp; docs &nbsp;/&nbsp; {label}</p>
    <h1>{h1}</h1>
{body}
  </main>
</div>
<footer>
  <div class="container">
    <div class="row">
{footerlinks}
    </div>
    <p>Harnessie &middot; <a href="https://github.com/snapsynapse/harnessie/blob/main/LICENSE" target="_blank" rel="noopener">Apache-2.0</a> &middot; A <a href="https://snapsynapse.com" target="_blank" rel="noopener">Snap Synapse</a> project. This page is generated from <a href="{srcurl}" target="_blank" rel="noopener">{srcname}</a>.</p>
  </div>
</footer>
{script}
</body>
</html>
"""


def build_toc(headings: list[tuple[int, str, str]]) -> str:
    """Sidebar 'On this page' rail from the top-level (h2) headings.

    Skips a 'Contents' heading since the rail replaces that inline list."""
    items = [
        (slug, text) for (level, slug, text) in headings
        if level == 2 and slug != "contents"
    ]
    if not items:
        return ""
    links = "".join(
        f'<a class="toc-link" href="#{slug}">{text}</a>' for slug, text in items)
    return f'<p class="toc-title">On this page</p><nav class="toc-nav">{links}</nav>'


# Remove the now-duplicate inline "Contents" heading + its list; the sidebar
# rail serves that role. Matches only a heading whose text is exactly Contents.
_CONTENTS_RE = re.compile(
    r'<h2 id="contents">Contents</h2>\s*<(ul|ol)>.*?</\1>', re.DOTALL)


def build() -> list[Path]:
    written = []
    for src, (out_name, label, description) in PAGES.items():
        md = (DOCS / src).read_text(encoding="utf-8")
        body, h1, headings = convert(md)
        toc = build_toc(headings)
        if toc:
            body = _CONTENTS_RE.sub("", body, count=1)
        navlinks = "\n".join(
            f'      <a href="/{o}"'
            + (' aria-current="page"' if o == out_name else "")
            + f">{lbl}</a>"
            for _, (o, lbl, _) in PAGES.items())
        footerlinks = "\n".join(
            f'      <a href="/{o}">{lbl}</a>'
            for _, (o, lbl, _) in PAGES.items())
        page = TEMPLATE.format(
            title=html.escape(label),
            description=html.escape(description),
            canonical=f"{SITE}/{out_name}",
            styles=STYLES,
            navlinks=navlinks,
            footerlinks=footerlinks,
            gridclass="" if toc else " no-toc",
            toc=toc,
            label=html.escape(label),
            h1=inline(html.escape(h1)) if h1 else html.escape(label),
            body=body,
            script=SCRIPT,
            srcurl=f"{GITHUB}/docs/{src}",
            srcname=f"docs/{src}",
        )
        target = DOCS / out_name
        target.write_text(page, encoding="utf-8")
        written.append(target)
    return written


if __name__ == "__main__":
    for path in build():
        print(f"wrote {path.relative_to(ROOT)}")
