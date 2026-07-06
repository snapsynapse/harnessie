"""Human-safe checksummed identifiers for run and request references.

Vendored from HardGuard25's Python implementation: a 25-character alphabet
with ambiguous letters removed, rejection-sampled generation, and a Mod-25
check digit.
"""

from __future__ import annotations

import re
import secrets

ALPHABET = "0123456789ACDFGHJKMNPRUWY"
ALPHABET_SET = frozenset(ALPHABET)
_CHAR_TO_INDEX = {char: idx for idx, char in enumerate(ALPHABET)}
_REGEX = re.compile(r"^[0-9ACDFGHJKMNPRUWY]+$")
_SEPARATOR_REGEX = re.compile(r"[-\s_.]+")


def generate(length: int, *, check_digit: bool = False) -> str:
    if length <= 0:
        raise ValueError("length must be greater than 0")
    result: list[str] = []
    while len(result) < length:
        byte_val = secrets.token_bytes(1)[0]
        if byte_val < 225:
            result.append(ALPHABET[byte_val % 25])
    code = "".join(result)
    if check_digit:
        code += check_digit_func(code)
    return code


def validate(input_str: str) -> bool:
    try:
        return bool(_REGEX.match(normalize(input_str)))
    except ValueError:
        return False


def normalize(input_str: str) -> str:
    if not isinstance(input_str, str):
        raise ValueError("input must be a string")
    normalized = _SEPARATOR_REGEX.sub("", input_str.strip()).upper()
    if not _REGEX.match(normalized):
        raise ValueError(f"invalid characters in input: {input_str}")
    return normalized


def check_digit(code: str) -> str:
    if not code:
        raise ValueError("code must not be empty")
    upper_code = code.upper()
    try:
        weighted_sum = sum(
            _CHAR_TO_INDEX[char] * (idx + 1)
            for idx, char in enumerate(upper_code)
        )
    except KeyError as e:
        raise ValueError(f"invalid character in code: {e}") from e
    return ALPHABET[weighted_sum % 25]


def verify_check_digit(code_with_check: str) -> bool:
    if not isinstance(code_with_check, str) or len(code_with_check) < 2:
        return False
    try:
        normalized = normalize(code_with_check)
        code = normalized[:-1]
        provided_check = normalized[-1]
        return provided_check == check_digit(code)
    except (ValueError, AttributeError):
        return False


check_digit_func = check_digit
