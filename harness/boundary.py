"""Containment boundary: deterministic PII strip/rehydrate at the provider
adapter (the mechanical half of the 0.7 sovereignty claim, adopted via
decisions/AIDR-0004).

PROVENANCE. Adapted from PAICE.work PBC's production PII service
(pii_service.py v1.0.0 at commit ab9b4109507022d2dca1954dd8481cef82f07d8c,
2026-04-01) and its locale pattern sets, under the PBC written grant
recorded in NOTICE: vendored under PAICE.work PBC's public Apache-2.0
license of July 9, 2026 for the identified snapshot (sole-director consent
on file with PBC records; same terms available to anyone).
Adaptations from the source: the third-party `regex` module becomes stdlib
`re` (unicode-property lookarounds converted to word-boundary forms), the
locale loader becomes an inlined multilingual pattern set, the
conversation-scoped manager becomes a run-scoped strip map with a
fail-closed resume lifecycle, and detection integrates with the harness's
existing secrets layer (harness/quarantine.py) instead of duplicating it.

The claim this module makes is exactly the coverage table (COVERAGE below),
in the same falsifiable-row style as docs/threat-model.md:
- structured PII: caught here, deterministically — regex over text, no model
  in the filter path, so the filter cannot be prompt-injected into leaking.
- secrets: caught here with a stricter lifecycle — never stored in any map,
  never rehydrated into any text; a secret in an egress payload always
  halts. There is no warn mode.
- unstructured free-text PII: NOT caught by this filter. Covered by
  contained routing (harness/cascade.py CONTAINED_TIERS): a task declaring a
  free-text-sensitive data class never egresses past the local/sovereign
  tier set. Never-egress, not imperfect filtering.

Every run artifact (workspace, phase reports, events, decision records)
carries placeholders only; rehydration happens solely at the operator
boundary, and per-tool rehydration is deny-all unless a grant names the
tool (the shipped approval-policy grammar: explicit deny wins, no match
denies closed).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .approval import ApprovalPolicy
from .quarantine import SECRET_PATTERNS

# Version of the boundary's detection contract. Part of a proven brain's
# bundle identity story: pattern-set changes are change control, so bump on
# ANY edit to PII_KINDS or the strip/rehydrate algorithm.
BOUNDARY_VERSION = "1"

# Placeholder shape: [KIND_N]. Same value, same placeholder, run-wide.
_PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]*_\d+\]")

# (kind, risk, contextual, pattern) — adapted multilingual set. Contextual
# kinds carry high false-positive risk without a keyword anchor and are
# skipped by default, matching the source service's production default.
PII_KINDS: tuple[tuple[str, str, bool, str], ...] = (
    ("EMAIL", "medium", False,
     r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    ("SSN", "critical", False,
     r"(?:(?:ssn|social\s*security(?:\s*number)?|ss#)[:\s#]*)(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b"
     r"|\b(\d{3}-\d{2}-\d{4})\b"),
    ("CREDIT_CARD", "critical", False,
     r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b"),
    ("PHONE", "medium", False,
     r"(?<!\d)(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    ("IP_ADDRESS", "low", False,
     r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
     r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    ("PK_CNIC", "high", False, r"(?<!\d)\d{5}-\d{7}-\d(?!\d)"),
    ("PK_MOBILE", "medium", False, r"(?<!\d)(?:\+92[-.]?|0)3\d{2}[-. ]?\d{7}(?!\d)"),
    ("IN_AADHAAR", "high", False, r"(?<!\d)\d{4}\s\d{4}\s\d{4}(?!\d)"),
    ("IN_PAN", "high", False, r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    ("ES_DNI_NIE", "high", False, r"\b[XYZ]?\d{7,8}[A-Z]\b"),
    ("MX_CURP", "high", False, r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d\b"),
    ("MX_RFC", "high", False, r"\b[A-Z]{3,4}\d{6}[0-9A-Z]{3}\b"),
    # Contextual: keyword-anchored to keep false positives down; group(1) is
    # the value. Skipped unless include_contextual=True.
    ("ROUTING_NUMBER", "high", True, r"(?:routing|aba|rtn)[:\s#]*(\d{9})\b"),
    ("DATE_OF_BIRTH", "medium", True,
     r"(?:dob|birth\s*date|born|birthday)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
    ("BANK_ACCOUNT", "high", True,
     r"(?:account|acct|iban)[:\s#]*(\d{8,20})\b"),
)

# The coverage table: the containment claim is exactly these rows.
COVERAGE: tuple[dict, ...] = (
    {"data_class": "structured PII", "mechanism": "boundary strip/rehydrate",
     "caught_by_filter": True,
     "detail": "PII_KINDS patterns; placeholders in every run artifact"},
    {"data_class": "secrets", "mechanism": "boundary egress halt + quarantine",
     "caught_by_filter": True,
     "detail": "never mapped, never rehydrated; egress with a secret always halts"},
    {"data_class": "unstructured free-text PII",
     "mechanism": "contained routing (never-egress)", "caught_by_filter": False,
     "detail": "cascade data_classes keep the task on CONTAINED_TIERS"},
)


class SecretEgressHalt(Exception):
    """A secret-shaped value reached an egress payload. Always a halt, never
    a warn. Carries kind labels only — never value fragments."""

    def __init__(self, kinds: list[str]) -> None:
        self.kinds = kinds
        super().__init__(
            f"secret egress halted: {', '.join(sorted(set(kinds)))} "
            "(kind labels only; values are never quoted)")


@dataclass
class StripResult:
    stripped: str
    mapping: dict[str, str]              # placeholder -> original value
    found: list[tuple[str, str]]         # (kind, placeholder) per new match

    @property
    def has_pii(self) -> bool:
        return bool(self.found)


class Boundary:
    """Deterministic strip/rehydrate. One instance per run; the mapping is
    cumulative so the same value gets the same placeholder run-wide (the
    source service's conversation-continuity property, run-scoped)."""

    def __init__(self, include_contextual: bool = False) -> None:
        self._compiled = [
            (kind, risk, re.compile(pattern, re.IGNORECASE))
            for kind, risk, contextual, pattern in PII_KINDS
            if include_contextual or not contextual
        ]

    def strip(self, text: str,
              mapping: dict[str, str] | None = None) -> StripResult:
        """Replace structured PII with stable placeholders before any egress.
        Overlap-safe positional replacement; per-kind counters continue from
        the mapping so placeholders never collide across calls."""
        mapping = dict(mapping or {})
        if not text:
            return StripResult("", mapping, [])
        reverse = {v: k for k, v in mapping.items()}

        spans: list[tuple[int, int, str, str]] = []   # start, end, kind, value
        taken: list[tuple[int, int]] = []
        for kind, _risk, pattern in self._compiled:
            for m in pattern.finditer(text):
                if m.lastindex:
                    groups = [i for i in range(1, m.lastindex + 1) if m.group(i)]
                    idx = groups[0] if groups else 0
                    value, start, end = m.group(idx), m.start(idx), m.end(idx)
                else:
                    value, start, end = m.group(), m.start(), m.end()
                if any(start < e and end > s for s, e in taken):
                    continue
                spans.append((start, end, kind, value))
                taken.append((start, end))

        counters: dict[str, int] = {}
        for placeholder in mapping:
            kind, _, num = placeholder[1:-1].rpartition("_")
            if kind and num.isdigit():
                counters[kind] = max(counters.get(kind, 0), int(num))

        found: list[tuple[str, str]] = []
        stripped = text
        for start, end, kind, value in sorted(spans, key=lambda s: s[0],
                                              reverse=True):
            placeholder = reverse.get(value)
            if placeholder is None:
                counters[kind] = counters.get(kind, 0) + 1
                placeholder = f"[{kind}_{counters[kind]}]"
                mapping[placeholder] = value
                reverse[value] = placeholder
            found.append((kind, placeholder))
            stripped = stripped[:start] + placeholder + stripped[end:]
        found.reverse()
        return StripResult(stripped, mapping, found)

    def guard_egress(self, text: str,
                     mapping: dict[str, str] | None = None) -> StripResult:
        """The egress gate: strip PII, then halt on any surviving secret.
        Secrets are deliberately checked AFTER the strip so a secret is never
        admitted to the mapping — there is nothing to rehydrate, ever."""
        result = self.strip(text, mapping)
        kinds = [m.lastgroup for m in SECRET_PATTERNS.finditer(result.stripped)
                 if m.lastgroup]
        if kinds:
            raise SecretEgressHalt(kinds)
        return result

    @staticmethod
    def rehydrate(text: str, mapping: dict[str, str]) -> str:
        """Operator-boundary only. Placeholders back to values; anything the
        mapping does not know stays a placeholder (fail closed, no guessing)."""
        if not text or not mapping:
            return text
        for placeholder, original in mapping.items():
            text = text.replace(placeholder, original)
        return text

    @staticmethod
    def unrehydrated(text: str) -> bool:
        return bool(_PLACEHOLDER.search(text))


@dataclass
class StripMap:
    """The strip map's lifecycle (designed, not deferred — the AIDR-0003
    round-one gap). An operator-boundary artifact stored OUTSIDE every run
    artifact: never in workspace/, runs/<id>/, reports, events, or decision
    records, which carry placeholders only. Secrets never enter it (their
    placeholders resolve from environment variables at the tool boundary, so
    there is no secret value to persist). On resume the map is reloaded
    before any rehydration; a missing or corrupt map fails closed —
    placeholders stay placeholders, the report names the degradation, and
    the harness never guess-rehydrates."""

    run_id: str
    directory: Path
    mapping: dict[str, str] = field(default_factory=dict)
    status: str = "new"                  # "new" | "loaded" | "missing" | "corrupt"

    @property
    def path(self) -> Path:
        return self.directory / f"{self.run_id}.json"

    @property
    def rehydration_available(self) -> bool:
        return self.status in ("new", "loaded")

    @classmethod
    def open(cls, root: Path, run_id: str,
             expect_existing: bool = False) -> "StripMap":
        directory = root / ".boundary"
        path = directory / f"{run_id}.json"
        if not path.exists():
            status = "missing" if expect_existing else "new"
            return cls(run_id=run_id, directory=directory, status=status)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mapping = data["mapping"]
            if not isinstance(mapping, dict) or not all(
                    isinstance(k, str) and isinstance(v, str)
                    for k, v in mapping.items()):
                raise ValueError("mapping shape")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
            # fail closed: a corrupt map disables rehydration; it never
            # guesses, and it never destroys the corrupt file (evidence)
            return cls(run_id=run_id, directory=directory, status="corrupt")
        return cls(run_id=run_id, directory=directory, mapping=mapping,
                   status="loaded")

    def save(self) -> None:
        """Atomic write, owner-only permissions. Refuses to save over a
        corrupt predecessor: that state needs the operator, not a writer."""
        if self.status == "corrupt":
            raise RuntimeError(
                f"strip map for run {self.run_id} is corrupt; refusing to "
                "overwrite it — inspect or remove it, then resume")
        self.directory.mkdir(mode=0o700, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": BOUNDARY_VERSION,
                                   "run_id": self.run_id,
                                   "mapping": self.mapping}, indent=1),
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)
        self.status = "loaded"

    def degradation_notice(self) -> str | None:
        if self.rehydration_available:
            return None
        return (f"strip map for run {self.run_id} is {self.status}: "
                "rehydration is disabled fail-closed; placeholders remain "
                "placeholders in all output. Inspect "
                f"{self.path} (or accept placeholder output), then resume")


