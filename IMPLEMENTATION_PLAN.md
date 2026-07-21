# Harnessie implementation plan

Ordered build steps. Each step has a done test: a check an operator can run that either passes or fails, in the spirit of "define evaluation before scale". Steps 1 through 10 plus the injection-defense layer, OS sandbox (step 15), and the first deterministic eval scorecard (step 12 foundation) are implemented in this repo; their done tests are encoded in tests/. Remaining steps are the hardening path.

The injection-defense layer (harness/quarantine.py; SECURITY.md) is implemented: ingress filter on quarantine=True tools, loop tripwire, per-phase deny_tools, scrubbed child-process env, shell-output secret redaction, and write-time credential refusal. Done test: tests/test_quarantine.py proves poisoned file content is fenced not obeyed, the tripwire re-asserts the boundary, denied tools are hidden and blocked, child env carries no secrets, and credential-shaped strings are redacted from output and refused on write. OS sandbox enforcement for allowlisted interpreters is implemented in step 15.

## Phase 1, minimum safe harness (implemented)

1. Model interface and adapters
- Files: harness/models/base.py, anthropic.py, openai_compat.py, __init__.py
- Done test: MockModel drives a loop deterministically; build_model resolves every provider named in config/models.yaml; adapters return stop_reason="error" turns instead of raising on HTTP failures. (tests/test_loop.py, adapters syntax-checked; live-endpoint smoke test is step 11.)

2. Tool registry with policy
- Files: harness/tools/registry.py, builtin.py
- Done test: a verifier calling write_file raises PermissionDenied; path escapes are rejected; shell allowlists are per role (verifiers get no interpreters or git) and path-escaping shell arguments are refused; approval-required tools fail closed with the default handler. (tests/test_registry.py, all pass.)

3. Agent loop with enumerated stop conditions
- File: harness/loop.py
- Done test: every loop ends in one of {complete, max_steps, budget, stuck, model_error, no_action, refusal}; a run can never end in silence. (tests/test_loop.py covers every stop condition.)

4. Run state journal and resumability
- File: harness/state.py
- Done test: kill a run after phase 1 of 3; re-running with the same run_id skips phases journaled as passed and consults the model zero times for them; a phase journaled as needs_human re-runs instead of silently counting as done. (tests/test_state_memory.py, tests/test_runner.py resume cases.)

5. Routing policy and budgets
- File: harness/routing.py, config/models.yaml
- Done test: task_class maps to declared (tier, effort); escalation walks effort-then-tier and terminates at None (human); budget ceilings stop loops mid-run; the SHIPPED config and workflows parse and reference only valid tiers, efforts, and agents. (tests/test_routing_verify.py, test_loop.py budget case, tests/test_repo_configs.py.)

6. Verification gate
- File: harness/verify.py
- Done test: red deterministic checks block the model verifier (no tokens wasted); failed attempts reformulate the task with evidence and escalate the route; verdict parsing takes the last JSON object with a passed key, so quoted example objects cannot fake a pass, string "false" fails closed, and prose-only verdicts fail closed; attempts exhaust to needs_human. (tests/test_routing_verify.py gate and parser cases.)

7. Memory and proofs
- File: harness/memory.py
- Done test: every fact file carries provenance frontmatter; the context block injected at run start is the index only, never fact bodies; check outputs persist per attempt under runs/<id>/proofs/. (tests/test_state_memory.py, test_runner.py proofs assertion.)

