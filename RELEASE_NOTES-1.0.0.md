# Harnessie 1.0.0: extensibility earned

Harnessie 1.0.0 freezes the authoring contract, closes the interpreter ownership gap, and admits installed tool extensions through one explicit trust boundary.

## Highlights

- Six strict Draft 2020-12 authoring schemas cover models, cascade, boundary, approval policy, ownership, and workflows. Runtime startup and `harnessie validate` use the same fail-closed contract.
- Worker shell calls, deterministic checks, and verifier commands receive agent-specific read-only ownership overlays. Unsupported nested profiles refuse instead of running unconfined.
- Installed tool plugins use only the `harnessie.tools.v1` entry-point group and never auto-load. Explicit `--plugin NAME` admission validates and namespaces tools, applies registry policy, records loader-supplied provenance, and pins exact receipts across resume.
- Anthropic and OpenAI-compatible adapters now normalize malformed provider responses into non-echoing error turns. Adversarial rebuttal agents receive complete peer positions without self-position leakage.

## Verification

- 413 tests passed with 1 environment-dependent skip.
- Deterministic eval scorecard: 50/50.
- Nine shipped authoring documents validated against schema v1.
- Outward trust manifest: 19 files. Inward manifest: 15 files.
- Ecosystem manifest and 8 generated documentation pages verified.
- Wheel and source distribution passed `twine check`, structural inspection, private-surface scrubbing, and fresh-install smoke.
- Adversarial plugin cases covered explicit-only admission, zero-selection non-discovery, malformed declarations, invalid parameter schemas, duplicate names, role denial, provenance attribution, and resume drift. No bypass or legitimate-corpus regression remained in the complete suite.
- Live provider scorecards were not run because the release changes harness mechanics and package contracts, not provider behavior. The deterministic mock-brain and real OS sandbox paths exercised the affected boundaries.

## Trust boundaries and residuals

- Plugin implementations run in process as operator-trusted code. Registry mediation is not a sandbox and does not prove declared effects. Untrusted plugins remain unsupported pending a separately versioned out-of-process design.
- Docker remains admitted for the base workspace sandbox only. A nonempty lane profile requires bubblewrap, firejail, or Seatbelt until Docker has a truthful nested-mount admission probe.
- `harnessie-verify-action` v0.1.1 and the Homebrew formula remain on Harnessie 0.8.0 pending their separately authorized release trains.
- The external `_assistant-guide.harnessie.com` DNS TXT anchor must rotate to the 1.0.0 guide hash before hosted GuideCheck can re-earn its independently anchored level.

The complete change record is in [CHANGELOG.md](https://github.com/snapsynapse/harnessie/blob/v1.0.0/CHANGELOG.md#100-2026-08-09).
