"""Cascade policy model: declared ladders, contained tiers, reserved classes.

Everything here fails closed: unknown keys, unknown reasons, exposed tiers in
contained ladders, and unconfigured tiers are load-time refusals, never
runtime surprises.
"""

import textwrap

import pytest

from harness.cascade import (
    CascadeConfig,
    CascadePolicy,
    load_cascade_config,
    validate_against_tiers,
)


def make_policy(**kw):
    base = dict(name="p", ladder=("local", "mid", "frontier"))
    base.update(kw)
    return CascadePolicy(**base)


def test_policy_defaults_and_ceiling():
    p = make_policy()
    assert p.escalate_on == ("gate_fail",)
    assert p.on_exhaust == "defer"
    assert not p.contained
    assert p.climb_ceiling == 2          # ladder-bounded when max_climb unset


def test_policy_validation_fails_closed():
    with pytest.raises(ValueError, match="ladder is empty"):
        make_policy(ladder=())
    with pytest.raises(ValueError, match="repeats a tier"):
        make_policy(ladder=("local", "local"))
    with pytest.raises(ValueError, match="unknown escalate_on"):
        make_policy(escalate_on=("vibes",))
    with pytest.raises(ValueError, match="escalate_on is empty"):
        make_policy(escalate_on=())
    with pytest.raises(ValueError, match="never silent"):
        make_policy(on_exhaust="continue")
    with pytest.raises(ValueError, match="max_climb 7 out of range"):
        make_policy(max_climb=7)


def test_contained_ladder_refuses_exposed_tiers():
    with pytest.raises(ValueError, match="exposed tier"):
        make_policy(ladder=("local", "frontier"), contained=True)
    ok = make_policy(ladder=("local", "sovereign"), contained=True)
    assert ok.contained


def test_next_tier_climbs_holds_and_exhausts():
    p = make_policy(escalate_on=("gate_fail", "schema_fail"), max_climb=1)

    climb = p.next_tier("local", climbs_used=0, reason="gate_fail")
    assert (climb.action, climb.tier) == ("climb", "mid")

    hold = p.next_tier("local", climbs_used=0, reason="refusal")
    assert hold.action == "hold"         # refusal moves sideways, not up

    capped = p.next_tier("mid", climbs_used=1, reason="gate_fail")
    assert capped.action == "exhausted"
    assert "max_climb 1" in capped.reason and "defer" in capped.reason

    top = make_policy(max_climb=-1).next_tier("frontier", 0, "gate_fail")
    assert top.action == "exhausted"
    assert "top of ladder" in top.reason

    with pytest.raises(ValueError, match="not on ladder"):
        p.next_tier("sovereign", 0, "gate_fail")


def test_load_missing_file_is_empty_opt_in(tmp_path):
    cfg = load_cascade_config(tmp_path / "cascade.yaml")
    assert cfg.policies == {} and cfg.reserved == ()
    assert not cfg.is_reserved("anything")


def test_load_parses_policies_and_reserved(tmp_path):
    f = tmp_path / "cascade.yaml"
    f.write_text(textwrap.dedent("""
        policies:
          cheap-first:
            ladder: [local, mid]
            escalate_on: [gate_fail, schema_fail]
            max_climb: 1
            on_exhaust: defer
          contained-local:
            ladder: [local, sovereign]
            data_classes: [freeform_sensitive]
            contained: true
        reserved:
          - arbitration
    """))
    cfg = load_cascade_config(f)
    assert cfg.policy("cheap-first").ladder == ("local", "mid")
    assert cfg.policy("contained-local").contained
    assert cfg.policy("contained-local").data_classes == ("freeform_sensitive",)
    assert cfg.is_reserved("arbitration")
    with pytest.raises(ValueError, match="unknown cascade policy"):
        cfg.policy("nope")


def test_load_refuses_unknown_keys_and_shapes(tmp_path):
    f = tmp_path / "cascade.yaml"
    f.write_text("policies:\n  p:\n    ladder: [local]\n    max_clib: 2\n")
    with pytest.raises(ValueError, match="unknown key.*max_clib"):
        load_cascade_config(f)
    f.write_text("policies:\n  p:\n    escalate_on: [gate_fail]\n")
    with pytest.raises(ValueError, match="missing ladder"):
        load_cascade_config(f)
    f.write_text("surprise: true\n")
    with pytest.raises(ValueError, match="unknown top-level"):
        load_cascade_config(f)
    f.write_text("reserved: arbitration\n")
    with pytest.raises(ValueError, match="reserved must be a list"):
        load_cascade_config(f)


def test_validate_against_tiers_names_the_missing_tier():
    cfg = CascadeConfig(policies={
        "p": CascadePolicy(name="p", ladder=("local", "sovereign"))})
    with pytest.raises(ValueError, match=r"unconfigured tier\(s\) \['sovereign'\]"):
        validate_against_tiers(cfg, {"local": object(), "mid": object()})
    validate_against_tiers(cfg, {"local": 1, "sovereign": 1})   # no raise


def test_shipped_cascade_config_defaults_closed():
    # the repo ships no active policies (opt-in stays opt-in) and reserves
    # arbitration — the human-only rule as config, not convention
    cfg = load_cascade_config("config/cascade.yaml")
    assert cfg.policies == {}
    assert cfg.is_reserved("arbitration")