8. Roles and prompt assembly
- Files: harness/roles.py, agents/*.md
- Done test: the harness appends the machine-owned boundary block after the prompt file, so editing agents/*.md cannot remove role limits; the stable prompt+boundaries prefix precedes volatile context; unknown agent names fail with the known-roles list. (tests/test_roles_cli.py.)

9. Workflow runner
- Files: harness/runner.py, workflows/*.yaml
- Done test: the mini workflow runs plan -> gated implement -> integrate end to end on a scripted mock brain; a gate failure halts the workflow before integrate; phase reports flow into later phase tasks. (tests/test_runner.py, passes.)

10. CLI and run reports
- File: harness/cli.py
- Done test: `python3 -m harness.cli report <run_id>` renders journal, gate/route events, and proofs for a finished run; exit code 2 when any phase needs_human (so CI can gate on it), 1 on unknown run_id. (tests/test_roles_cli.py.)

## Phase 2, durability and evaluation (partly implemented)

11. Live adapter smoke tests
- Implemented: `tests/live/` and `harness/live_scorecard.py` are opt-in via `HARNESSIE_LIVE=1`. They discover one Anthropic target and one local OpenAI-compatible target, skip visibly when the flag, key, or endpoint configuration is absent, and run real adapter calls only under that explicit operator opt-in.
- Done test: `python3 -m pytest tests/live -q` skips cleanly without live configuration; `HARNESSIE_LIVE=1 python3 -m pytest tests/live -q` runs the live provider scorecard when credentials/endpoints are configured.

12. Golden-task evaluation suite
- Implemented foundation: `evals/baseline.yaml` plus `harnessie eval` runs 10 network-free mock-brain scenarios: 5 golden, 3 risky fail-closed, and 2 recovery/gate scenarios.
- Implemented live layer: `python3 -m harness.cli eval --live` runs comparable direct, verifier, tool-loop, consent-loop, and consent-lock scorecard rows per configured real provider, with token and cost display where the provider reports usage.
- Done test now: `python3 -m harness.cli eval evals/baseline.yaml` produces a 10/10 scorecard; `tests/test_evals.py` gates it. `python3 -m harness.cli eval --live` exits cleanly with explicit skips in a keyless environment.

13. Interactive approval handler and operator UX (implemented)
- `ToolRegistry.approval_handler` is wired to workflow pre-approval, a headless allow/deny policy file (`--approval-policy`), and an optional TTY prompt (`--approve-interactive`); per-phase token/USD deltas are shown in phase outcomes, `phase_done` events, and CLI output.
- Done test: a requires_approval tool blocks in headless mode by default and proceeds when policy allows; approvals appear in the journal. Covered by `tests/test_approval.py`, `tests/test_triage.py`, and `evals/operability.yaml`.

14. Parallel workers (implemented)
- Independent consecutive phases declared with the same `parallel:` label fan out across workers, with per-phase workspaces under `workspace/.phases/<phase>` to prevent write conflicts.
- The first 0.8 write-safety slice adds opt-in `writes:` preflight: exact files and directory subtrees are parsed in a deliberately decidable language, every member must declare after any member opts in, and invalid or overlapping declarations refuse before workspace creation or dispatch. Declared ownership lanes remain enforced in each isolated workspace; phase-local first-writer claims remain independent.
- Done test: two independent phases run concurrently with disjoint workspaces and both gate independently; total wall-clock beats sequential on a mock brain with latency. Dispatch spies prove conflicts start no phase, adversarial parser cases prove portable alias handling, and operator-owned paths remain denied in parallel phases. Covered by `tests/test_runner.py`, `tests/test_write_safety.py`, `tests/test_ownership.py`, and `evals/operability.yaml`.

15. OS sandbox for shell execution (implemented)
- run_shell and gate checks run inside an OS confinement (harness/sandbox.py; macOS Seatbelt via sandbox-exec) that limits writes to the workspace and denies network by default, closing the interpreter escape that per-role allowlists and the argument jail only narrow. Policy: fail closed everywhere (no backend means shell/checks are blocked, not run unconfined); network is per-phase opt-in via allow_network.
- Done test: a worker's `python3 -c "open('~/x','w')"` is blocked by the sandbox and the file is never created; the same write into the workspace succeeds; network is denied by default; run_shell and gate checks fail closed when the backend is monkeypatched absent. (tests/test_sandbox.py, 7 tests.)
- Linux parity shipped in 0.4.0 through bubblewrap, firejail, and docker backends with admission probes; the no-backend path still fails closed. See [ROADMAP.md](ROADMAP.md) under Platform support.

## Phase 3, extensibility (later, only when earned)

16. Tool plugins: load extra ToolSpecs from tools/*.py entry points with declared effects and roles; a plugin can never bypass registry dispatch.
17. Multi-orchestrator handoffs (only if a single orchestrator demonstrably cannot hold a job): explicit handoff packets with state ownership rules.

Working-set rule: do not start Phase 3 while any Phase 2 done test is red.
