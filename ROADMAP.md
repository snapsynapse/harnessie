# Harnessie roadmap

This is the forward view: versioned milestones, their themes, and platform support. It answers "what comes next and in what order". For the numbered build steps and their pass/fail done-tests, see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); for the security properties every sandbox backend must satisfy, see [SECURITY.md](SECURITY.md).

Roadmap items are intent, not commitments. Dates are omitted deliberately; milestones ship when their acceptance criteria are green, not on a calendar.

## Current release: 0.5.0 (2026-07-07)

The operability release: approval-gated tools can be governed by a headless allow/deny policy file or an interactive TTY prompt; run output and audit events now show per-phase cost; independent phases declared with the same `parallel:` label fan out into per-phase workspaces and gate independently. Details in [CHANGELOG.md](CHANGELOG.md).

## Prior release: 0.4.0 (2026-07-07)

The portability-and-proof release: Linux sandbox backends and CI matrix are in, live provider scorecard infrastructure is opt-in and skipped visibly when no credentials/endpoints are configured, and the public trust bundle has a hash-verified `docs/MANIFEST.yaml`. The live provider calls themselves remain operator-attended: `HARNESSIE_LIVE=1 python3 -m harness.cli eval --live` is the documented invocation, not a default test path. Details in [CHANGELOG.md](CHANGELOG.md).

## Prior release: 0.3.3 (2026-07-06)

Mitigation patch from the v0.3.2 verification rotation: `refusal` events carry the full grammar (`detail`, `why`) so no consumer parses truncated `tool_result` content; the stuck detector counts policy refusals regardless of the `ok` flag; `find_secrets` reports kind labels instead of credential fragments. Details in [CHANGELOG.md](CHANGELOG.md).

## Prior release: 0.3.2 (2026-07-06)

The v0.3 patch line now includes the aggregated-intelligence release plus the v0.3.2 hardening patch: structured refusal grammar on denial surfaces, audited `refusal` events, and human-readable checked refs for run IDs, change requests, and generated decision records. Tenets mapping: [GOVERNANCE.md](GOVERNANCE.md) §7; direction record `decisions/AIDR-0002` (human-arbitrated 2026-07-06). Portability remains the undiluted 0.4 headline.

## Prior release: 0.2.0 (2026-07-06)