class RehydrationGrants:
    """Per-tool rehydration grants on the shipped approval-policy grammar:
    allow/deny by tool and optional phase, explicit deny wins, no match
    denies closed. Starts deny-all: absent file or empty policy grants
    nothing."""

    def __init__(self, policy: ApprovalPolicy | None) -> None:
        self._policy = policy

    @classmethod
    def load(cls, path: Path) -> "RehydrationGrants":
        if not path.exists():
            return cls(None)              # deny-all
        return cls(ApprovalPolicy.load(path))

    def allows(self, tool: str, phase: str) -> bool:
        if self._policy is None:
            return False
        return self._policy.decide(phase, tool, {}) is True

    def rehydrate_for_tool(self, tool: str, phase: str, text: str,
                           strip_map: StripMap) -> str:
        """Rehydrate only under an explicit grant AND an intact map. Every
        other combination returns the text unchanged (placeholders are the
        safe default everywhere)."""
        if not self.allows(tool, phase):
            return text
        if not strip_map.rehydration_available:
            return text
        return Boundary.rehydrate(text, strip_map.mapping)


def scrub_tool_result(boundary: Boundary, text: str,
                      mapping: dict[str, str] | None = None) -> StripResult:
    """Tool results are scrubbed before they enter context, closing the loop
    where a worker reads a file whose PII would otherwise ride the next model
    call out. Secrets in tool results are already redacted by the quarantine
    layer at the tool boundary; this adds the PII strip on the same edge."""
    return boundary.strip(text, mapping)
