"""Guide-artifact sync: the GuideCheck trust pair cannot drift silently.

assistant-guide.txt exists in four in-repo copies/derivations that must move
together: the repo-root guide, the byte-identical served copy under
docs/.well-known/, the sidecar provenance manifest's hash and byte count, and
the trust-bundle pins in docs/MANIFEST.yaml. The GuideCheck spec treats a
diverged pair as a forge/confusion vector (verifiers MUST fail on it), so
divergence here is a red test, not a judgment call. A fifth sync point, the
DNS TXT record at _assistant-guide.harnessie.com, lives at the registrar and
cannot be asserted offline; the canonical hash these tests compute is the
value that record must carry.
"""

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "assistant-guide.txt"
SERVED = ROOT / "docs" / ".well-known" / "assistant-guide.txt"
SIDECAR = ROOT / "docs" / ".well-known" / "assistant-guide-manifest.txt"
NOJEKYLL = ROOT / "docs" / ".nojekyll"
TRUST = ROOT / "docs" / "MANIFEST.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar_fields() -> dict:
    fields = {}
    for line in SIDECAR.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_served_copy_is_byte_identical():
    # A divergence between the root and .well-known copies is the exact forge
    # vector the GuideCheck spec names; verifiers MUST fail on it.
    assert GUIDE.read_bytes() == SERVED.read_bytes()


def test_sidecar_manifest_matches_guide_bytes():
    fields = _sidecar_fields()
    assert fields["guide-sha256"] == _sha256(GUIDE)
    assert int(fields["guide-bytes"]) == len(GUIDE.read_bytes())
    assert fields["guide-path"] == "/.well-known/assistant-guide.txt"


def test_trust_bundle_pins_all_three_guide_files():
    manifest = yaml.safe_load(TRUST.read_text(encoding="utf-8"))
    pins = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    for rel in (
        "assistant-guide.txt",
        "docs/.well-known/assistant-guide.txt",
        "docs/.well-known/assistant-guide-manifest.txt",
    ):
        assert rel in pins, f"{rel} missing from trust bundle"
        assert pins[rel] == _sha256(ROOT / rel), f"stale pin for {rel}"


def test_nojekyll_present_so_pages_serves_well_known():
    # Without .nojekyll, GitHub Pages' Jekyll build drops dot-directories and
    # the canonical /.well-known/ URL 404s.
    assert NOJEKYLL.exists()


def test_guide_satisfies_byte_profile_limits():
    # GuideCheck Level 2+ byte profile: ASCII printable + LF, no tabs/CR,
    # <= 8192 bytes, <= 120 bytes/line, <= 400 lines.
    data = GUIDE.read_bytes()
    assert len(data) <= 8192
    assert b"\r" not in data and b"\t" not in data
    assert all(b == 0x0A or 0x20 <= b <= 0x7E for b in data)
    lines = data.split(b"\n")
    assert len(lines) <= 400 + 1  # trailing newline yields one empty tail
    assert max(len(line) for line in lines) <= 120


def test_guide_metadata_names_the_canonical_pair():
    text = GUIDE.read_text(encoding="utf-8")
    block = re.search(
        r"\[assistant-guide-metadata\](.*?)\[/assistant-guide-metadata\]",
        text, re.S)
    assert block, "metadata block missing"
    meta = block.group(1)
    assert "canonical-url: https://harnessie.com/.well-known/assistant-guide.txt" in meta
    assert "manifest-url: https://harnessie.com/.well-known/assistant-guide-manifest.txt" in meta
    assert "source-path: /docs/.well-known/assistant-guide.txt" in meta