The governance release: consent-based orchestration (task packets are offers; accept/decline enforced at dispatch), ownership lanes (agents own their files, never each other's; operator lanes locked), adversarial contested phases emitting AIDR-shaped decision records with human-only arbitration and structurally earned claims, a hash-chained events log with `harnessie audit`, and the eval-first change discipline with an 11-scenario governance suite (12 as of v0.3.1). Direction recorded in `decisions/AIDR-0001` (human-arbitrated 2026-07-06); design in [GOVERNANCE.md](GOVERNANCE.md). This displaced the previously planned portability theme, which moves to 0.3.0.

## Prior release: 0.1.0 (2026-07-06)

Shipped: brain-agnostic model interface with hot-swappable tiers, tool registry with per-role policy, bounded agent loop, verification gate with reformulate-and-escalate ladder, cost routing and budgets, file-based memory and resumable journal, the workflow runner, a deterministic mock-brain eval scorecard, and a seven-layer prompt-injection defense including an OS sandbox on macOS when Seatbelt profiles can be applied. Full detail in [CHANGELOG.md](CHANGELOG.md). The suite is mock-brain and no-network; real sandbox tests skip on hosts where `sandbox-exec` exists but cannot apply profiles.

## Guiding priorities

- Correctness and safety land before features; no milestone opens while a prior acceptance criterion is red.
- Brain-agnosticism must be a testable claim, not a slogan: a brain is admitted to a tier by passing a scorecard, not by assertion.
- Portability never weakens a guarantee: an unsupported platform fails closed rather than running a control unenforced.
- Lean and solo-operable: complexity is added only when a real threshold is crossed.

## Milestones

### 0.3.x: Aggregated-intelligence tenets, agent triage, refusal hardening - SHIPPED (current release above)

Acceptance met: triage runs headless as propose-only and applies only under recorded approval; a stale fact is surfaced by date, archived never deleted; the audit timeline shows agent and operator actions interleaved; refusals carry `{error, boundary, detail, why}` and are audit-rendered. Current baseline: 117 passed, 3 skipped; 26 eval scenarios green.

### 0.4.0: Portability and proof - SHIPPED

Theme: make the harness runnable and measurable beyond a single Mac.

- Linux sandbox backend, so shell-using workflows run confined on Linux instead of failing closed (detail in Platform support below). Implementation step 15 follow-up. GREEN 2026-07-07: bwrap/firejail/docker backends with startup smoke tests, policy-construction unit tests, and a CI matrix (Linux bubblewrap parity, macOS, no-backend fail-closed) passing on a real run. The first run caught one macOS-hardcoded test, since fixed. This acceptance is met: the full suite is green on Linux with a backend present and fails closed on a runner with none.
- Live-endpoint smoke tests: implemented as opt-in code and pytest infrastructure (`tests/live/`, `harness/live_scorecard.py`). A keyless/no-endpoint environment emits visible skips; real calls require `HARNESSIE_LIVE=1` plus provider configuration. Implementation step 11.
- Golden-task evaluation scorecard beyond the mock-brain baseline: implemented as `python3 -m harness.cli eval --live`, with direct, verifier, tool-loop, consent-loop, and consent-lock rows per configured provider, including token and cost display where usage is reported. Implementation steps 11 and 12.
- Trust-bundle manifest integrity: `docs/MANIFEST.yaml` pins the hash of public machine-readable trust/discovery files; `python3 -m harness.cli verify-manifest` and `tests/test_trust_manifest.py` verify it.
- Live contested-phase run: ready for an operator-attended run through `workflows/contested-decision.yaml` across two real providers. This remains a live-provider operation and is not part of the default no-network suite.

Acceptance: the full suite is green on Linux with a backend present and fails closed on a runner with none; a brain swap (config edit) produces a comparable scorecard.

### 0.5.0: Operability - SHIPPED (current release above)

Theme: put a human comfortably in the loop for long autonomous runs.

- Interactive approval handler wired to a TTY prompt and a headless allow/deny policy file; per-phase cost display. Implementation step 13. GREEN 2026-07-07: `--approval-policy` and `--approve-interactive` are wired through CLI and `WorkflowRunner`; policy denials fail closed; phase outcomes/events carry local cost deltas.
- Parallel workers: independent phases fan out with per-phase workspaces to prevent write conflicts. Implementation step 14. GREEN 2026-07-07: contiguous phases with the same `parallel:` label run concurrently under `workspace/.phases/<phase>`, gate independently, and beat the sequential wall-clock in the mock-brain test.

Acceptance: a requires_approval tool blocks headless by default and proceeds only under policy; two independent phases run concurrently, gate independently, and beat sequential wall-clock.

### 0.6.0: First-harness readiness (public launch gate)

Theme: make "the safest and easiest first AI harness for people" true for someone who has never identified as a developer, and make the safety claim falsifiable for the developers who will audit it. This milestone gates the public launch; it does not displace 0.4 portability or 0.5 operability, both of which it depends on.

Ease (the first-run path):
- PyPI packaging: `pip install harnessie` (or `pipx install harnessie`) replaces clone-and-editable-install as the documented entry; signed, tagged releases with `RELEASE_CHECKLIST.md` per the repo-standards promotion path.
- Guided first run: `harnessie init` grows an interactive setup that checks Python version, detects a sandbox backend, walks API-key setup via environment variable (never a file), and ends with a green mock-brain run so the first experience costs zero dollars.
- Plain-language operator surface: `harnessie report` and every halt message readable by a non-developer; each stop condition explains itself in one sentence and names the single next action (the README halt table becomes the in-tool text, not just docs).
- Pre-run cost preview: before a live run, show the configured ceilings and a worst-case dollar estimate; refuse to start when no ceiling is set. GREEN 2026-07-07: `harness/preflight.py` prints a LIVE/MOCK preview with ceilings and the token-implied worst case (naming which ceiling binds first) ahead of any run state or brain build, and returns a non-zero refusal for a live, ceiling-less config; mock runs are always free and never refused, an unknown provider is treated as billable. Covered by `tests/test_preflight.py` and a CLI refusal check leaving no run artifact. Meets the acceptance clause "a fresh install on a ceiling-less config refuses a live run."
- A non-developer quickstart in `docs/` (the served tree once public): one real, useful, low-risk workflow end to end, with a glossary that never assumes git or shell fluency.
- Windows path documented honestly: WSL2 walkthrough, plus a clear statement of what fails closed on bare Windows and why that is protection, not breakage.

Standards adoption (the credited specs become checkable claims):
- GuideCheck: rewrite the shipped `assistant-guide.txt` from the current minimal unstructured guide to a conformable Level 3+ profile; add the byte-identical `.well-known/assistant-guide.txt` plus manifest sidecar (the trust-anchored pair) and verify the hash match; link it from the landing page footer and README so it is discoverable, not just present. The `.well-known/` half is only verifiable end-to-end once Pages is live; the content rewrite and manifest need not wait.
- Graceful Boundaries: check the shipped v0.3.2 refusal grammar against GB's conformance criteria across all 16 enumerated denial sites; cite the achieved level (or a named gap list) in `SECURITY.md` or `GOVERNANCE.md`; update `INTENT.md` §7 from lesson-import to the real adopted status.
- Siteline: the live canonical page (harnessie.com) scores 90 or above on a `siteline-scan`, complementing the already-clean axe-core WCAG pass. Requires the site live; restated from the go-live steps so it is a gate, not an assumption.

Safety (the falsifiable claim):
- A published threat-model comparison artifact: SECURITY.md properties mapped against the failure modes of prevailing harness patterns (unsandboxed shell, prompt-level-only guardrails, self-verification, silent dissent-merging), each row citing the enforcing code and its test. This is the artifact the "safest" headline points at. GREEN 2026-07-07: [docs/threat-model.md](docs/threat-model.md) ships an eleven-row falsifiable table over those four spine patterns plus cost, secrets, approval, ownership, consent, and audit; all 25 cited `file::test` nodes resolve and pass; the honest residual and the tamper-evident/per-file limits are stated plainly. Linked from README and SECURITY.md for discoverability.
- A standing "break it" invitation: a `SECURITY.md` disclosure path plus eval scenarios published as red-team targets, so the claim is contestable in public rather than asserted.
- Default-deny posture audit before launch: one pass proving every tool grant, network allowance, and approval gate defaults closed in the shipped configs (extends `tests/test_repo_configs.py`). GREEN 2026-07-07: eleven assertions over the shipped `register_builtin` registry, `OWNERSHIP.yaml`, and both CLI seams — the orchestrator holds no side-effecting tool, the verifier never writes, every write/execute tool excludes the orchestrator, the destructive `expire_fact` is approval-gated, `dispatch` and `_loop_for` default network off, and unknown-tool / wrong-role / unapproved / pre-consent dispatches all fail closed; the operator lane ships and no files are pre-claimed for agents.

Acceptance: a non-developer given only the quickstart reaches a green first run without touching a config file; the comparison artifact exists with every row citing code and test; a fresh install on a ceiling-less config refuses a live run; the GuideCheck pair verifies, the Graceful Boundaries status (level or gap list) is cited in a tracked doc, and the live page passes the Siteline bar.

### 1.0.0: Extensibility, earned

Theme: stable surfaces and pluggability, only after the core is proven.

- Tool plugins loaded from entry points with declared effects and roles; a plugin can never bypass registry dispatch. Implementation step 16.
- Multi-orchestrator handoffs, only if a single orchestrator is demonstrably unable to hold a job. Implementation step 17.
- Per-lane sandbox profiles, closing the ownership layer's honest limit (interpreter writes bypass the per-file check today).
- Frozen config and workflow schema with a written deprecation policy.

Gate: no 1.0 while any 0.3, 0.4, 0.5, or 0.6 acceptance criterion is red.

## Platform support

### Supported today

macOS is fully supported: the OS sandbox uses native `sandbox-exec` (Seatbelt), confining child-command writes to the workspace and denying network by default. Linux backends (bubblewrap preferred, firejail alternate, docker fallback) are implemented as of the 0.4 line, each admitted only after a startup smoke test; CI proves the suite green under bubblewrap and proves fail-closed with every backend removed. On Windows, and on any host where no backend passes its smoke test, shell-using workflows fail closed. This is the fail-closed-everywhere policy working as designed, not a bug: a control that cannot be enforced is refused rather than skipped.

### Linux support (0.4.0 target)

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
