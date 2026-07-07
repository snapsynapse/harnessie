"""0.7 proof suite: bundle identity — a scorecard result pins model,
provider, endpoint, prompt version, parser version, and sampling, and any
component change requires a re-run. Change control, not drift monitoring.
No network anywhere in here.
"""

from harness.live_scorecard import (
    BundleIdentity,
    bundle_drift,
    bundle_identity,
    prompt_sha,
)
from harness.models.base import ModelSpec
from harness.verify import PARSER_VERSION


def scaffold_agents(root):
    (root / "agents" / "workers").mkdir(parents=True)
    (root / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan.")
    (root / "agents" / "workers" / "implementer.md").write_text("# Worker\nDo.")


def spec(**kw):
    base = dict(name="mid", provider="openai-compat", model_id="brain-a",
                base_url="http://localhost:11434/v1")
    base.update(kw)
    return ModelSpec(**base)


def test_bundle_identity_is_stable_and_complete(tmp_path):
    scaffold_agents(tmp_path)
    a = bundle_identity(tmp_path, spec())
    b = bundle_identity(tmp_path, spec())
    assert a == b and a.bundle_id == b.bundle_id
    assert a.model == "brain-a"
    assert a.provider == "openai-compat"
    assert a.endpoint == "http://localhost:11434/v1"
    assert a.parser_version == PARSER_VERSION
    assert a.sampling == "effort=low"
    assert len(a.bundle_id) == 12


def test_every_component_change_rotates_the_bundle(tmp_path):
    scaffold_agents(tmp_path)
    base = bundle_identity(tmp_path, spec())
    changed = [
        bundle_identity(tmp_path, spec(model_id="brain-b")),
        bundle_identity(tmp_path, spec(provider="anthropic", base_url=None)),
        bundle_identity(tmp_path, spec(base_url="https://other/v1")),
    ]
    # prompt edit rotates too
    (tmp_path / "agents" / "orchestrator.md").write_text("# Orchestrator\nPlan v2.")
    changed.append(bundle_identity(tmp_path, spec()))
    ids = {c.bundle_id for c in changed}
    assert base.bundle_id not in ids
    assert len(ids) == len(changed)          # each change is a distinct bundle


def test_prompt_sha_covers_the_whole_agents_tree(tmp_path):
    scaffold_agents(tmp_path)
    before = prompt_sha(tmp_path)
    (tmp_path / "agents" / "workers" / "reviewer.md").write_text("# Reviewer\n")
    assert prompt_sha(tmp_path) != before     # adding a role prompt rotates


def test_bundle_drift_names_the_changed_components(tmp_path):
    scaffold_agents(tmp_path)
    current = bundle_identity(tmp_path, spec())
    recorded = current.as_dict()
    assert bundle_drift(recorded, current) == []          # same bundle: no drift

    stale = dict(recorded, model="brain-old", parser_version="0")
    drift = bundle_drift(stale, current)
    assert len(drift) == 2
    assert any(d.startswith("model:") for d in drift)
    assert any(d.startswith("parser_version:") for d in drift)


def test_identity_dict_carries_bundle_id(tmp_path):
    scaffold_agents(tmp_path)
    d = bundle_identity(tmp_path, spec()).as_dict()
    assert set(d) == {"model", "provider", "endpoint", "prompt_sha",
                      "parser_version", "sampling", "bundle_id"}
