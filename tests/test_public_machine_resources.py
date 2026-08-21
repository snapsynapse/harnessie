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


def test_agents_json_describes_only_shipped_local_surfaces():
    data = _json(AGENTS)
    assert data["product"]["version"] == _project_version()
    assert data["product"]["type"] == "local Python library and CLI"
    assert {item["id"] for item in data["capabilities"]} == {
        "review-checkout", "verify-claims", "validate-project", "run-workflow"}
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
    assert "matches the 1.0.0 guide hash" in guide_status["external_anchor"]
    assert guide_status["current_end_to_end_level"].startswith("Level 4 re-confirmed")
    assert capabilities["run-workflow"]["human_arbitration_required"] is True


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


def test_cli_manifest_is_complete_and_explicitly_not_hosted():
    data = _json(CLI_MANIFEST)
    assert data["package"]["version"] == _project_version()
    assert data["interface"]["kind"] == "local process interface"
    assert data["interface"]["hosted"] is False
    assert data["interface"]["network_service"] is False
    assert set(data["paths"]) == {
        "run", "resume", "report", "audit", "eval", "verify-manifest",
        "verify-inward-manifest", "approve-maiden", "verify", "init", "validate",
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
    for path in (
        "/agents.json", "/api/v1/index.json", "/changelog.json",
        "/.well-known/security.txt"):
        assert path in html
        assert f"https://harnessie.com{path}" in llms
    assert "Contact support" in html
    assert "Report a vulnerability" in html
    assert "GuideCheck Level 4" in html
    assert "DNS re-anchor pending" not in html
    assert "opt-in containment" in html.lower()
    assert "operator-trusted in-process code" in html
    assert "Homebrew also carries 1.0.0" in html
    assert "Harnessie's Golden Rule for agent work" in html
    assert "Read together." in html
    assert "Write only what you own." in html

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


def test_agent_file_ownership_claim_is_bounded_and_falsifiable():
    html = (DOCS / "agent-file-ownership.html").read_text(encoding="utf-8")
    assert "<h1>Harnessie&#x27;s Golden Rule for agent work</h1>" in html
    assert "Read together. Write only what you own." in html
    assert "does not claim that cross-agent overwrite prevention is a unique" in html
    assert "Collaborative lanes deliberately permit co-editing" in html
    assert "operator-trusted code" in html
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
