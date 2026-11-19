"""SEC-20261118-008: a recognized secret is refused against the ORIGINAL
text, before any PII replacement, so an overlapping PII pattern can never
erase the secret's shape and carry it into a rehydratable strip map.

Every value here is synthetic. Each overlap case is a credential whose tail
also matches a structured-PII pattern; the matrix crosses every secret kind
the quarantine layer detects with the PII shapes that can overlap it, at
several offsets.
"""

import pytest

from harness.boundary import Boundary, SecretEgressHalt, StripMap
from harness.quarantine import SECRET_KINDS, find_secrets

# (kind, synthetic credential whose characters overlap a PII pattern)
OVERLAPS = [
    ("perplexity_key", "pplx-" + "SYNTHETICAB" + "2025550187"),          # phone
    ("perplexity_key", "pplx-" + "syntheticfakevaluezz" + "x@example.com"),  # email
    ("anthropic_key", "sk-ant-ABCD-" + "2222333344445555"),             # card
    ("anthropic_key", "sk-ant-SYNTHETICVAL-" + "2025550187"),           # phone
    ("anthropic_key", "sk-ant-" + "synthetic-fake-value-zz" + "@example.com"),  # email
    ("openai_style_key", "sk-" + "SYNTHETICFAKEVALUE0000AB" + "2025550187"),  # phone
    ("openai_style_key", "sk-" + "syntheticfakevalue" * 2 + "@example.com"),  # email
    ("github_token", "ghp_" + "SYNTHETICFAKEVALUEAB" + "2025550187"),   # phone
    ("github_pat", "github_pat_" + "SYNTHETIC_FAKE_VALUEAB" + "2025550187"),  # phone
    ("aws_access_key", "AKIA" + "SYNTHE" + "2025550187"),               # phone
    ("slack_token", "xoxb-" + "202-555-0187"),                          # phone
    ("slack_token", "xoxb-" + "4111-1111-1111-1111"),                   # card
    ("slack_token", "xoxb-" + "synthetic-fake" + "@example.com"),       # email
]

OFFSETS = [
    ("start", "{secret} trailing words"),
    ("middle", "leading words {secret} trailing words"),
    ("end", "leading words {secret}"),
]


def _cases():
    for kind, secret in OVERLAPS:
        for where, template in OFFSETS:
            yield pytest.param(kind, secret, template,
                               id=f"{kind}-{secret[-12:]}-{where}")


def test_matrix_covers_every_detected_secret_kind():
    assert {k for k, _ in OVERLAPS} == {k for k, _ in SECRET_KINDS}


@pytest.mark.parametrize("kind,secret,template", list(_cases()))
def test_overlapping_secret_halts_and_never_enters_mapping(kind, secret, template):
    text = template.format(secret=secret)
    assert kind in find_secrets(text)          # recognized before any strip
    with pytest.raises(SecretEgressHalt) as exc:
        Boundary().guard_egress(text)
    assert kind in exc.value.kinds
    assert secret not in str(exc.value)
    # The strip on its own never maps any fragment of the credential.
    stripped = Boundary().strip(text)
    assert all(v not in secret and secret not in v
               for v in stripped.mapping.values())
    assert secret in stripped.stripped         # left whole for the halt layer


@pytest.mark.parametrize("kind,secret", OVERLAPS,
                         ids=[f"{k}-{s[-12:]}" for k, s in OVERLAPS])
def test_secret_beside_separate_pii_halts_and_maps_only_the_pii(kind, secret):
    text = f"mail casey@example.com about {secret} today"
    with pytest.raises(SecretEgressHalt) as exc:
        Boundary().guard_egress(text)
    assert kind in exc.value.kinds
    stripped = Boundary().strip(text)
    assert "casey@example.com" in stripped.mapping.values()
    assert all(v not in secret and secret not in v
               for v in stripped.mapping.values())


def test_incoming_mapping_with_secret_material_fails_closed():
    poisoned = {"[CREDIT_CARD_1]": "sk-ant-ABCD-2222333344445555"}
    with pytest.raises(SecretEgressHalt) as exc:
        Boundary().guard_egress("ordinary text [CREDIT_CARD_1]", poisoned)
    assert "anthropic_key" in exc.value.kinds


def test_rehydrate_never_reconstructs_secret_material():
    poisoned = {"[CREDIT_CARD_1]": "sk-ant-ABCD-2222333344445555",
                "[EMAIL_1]": "casey@example.com"}
    out = Boundary.rehydrate("sk-ant-ABCD-[CREDIT_CARD_1] and [EMAIL_1]", poisoned)
    assert "2222333344445555" not in out
    assert "[CREDIT_CARD_1]" in out
    assert "casey@example.com" in out


def test_strip_map_round_trip_after_overlap_holds_no_secret(tmp_path):
    m = StripMap.open(tmp_path, "r")
    b = Boundary()
    with pytest.raises(SecretEgressHalt):
        r = b.guard_egress("pay with sk-ant-ABCD-2222333344445555", m.mapping)
        m.mapping = r.mapping
    assert m.mapping == {}


# Positive controls: PII-only and nonsecret numeric payloads keep 0.7 behavior.

@pytest.mark.parametrize("text,kind,value", [
    ("reach casey@example.com today", "EMAIL", "casey@example.com"),
    ("call 415-555-0187 today", "PHONE", "415-555-0187"),
    ("card 4111 1111 1111 1111 on file", "CREDIT_CARD", "4111 1111 1111 1111"),
    ("ssn: 078-05-1120 on file", "SSN", "078-05-1120"),
])
def test_pii_only_payloads_still_strip_and_rehydrate(text, kind, value):
    r = Boundary().guard_egress(text)
    assert value not in r.stripped
    assert value in r.mapping.values()
    assert any(k == kind for k, _ in r.found)
    assert Boundary.rehydrate(r.stripped, r.mapping) == text


@pytest.mark.parametrize("text", [
    "the docs mention the sk-ant- prefix and pplx- keys",
    "order 2222333344445555 shipped",
    "xoxb- tokens are short-lived; ghp_ too",
    "sk-short-123 is not a credential",
])
def test_nonsecret_text_passes_without_halt(text):
    r = Boundary().guard_egress(text)
    assert Boundary.rehydrate(r.stripped, r.mapping) == text
