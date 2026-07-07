# Harnessie evals
Harnessie evals are YAML scorecards under `evals/`. They are deliberately small, deterministic, and runnable without network by default. The current baseline suite uses a scripted mock brain so it can run in CI and on hosts without usable sandbox support.
## Commands
- Run every suite: `python3 -m harness.cli eval`
- Run one suite: `python3 -m harness.cli eval evals/baseline.yaml`
- Run opt-in live provider scorecards: `HARNESSIE_LIVE=1 python3 -m harness.cli eval --live`
- Test the eval runner: `python3 -m pytest tests/test_evals.py -q`
## Scenario contract
Every scenario has:
- `id`: stable snake-case identifier, unique within the suite.
- `kind`: one of `verdict`, `loop`, `workflow`, `resume`, `ownership`, `adversarial`, `audit`, `triage`, or `parallel`.
- Expected result fields, which depend on `kind`.
## Suites
- `evals/baseline.yaml`: core harness guarantees (verdicts, stop conditions, gates, resume).
- `evals/governance.yaml`: the v0.2 governance layer (consent, ownership, adversarial contest, audit). Written red before the implementation per the eval-first change discipline (GOVERNANCE.md §6); a governance feature without a red-then-green scenario pair does not merge.
- `evals/operability.yaml`: the v0.5 operability layer (headless approval policy, parallel phase workspaces).
- `evals/triage.yaml`: the v0.3 memory-triage layer (approval-gated expiry, headless propose-only, memory lint halting). Same red-first discipline.
## Scenario kinds
### verdict
Exercises verifier verdict parsing only.
- Input: `report`
- Expected: `expect_passed`
- Use for JSON edge cases, prose-only verdicts, quoted example objects, string booleans, and fail-closed parsing.
### loop
Exercises the inner `AgentLoop`.
- Input: `role`, `task`, `max_steps`, `script`, optional `consent` (bool), optional `agent`
- Expected: `expect_stop`, optional `expect_file` (`{path, contains}`), optional `expect_file_absent`, optional `expect_refusal` (`{tool, error, boundary, content_fields}`). `content_fields` is asserted against the `refusal` event, which carries the full `{error, boundary, detail, why}` grammar; `tool_result` content is truncated at 300 chars and is never parsed by the checker.
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
### triage
A memory-triage workflow over seeded facts (one fresh, one stale).
- Input: `script`, `approve_expiry` (bool), optional `approval_policy` (`allow`/`deny` rules), optional `corrupt_index` (bool)
- Expected: `expect_statuses`, optional `expect_fact`, `expect_archived`, `expect_fact_kept`
- Use for recorded-approval expiry, headless propose-only fail-closed behavior, and memory-lint halting.
### parallel
Exercises a plan -> two parallel worker phases -> integrate workflow.
- Input: optional `goal`, `expect_elapsed_lt`
- Expected: `expect_statuses`, optional `expect_files` mapping phase-relative paths under `workspace/.phases/` to exact contents.
- Use for proving independent phases gate under separate workspaces and beat the sequential wall-clock.
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
The mock-brain baseline proves harness mechanics. The 0.4 live scorecard in `harness/live_scorecard.py` reuses the same categories against configured real endpoints, including governance probes for consent and the locked-side-effect boundary:
- Anthropic target: configured from `config/models.yaml` by default; requires `HARNESSIE_LIVE=1` and `ANTHROPIC_API_KEY`.
- Local OpenAI-compatible target: requires `HARNESSIE_LIVE=1` and either `HARNESSIE_OPENAI_COMPAT_BASE_URL` or `HARNESSIE_LIVE_OPENAI_COMPAT=1` to use the checked-in local tier.
- Scorecard rows: direct completion, verifier JSON, tool-loop completion, consent-loop completion, and consent-lock risky behavior.
Do not make live evals part of the default no-network suite. Gate them behind the explicit environment flag; absent credentials or endpoints produce visible `SKIP` rows, not silent omissions.
