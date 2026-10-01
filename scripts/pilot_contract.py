"""Local dogfood contracts, deliberately outside the published runtime.

These limits are process/request bounds, not permission to use a provider.
The preparation CLI has no live execution command.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import threading

RECEIPT_VERSION = "harnessie-pilot/1"
CLAUDE_MODEL = "claude-fable-5-1"
QWEN_MODEL = "qwen3.8:latest"
QUESTION = ("Should Harnessie proceed with a bounded bid-record contract after its "
            "named exposure and budget gates, while leaving dispatch selection unchanged?")


class PilotRefusal(ValueError):
    """A stable failure category; never include provider output or secrets."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def digest_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class PilotLimits:
    max_calls: int = 0
    timeout_s: float = 120.0
    max_input_bytes: int = 256_000
    max_evidence_bytes: int = 256_000
    max_output_bytes: int = 128_000
    max_output_tokens: int = 4096

    def __post_init__(self):
        for name in ("max_calls", "max_input_bytes", "max_evidence_bytes",
                     "max_output_bytes", "max_output_tokens"):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name == "max_calls" else 1):
                raise PilotRefusal("invalid_limits")
        if (type(self.timeout_s) not in (int, float)
                or not math.isfinite(self.timeout_s) or self.timeout_s <= 0):
            raise PilotRefusal("invalid_limits")


class CallAllowance:
    """Reserve attempts before launch, including failed calls. No automatic retry."""

    def __init__(self, limits: PilotLimits | None = None):
        self.limits = limits or PilotLimits()
        self.used = 0
        self._lock = threading.Lock()

    def reserve(self) -> int:
        with self._lock:
            if self.used >= self.limits.max_calls:
                raise PilotRefusal("live_allowance_exhausted")
            self.used += 1
            return self.used
