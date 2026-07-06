# Next session handoff
## Current state
Harnessie is a private personal-utility repo on `main`, trajectory public / portfolio-bound. The core v0.1 harness is implemented: model adapters, role prompts, registry, loop, verification gate, routing, memory, journal, runner, CLI, quarantine, and macOS Seatbelt sandbox integration when usable.
## Verification status
- `python3 -m pytest -q`: 56 passed, 3 skipped.
- `python3 -m harness.cli eval`: 10/10 passed.
- `python3 -m harness.cli eval evals/baseline.yaml`: 10/10 passed.
- `python3 -m harness.cli --root /private/tmp init harnessie-init-smoke`: scaffolded 7 files successfully.
## Host caveat
This Codex host exposes `sandbox-exec` but rejects profile application with `sandbox_apply: Operation not permitted`. Harnessie now treats that as sandbox-unavailable and fails closed. The 3 skipped tests are real Seatbelt confinement tests that should run on a normal macOS host where profiles can be applied.
## What changed most recently
- Added `harnessie eval` and `evals/baseline.yaml`.
- Added `harnessie init` for installed CLI scaffolding.
- Made sandbox availability require a real profile-application smoke test.
- Made bad route tiers fail early instead of silently falling back.
- Updated docs and tests to reflect the new behavior.
## Next 0.2 priorities
1. Add opt-in live endpoint smoke tests under `tests/live/`.
2. Expand evals from mock-brain mechanics to real brain-swap scorecards.
3. Add Linux sandbox backend detection and parity tests for bubblewrap first, then firejail/docker fallback.
4. Add interactive/headless approval policy support and journaled approvals.
5. Decide packaging surface: package data, `harnessie init` as canonical, or both.
## Non-goals for next session
- Do not add plugins before the core eval and portability gates are stronger.
- Do not make live evals run by default.
- Do not weaken fail-closed behavior to make tests pass on unsupported hosts.
- Do not stage `.agents/` or `.codex/` unless the operator explicitly decides those local wrappers should become tracked repo assets.
## First commands for the next agent
- `git status --short --branch`
- `python3 -m pytest -q`
- `python3 -m harness.cli eval`
