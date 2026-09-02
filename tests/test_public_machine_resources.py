import hashlib
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
AGENTS = DOCS / "agents.json"
CHANGELOG = DOCS / "changelog.json"
CLI_MANIFEST = DOCS / "api" / "v1" / "index.json"
SECURITY = DOCS / ".well-known" / "security.txt"
TRUST = DOCS / "MANIFEST.yaml"
GUIDECHECK_RECEIPT = (
    ROOT / "audits" / "guidecheck-live-result-2026-08-21-v1.1.0.json")


def _project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _url_strings(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _url_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _url_strings(nested)
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        yield value


def _security_fields() -> dict[str, str]:
    fields = {}
    for line in SECURITY.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        fields[key] = value.strip()
    return fields


def test_agents_json_describes_released_core_and_downstream_boundaries():
    data = _json(AGENTS)
    assert data["product"]["version"] == _project_version()
    assert data["product"]["type"] == "local Python library and CLI"
    assert data["release_context"]["stable_release"] == _project_version()
    assert data["release_context"]["unreleased_changes_since_stable"] is True
    assert {item["id"] for item in data["capabilities"]} == {
        "review-checkout", "verify-claims", "validate-project",
        "inspect-ownership", "run-workflow"}
    assert data["boundaries"] == {
        "hosted_api": False,
        "hosted_service": False,
        "mcp_server": False,
        "autonomous_remote_agent": False,
        "note": data["boundaries"]["note"],
    }
    capabilities = {item["id"]: item for item in data["capabilities"]}
    assert capabilities["review-checkout"]["human_approval_required"] is True
    guide_status = capabilities["review-checkout"]["integrity_status"]
    assert "1.2.0 DNS TXT" in guide_status["external_anchor"]
    assert guide_status["current_end_to_end_level"].startswith(
        "Pending external re-verification")
    assert guide_status["historical_receipt"].endswith(
        "/audits/guidecheck-live-result-2026-08-21-v1.1.0.json")
    assert capabilities["inspect-ownership"]["side_effects"] == "read-only"
    assert capabilities["run-workflow"]["human_arbitration_required"] is True


def test_current_guidecheck_receipt_earns_the_claimed_level():
    receipt = _json(GUIDECHECK_RECEIPT)
    assert receipt["outcome"] == "evaluated"
    assert receipt["guide"] == {
        "bytes": 7947,
        "sha256": (
            "f7d45f62f2941f5541d1342be0fc037c1ef7fc3e06f44ad39cf94a5b50e5080d"),
        "achieved_level": 4,
        "level5_ready": True,
    }
    assert receipt["summary"]["blocking_findings"] == 0
    anchors = {
        item["channel"]: item for item in receipt["cross_channel_anchors"]}
    for channel in ("dns-txt", "repository-file"):
        assert anchors[channel]["status"] == "present-matches"
        assert anchors[channel]["observed_sha256"] == (
            receipt["guide"]["sha256"])


def test_machine_resource_urls_follow_public_url_policy():
    for path in (AGENTS, CLI_MANIFEST, CHANGELOG):
        for url in _url_strings(_json(path)):
            assert url.startswith("https://"), url
            assert "://www." not in url, url


def test_machine_changelog_tracks_the_packaged_release():
    data = _json(CHANGELOG)
    version = _project_version()
    assert data["current"]["version"] == version
    versions = [entry["version"] for entry in data["history"]]
    assert versions[0] == version
    assert len(versions) == len(set(versions))
    assert data["current"]["release"].endswith(f"/v{version}")
    assert data["unreleased"]["status"] == "active"
    assert data["unreleased"]["summary"] == (
        "Trusted-publishing recovery maintenance and exact 1.2.0 "
        "release-closeout evidence.")


def test_public_verifier_copy_describes_the_released_evidence_contract():
    surfaces = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "docs/GUIDE.md": (DOCS / "GUIDE.md").read_text(encoding="utf-8"),
        "docs/ringer.md": (DOCS / "ringer.md").read_text(encoding="utf-8"),
        "docs/index.html": (DOCS / "index.html").read_text(encoding="utf-8"),
        "docs/llms.txt": (DOCS / "llms.txt").read_text(encoding="utf-8"),
    }
    for name, text in surfaces.items():
        assert "1.2.0" in text, name
        assert "evidence bundle" in text.lower() or "evidence-bound" in text.lower(), name

    assert "Harnessie 1.2.0 accepts raw criteria or a v1 evidence bundle" in (
        surfaces["README.md"])
    assert "Evidence bundles are the stronger 1.2.0 adoption contract" in (
        surfaces["docs/GUIDE.md"])
    assert "Harnessie 1.2.0 accepts raw criteria or evidence bundles" in (
        surfaces["docs/index.html"])


