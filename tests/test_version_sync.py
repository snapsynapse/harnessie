"""Version strings on hand-edited surfaces must match pyproject.

The generated docs pages get versions from their sources, but the landing
page and the GuideCheck trust pair are hand-edited prose. Every release
that bumped pyproject and missed one of these shipped a stale public
version claim (0.7.1 shipped with the landing page still saying 0.7.0).
This test turns that miss into a red suite, which the release checklist
runs before anything is tagged.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.M).group(1)


def test_landing_page_version_pills_match_pyproject():
    version = pyproject_version()
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    claimed = re.findall(r"\bv(\d+\.\d+\.\d+)\b", html)
    assert claimed, "landing page no longer carries a version pill; update this test"
    stale = [c for c in claimed if c != version]
    assert not stale, (
        f"docs/index.html claims version(s) {sorted(set(stale))} "
        f"but pyproject says {version}")


def test_assistant_guide_version_matches_pyproject():
    version = pyproject_version()
    guide = (ROOT / "assistant-guide.txt").read_text(encoding="utf-8")
    m = re.search(r"^guide-version: (.+)$", guide, re.M)
    assert m and m.group(1).strip() == version, (
        f"assistant-guide.txt guide-version {m and m.group(1)!r} != pyproject {version}")


def test_guide_manifest_version_and_release_url_match_pyproject():
    version = pyproject_version()
    manifest = (ROOT / "docs" / ".well-known" /
                "assistant-guide-manifest.txt").read_text(encoding="utf-8")
    m = re.search(r"^guide-version: (.+)$", manifest, re.M)
    assert m and m.group(1).strip() == version
    url = re.search(r"^immutable-release-url: (.+)$", manifest, re.M).group(1)
    assert url.endswith(f"/v{version}"), (
        f"guide manifest immutable-release-url {url!r} does not end with v{version}")
