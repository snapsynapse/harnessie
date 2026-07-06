import re

from harness.ids import ALPHABET_SET, generate, validate, verify_check_digit
from harness.state import new_run_id


def test_generate_uses_human_safe_alphabet_and_check_digit():
    code = generate(5, check_digit=True)
    assert len(code) == 6
    assert set(code) <= ALPHABET_SET
    assert validate(code)
    assert verify_check_digit(code)


def test_run_id_keeps_timestamp_prefix_with_checksummed_suffix():
    run_id = new_run_id()
    assert re.match(r"^\d{8}-\d{6}-[0-9ACDFGHJKMNPRUWY]{6}$", run_id)
    assert verify_check_digit(run_id.rsplit("-", 1)[1])