def test_cli_manifest_is_complete_and_explicitly_not_hosted():
    data = _json(CLI_MANIFEST)
    assert data["package"]["version"] == _project_version()
    assert data["interface"]["kind"] == "local process interface"
    assert data["interface"]["hosted"] is False
    assert data["interface"]["network_service"] is False
    assert data["release_context"] == {
        "stable_release": _project_version(),
        "describes": "released 1.2.0 core",
        "unreleased_changes_since_stable": True,
        "note": data["release_context"]["note"],
    }
    assert set(data["paths"]) == {
        "run", "resume", "report", "audit", "eval", "verify-manifest",
        "verify-inward-manifest", "approve-maiden", "verify", "init", "validate",
        "ownership",
    }
    for command, contract in data["paths"].items():
        assert contract["synopsis"].startswith(f"harnessie {command}")
        assert contract["purpose"]
        assert contract["side_effects"]
        help_result = subprocess.run(
            [sys.executable, "-m", "harness.cli", command, "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        live_options = set(re.findall(r"--[a-z][a-z-]*", help_result.stdout))
        live_options.discard("--help")
        documented_options = set(
            re.findall(r"--[a-z][a-z-]*", contract["synopsis"]))
        assert documented_options == live_options, command
    assert "status" not in data["paths"]["ownership"]


def test_security_txt_has_a_current_rfc9116_contact_contract():
    fields = _security_fields()
    assert fields["Contact"] == (
        "https://github.com/snapsynapse/harnessie/security/advisories/new")
    assert fields["Canonical"] == (
        "https://harnessie.com/.well-known/security.txt")
    assert fields["Policy"].endswith("/blob/main/SECURITY.md")
    expires = datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
    remaining = expires - datetime.now(UTC)
    assert timedelta(days=30) < remaining <= timedelta(days=366)


def test_public_discovery_links_expose_support_and_machine_resources():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    llms = (DOCS / "llms.txt").read_text(encoding="utf-8")
    assert (DOCS / "llm.txt").read_bytes() == (DOCS / "llms.txt").read_bytes()
    for path in (
        "/agents.json", "/api/v1/index.json", "/changelog.json",
        "/.well-known/security.txt"):
        assert path in html
        assert f"https://harnessie.com{path}" in llms
    assert "Contact support" in html
    assert "Report a vulnerability" in html
    assert "1.1 guide: GuideCheck Level 4" in html
    assert "historical hash independently pinned" in html
    assert "historical evidence" in html
    assert "opt-in containment" in html.lower()
    assert "operator-trusted in-process code" in html
    assert "Homebrew is a separately propagated downstream" in html
    assert "Harnessie's Golden Rule for agent work" in html
    assert "Read together." in html
    assert "Write only what you own." in html
    assert "https://anthropic.com/research/multiagent-systems" in html
    assert "coordination failures, collusion, and sabotage" in html

    sitemap = ET.parse(DOCS / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {
        item.text for item in sitemap.findall("sm:url/sm:loc", namespace)
    }
    for page in (
        "quickstart.html", "getting-started.html", "ladder.html", "guide.html",
        "agent-file-ownership.html", "brains.html", "threat-model.html",
        "compare.html", "ringer.html",
    ):
        assert f"https://harnessie.com/{page}" in locations

    assert "https://harnessie.com/agent-file-ownership.html" in llms
    agents = _json(AGENTS)
    assert agents["discovery"]["agent_file_ownership"] == (
        "https://harnessie.com/agent-file-ownership.html")
    assert agents["discovery"]["ringer"] == "https://harnessie.com/ringer.html"
    assert "https://harnessie.com/ringer.html" in llms
    assert 'href="/ringer.html"' in html

    for page in ("quickstart.html", "guide.html", "ringer.html"):
        generated = (DOCS / page).read_text(encoding="utf-8")
        assert 'href="/ringer.html"' in generated


def test_homepage_preserves_lighthouse_accessibility_repairs():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Star on GitHub"' in html
    assert '<h4>It scopes first</h4>' not in html
    for heading in (
        "It scopes first", "It checks its work", "You have the final say",
        "It keeps the receipts",
    ):
        assert f"<h3>{heading}</h3>" in html
    assert "p a { text-decoration: underline;" in html
    assert ".foot-col .head" in html and "color: var(--text-muted);" in html
    assert ".foot-note" in html and "font-size: 0.78rem; color: var(--text-muted);" in html

    generated = (DOCS / "ringer.html").read_text(encoding="utf-8")
    assert ".doc-toc .toc-title" in generated
    assert "color: var(--text-muted);" in generated
    assert ".doc-content p a, .doc-content li a, footer p a" in generated
    assert "text-decoration: underline; text-underline-offset: 0.14em;" in generated


def test_agent_file_ownership_claim_is_bounded_and_falsifiable():
    html = (DOCS / "agent-file-ownership.html").read_text(encoding="utf-8")
    assert "<h1>Harnessie&#x27;s Golden Rule for agent work</h1>" in html
    assert "Read together. Write only what you own." in html
    assert "does not claim that cross-agent overwrite prevention is a unique" in html
    assert "Collaborative lanes deliberately permit co-editing" in html
    assert "operator-trusted code" in html
    assert "Shipped in Harnessie 1.1.0" in html
    assert "https://anthropic.com/research/multiagent-systems" in html
    assert "cooperation prompts as guidance, not as a control" in html
    for proof in (
        "harness/ownership.py", "harness/sandbox.py", "tests/test_ownership.py",
        "tests/test_runner.py", "tests/test_sandbox.py",
    ):
        assert proof in html
    for target in (
        "https://github.com/snapsynapse/harnessie/blob/main/harness/ownership.py",
        "https://github.com/snapsynapse/harnessie/blob/main/harness/sandbox.py",
        "https://github.com/snapsynapse/harnessie/blob/main/OWNERSHIP.yaml",
    ):
        assert f'href="{target}"' in html


def test_trust_bundle_pins_all_machine_resources():
    manifest = yaml.safe_load(TRUST.read_text(encoding="utf-8"))
    pins = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    for rel in (
        "docs/agents.json",
        "docs/api/v1/index.json",
        "docs/changelog.json",
        "docs/.well-known/security.txt",
    ):
        assert rel in pins
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert pins[rel] == digest
