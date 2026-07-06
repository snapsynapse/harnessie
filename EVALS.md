# Harnessie evals
Harnessie evals are YAML scorecards under `evals/`. They are deliberately small, deterministic, and runnable without network by default. The current baseline suite uses a scripted mock brain so it can run in CI and on hosts without usable sandbox support.
## Commands
- Run every suite: `python3 -m harness.cli eval`
- Run one suite: `python3 -m harness.cli eval evals/baseline.yaml`
- Test the eval runner: `python3 -m pytest tests/test_evals.py -q`
## Scenario contract
Every scenario has:
- `id`: stable snake-case identifier, unique within the suite.
- `kind`: one of `verdict`, `loop`, `workflow`, or `resume`.
- Expected result fields, which depend on `kind`.
## Suites
- `evals/baseline.yaml`: core harness guarantees (verdicts, stop conditions, gates, resume).
- `evals/governance.yaml`: the v0.2 governance layer (consent, ownership, adversarial contest, audit). Written red before the implementation per the eval-first change discipline (GOVERNANCE.md §6); a governance feature without a red-then-green scenario pair does not merge.
## Scenario kinds
### verdict
Exercises verifier verdict parsing only.
- Input: `report`
- Expected: `expect_passed`
- Use for JSON edge cases, prose-only verdicts, quoted example objects, string booleans, and fail-closed parsing.
### loop
Exercises the inner `AgentLoop`.
- Input: `role`, `task`, `max_steps`, `script`, optional `consent` (bool), optional `agent`
- Expected: `expect_stop`, optional `expect_file` (`{path, contains}`), optional `expect_file_absent`
- Use for stop conditions such as `no_action`, `refusal`, `model_error`, `budget`, `stuck`, and `declined`, and for consent-lock behavior (side effect before accept_task must leave no artifact).
### workflow
Exercises plan, gated implement, and integrate over a scaffolded temporary project.
- Input: `script`, optional `max_attempts`, optional `goal`
- Expected: `expect_statuses`
- Use for golden happy paths, verifier rejection, retry recovery, and halt-before-integrate behavior.
### resume
Runs the same temporary workflow twice with the same `run_id`.
- Input: `first_script`, `second_script`
- Expected: `expect_first_statuses`, `expect_second_statuses`
- Use for resume semantics, especially skipping only verified successes and re-running `needs_human` phases.
### ownership
Sequential worker loops as different agents over one shared workspace and ownership ledger.
- Input: `steps` (list of `{agent, script}`), optional `lanes` (`agent` / `collaborative` / `operator`)
- Expected: optional `expect_owner` (path -> agent), `expect_file`, `expect_file_absent`
- Use for first-writer-owns, cross-agent denial, operator-lane locks, and collaborative sharing.
### adversarial
A contested phase (`mode: adversarial`, two scripted positions) in a temporary project.
- Input: `script`; optional `arbitration_text` to simulate the operator arbitrating between runs (the eval fixture plays the human; at runtime no code path does this)
- Expected: `expect_statuses`, or `expect_first_statuses` + `expect_second_statuses` with `arbitration_text`
- Use for convergence, dissent halting as `needs_arbitration`, fail-closed stance parsing, and arbitration-resume.
### audit
Emits a small event log, verifies the hash chain, optionally tampers a line.
- Input: `tamper` (bool)
- Expected: `expect_before`, `expect_after`
- Use for proving the chain detects edits.
## Script turns
Mock-brain script entries can be tool calls:
- `tool`: tool name such as `task_complete`, `write_file`, or `read_file`
- `args`: tool arguments
Or plain model turns:
- `content`: assistant text
- `stop_reason`: optional normalized stop reason
## Adding cases
Add cases in this order:
- Golden cases: expected good behavior must pass.
- Risky cases: unsafe, ambiguous, malformed, or overconfident behavior must fail closed.
- Recovery cases: a first failure should reformulate, retry, escalate, or halt as specified.
Prefer narrow scenarios. A scenario should explain one harness guarantee. If it needs many unrelated turns, split it.
## Live eval path
The mock-brain baseline proves harness mechanics. The 0.2 live scorecard should reuse the same categories against configured real endpoints:
- Anthropic smoke: one golden workflow and one verifier verdict.
- Local OpenAI-compatible smoke: one golden workflow and one risky fail-closed case.
- Brain-swap report: same task set, same acceptance criteria, comparable pass/fail and cost output.
Do not make live evals part of the default no-network suite. Gate them behind an explicit environment flag and skip cleanly without credentials.
