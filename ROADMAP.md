# Harnessie roadmap

This is the forward view: versioned milestones, their themes, and platform support. It answers "what comes next and in what order". For the numbered build steps and their pass/fail done-tests, see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); for the security properties every sandbox backend must satisfy, see [SECURITY.md](SECURITY.md).

Roadmap items are intent, not commitments. Dates are omitted deliberately; milestones ship when their acceptance criteria are green, not on a calendar.

## Current release: 0.1.0 (2026-07-06)

Shipped: brain-agnostic model interface with hot-swappable tiers, tool registry with per-role policy, bounded agent loop, verification gate with reformulate-and-escalate ladder, cost routing and budgets, file-based memory and resumable journal, the workflow runner, a deterministic mock-brain eval scorecard, and a seven-layer prompt-injection defense including an OS sandbox on macOS when Seatbelt profiles can be applied. Full detail in [CHANGELOG.md](CHANGELOG.md). The suite is mock-brain and no-network; real sandbox tests skip on hosts where `sandbox-exec` exists but cannot apply profiles.

## Guiding priorities

- Correctness and safety land before features; no milestone opens while a prior acceptance criterion is red.
- Brain-agnosticism must be a testable claim, not a slogan: a brain is admitted to a tier by passing a scorecard, not by assertion.
- Portability never weakens a guarantee: an unsupported platform fails closed rather than running a control unenforced.
- Lean and solo-operable: complexity is added only when a real threshold is crossed.

## Milestones

### 0.2.0: Portability and proof

Theme: make the harness runnable and measurable beyond a single Mac.

- Linux sandbox backend, so shell-using workflows run confined on Linux instead of failing closed (detail in Platform support below). Implementation step 15 follow-up.
- Live-endpoint smoke tests: one loop turn against a real Anthropic endpoint and one against a local OpenAI-compatible endpoint, opt-in by env var. Implementation step 11.
- Expand the golden-task evaluation scorecard beyond the current mock-brain baseline: golden, risky, and failure-recovery tasks scored into a comparable report against real Anthropic and local OpenAI-compatible endpoints. Implementation steps 11 and 12.

Acceptance: the full suite is green on Linux with a backend present and fails closed on a runner with none; a brain swap (config edit) produces a comparable scorecard.

### 0.3.0: Operability

Theme: put a human comfortably in the loop for long autonomous runs.

- Interactive approval handler wired to a TTY prompt and a headless allow/deny policy file; per-phase cost display. Implementation step 13.
- Parallel workers: independent phases fan out with per-phase workspaces to prevent write conflicts. Implementation step 14.

Acceptance: a requires_approval tool blocks headless by default and proceeds only under policy; two independent phases run concurrently, gate independently, and beat sequential wall-clock.

### 1.0.0: Extensibility, earned

Theme: stable surfaces and pluggability, only after the core is proven.

- Tool plugins loaded from entry points with declared effects and roles; a plugin can never bypass registry dispatch. Implementation step 16.
- Multi-orchestrator handoffs, only if a single orchestrator is demonstrably unable to hold a job. Implementation step 17.
- Frozen config and workflow schema with a written deprecation policy.

Gate: no 1.0 while any 0.2 or 0.3 acceptance criterion is red.

## Platform support

### Supported today

macOS is fully supported: the OS sandbox uses native `sandbox-exec` (Seatbelt), confining child-command writes to the workspace and denying network by default. On Linux and Windows the harness logic (pure Python) runs, but shell-using workflows fail closed because no sandbox backend is wired. This is the fail-closed-everywhere policy working as designed, not a bug: a control that cannot be enforced is refused rather than skipped.

### Linux support (0.2.0 target)

This is the headline portability need. The same security policy the macOS backend enforces (writes confined to the workspace, network denied by default, per-phase `allow_network` opt-in) must be expressed with Linux primitives.

Backend:

- Add a Linux backend to `harness/sandbox.py` that maps the existing policy onto, in order of preference:
  - bubblewrap (`bwrap`) as primary: rootless, no daemon, lightweight. Confinement via read-only bind of the root filesystem, a read-write bind of the workspace, `--unshare-net` for network deny, a private `/tmp`, a minimal `/dev`, and `--die-with-parent`.
  - firejail as the alternative where bubblewrap is absent.
  - docker as a heavyweight fallback: the workspace bind-mounted, `--network none` for deny, non-root user.
- Extend `backend_name()` to detect the available backend on Linux and keep failing closed when none is present.

Parity tests:

- The existing escape tests (a worker `python3` writing outside the workspace is denied, network is denied, a workspace write succeeds, and shell/checks fail closed when no backend exists) must pass under the Linux backend with the same assertions as the macOS suite. Confinement equivalence is the acceptance bar, not merely "a sandbox runs".

CI:

- Run the full suite on both a Linux runner with bubblewrap installed and a macOS runner; assert both green. Add a job with no backend present and assert shell-using workflows fail closed.

Docs:

- Extend the backend section of [SECURITY.md](SECURITY.md) with a table: platform, backend, the confinement primitive used, and its known gaps.

Linux non-goals for now:

- seccomp-bpf syscall filtering beyond what bubblewrap already provides; revisit only if the threat model demands it.
- Rootless-container orchestration beyond a single bind-mounted workspace.

### Windows

The pure-Python harness logic runs on Windows, but shell and gate checks fail closed: there is no first-class rootless sandbox equivalent in scope. Windows sandboxing is out of scope for the current roadmap; workflows that need shell should run under WSL2 (which presents as Linux and uses the Linux backend) or on macOS.

## Non-goals (all platforms)

- Multi-agent coordination beyond orchestrator / worker / verifier until a single orchestrator is provably insufficient for a real job.
- A plugin system before the core primitives are stable; gated behind 1.0.
- Hosted-service conventions (robots.txt, sitemaps, and similar): Harnessie is a library and CLI, not a site.

## How the planning docs relate

- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): numbered build steps, each with a pass/fail done-test. The how.
- [ROADMAP.md](ROADMAP.md): versioned milestones and platform support. The what-order and when-ready.
- [SECURITY.md](SECURITY.md): the security model each backend and control must satisfy. The invariants.
