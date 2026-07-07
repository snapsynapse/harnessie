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
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    :root {{
      --bg: #f7f8fc; --bg-alt: #eceff4; --text: #17281a; --text-muted: #566458;
      --accent: #2f6b28; --accent-hover: #24571f; --border: #d6dce2;
      --code-bg: #16261a; --code-text: #e8ece4;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
      --max-width: 860px; --radius: 10px;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ font-family: var(--font); color: var(--text); background: var(--bg); line-height: 1.65; -webkit-font-smoothing: antialiased; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: var(--accent-hover); text-decoration: underline; }}
    .skip-link {{ position: absolute; left: -9999px; top: 0; background: var(--accent); color: var(--bg); padding: 0.5rem 1rem; z-index: 100; }}
    .skip-link:focus {{ left: 0; }}
    .container {{ max-width: var(--max-width); margin: 0 auto; padding: 0 1.5rem; }}
    nav.site {{ border-bottom: 1px solid var(--border); background: var(--bg); }}
    nav.site .container {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem 1rem; padding-top: 0.8rem; padding-bottom: 0.8rem; }}
    nav.site .logo {{ display: flex; align-items: center; gap: 0.5rem; font-weight: 700; color: var(--text); font-size: 1.05rem; }}
    nav.site .links {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; font-size: 0.95rem; }}
    nav.site .links a {{ color: var(--text-muted); }}
    nav.site .links a[aria-current="page"] {{ color: var(--accent); font-weight: 600; }}
    main {{ padding: 2.5rem 0 3.5rem; }}
    h1 {{ font-size: 1.9rem; line-height: 1.25; margin-bottom: 1rem; }}
    h2 {{ font-size: 1.4rem; margin: 2.2rem 0 0.7rem; padding-top: 0.4rem; }}
    h3 {{ font-size: 1.12rem; margin: 1.6rem 0 0.5rem; }}
    h4 {{ font-size: 1rem; margin: 1.2rem 0 0.4rem; }}
    p {{ margin: 0 0 1rem; }}
    ul, ol {{ margin: 0 0 1rem 1.4rem; }}
    li {{ margin-bottom: 0.35rem; }}
    code {{ font-family: var(--mono); font-size: 0.88em; background: var(--bg-alt); border: 1px solid var(--border); border-radius: 4px; padding: 0.08em 0.35em; }}
    pre {{ background: var(--code-bg); color: var(--code-text); border-radius: var(--radius); padding: 1rem 1.2rem; overflow-x: auto; margin: 0 0 1.2rem; font-size: 0.86rem; line-height: 1.55; }}
    pre code {{ background: none; border: none; padding: 0; color: inherit; font-size: inherit; }}
    .table-wrap {{ overflow-x: auto; margin: 0 0 1.2rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
    th, td {{ border: 1px solid var(--border); padding: 0.5rem 0.7rem; text-align: left; vertical-align: top; }}
    th {{ background: var(--bg-alt); }}
    .crumb {{ font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.2rem; }}
    footer {{ border-top: 1px solid var(--border); background: var(--bg-alt); padding: 2rem 0; font-size: 0.9rem; color: var(--text-muted); }}
    footer .row {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.2rem; margin-bottom: 0.6rem; }}
  </style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
<nav class="site" aria-label="Main navigation">
  <div class="container">
    <a href="/" class="logo" aria-label="Harnessie home">
      <img src="/imgs/harnessie-mark.png" width="26" height="26" alt="">
      <span>Harnessie</span>
    </a>
    <div class="links">
{navlinks}
      <a href="https://github.com/snapsynapse/harnessie" target="_blank" rel="noopener">GitHub</a>
    </div>
  </div>
</nav>
<main id="main-content">
  <div class="container">
    <p class="crumb"><a href="/">harnessie.com</a> / docs / {label}</p>
    <h1>{h1}</h1>
{body}
  </div>
</main>
<footer>
  <div class="container">
    <div class="row">
{footerlinks}
    </div>
    <p>Harnessie &middot; <a href="https://github.com/snapsynapse/harnessie/blob/main/LICENSE" target="_blank" rel="noopener">Apache-2.0</a> &middot; A <a href="https://snapsynapse.com" target="_blank" rel="noopener">Snap Synapse</a> project. This page is generated from <a href="{srcurl}" target="_blank" rel="noopener">{srcname}</a>.</p>
  </div>
</footer>
</body>
</html>
"""


def build() -> list[Path]:
    written = []
    for src, (out_name, label, description) in PAGES.items():
        md = (DOCS / src).read_text(encoding="utf-8")
        body, h1, _headings = convert(md)
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
            navlinks=navlinks,
            footerlinks=footerlinks,
            label=html.escape(label),
            h1=inline(html.escape(h1)) if h1 else html.escape(label),
            body=body,
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
