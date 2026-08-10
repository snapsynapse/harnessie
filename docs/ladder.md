# Modes: the ease and safety ladder

An AI harness is easier to watch than to explain, and easier to trust once you can see exactly how much of it is real. Harnessie runs at five named modes. Each one trades ease of use against a single thing: how much a human has their eyes on the code before it runs.

The point of naming them is choice. Every mode states, in plain language, what is real, what is not, and which risk you are accepting, so you pick the rung on purpose instead of discovering the trade-off after the fact. Start at the bottom and climb at your own pace. Nothing pushes you up a rung.

## The trade-off axis

There is one axis: human eyes on the code. At the bottom, a mock run creates only local scaffold and run records. At the top, an external agent may drive the CLI while a human has not read the resulting code. The lower rungs are safer and slower; the higher rungs are easier and faster and accept more risk. The ladder makes the exchange rate visible.

Inside a Harnessie run, deterministic gates apply to worker phases and child commands require an admitted sandbox. Harness-managed agents cannot write decision records, so contested decisions halt for an operator. An external agent driving the CLI is outside that identity boundary; Harnessie cannot currently prove whether the operator editing an arbitration record was a human or another process.

## The ladder at a glance

| Rung | What is real | Your role | Risk you accept | Status |
| --- | --- | --- | --- | --- |
| 0 Watch | Mock brain; local scaffold and run records; no provider call or model spend | Watch a harness work end to end | Local files are created | Shipped |
| 1 Narrate | Real brains reasoning; side effects disabled | Watch real agents think and verify | None of consequence | Partial |
| 2 Approve every step | Intended full run with every write and execution mediated | Read each proposed side effect | Not available as a complete mode | Not shipped |
| 3 Approve on exception | Full run, halts only at named conditions | Review the exceptions, not every line | Code you did not read may run inside the gates | Shipped |
| 4 Agent-mediated | External agent drives the CLI outside Harnessie's role boundary | Supervise in natural language | Operator identity and arbitration authorship are not authenticated | Experimental |

## Rung 0, Watch

The gentlest entry. A mock brain makes no provider call and spends no model money. `harnessie init` still creates a local project scaffold and local run records, so this is low consequence rather than no side effect. This rung exists to make the concept concrete before you configure a real model.

Mechanism: the zero-dollar mock run scaffolded by `harnessie init`. See [Getting started](getting-started.md).

Risk accepted: none. What you are choosing: understand the idea first.

## Rung 1, Narrate

Real models reason about your goal, but every side effect is disabled and each gate and disagreement is explained inline. You see genuine cognition, real verification, and real contested decisions, while nothing touches your files or system. This is the honest bridge between watching a mock and running the real thing.

Risk accepted: none of consequence, because no side effect executes. What you are choosing: see real thinking without real results. This rung is partly present today and is called out as a gap in the [INTENT](../INTENT.md); it is being built out.

## Rung 2, Approve every step

A complete approve-every-step mode would mediate every write and command before execution and show the proposed effect to the operator. Harnessie does not currently provide that mode. `--approve-interactive` is narrower: it prompts only for tools whose registry declaration sets `requires_approval`. Built-in `write_file` and `run_shell` are governed by consent, role, ownership, sandbox, and workflow policy, but they are not turned into per-call human prompts by this flag.

Current building block: `--approve-interactive` for approval-gated tools. Shipping this rung requires a separate structural mediation mode for every side-effecting tool.

Status: not shipped as described. Do not treat `--approve-interactive` as an every-side-effect guarantee.

## Rung 3, Approve on exception

The run proceeds autonomously and halts only at named conditions: a budget ceiling, a verifier failure, a contested decision, or a prompt-injection quarantine. You review the exceptions the harness raises rather than every line. This is faster, and it is honest about its cost.

Mechanism: ordinary governed execution plus an optional headless policy for tools that are explicitly approval-gated. The policy does not grant or deny every write or command. The controls it composes are documented in the [Threat model](threat-model.md).

Risk accepted: code you did not personally read may execute inside the sandbox and gates before you see it; you are trusting the automatic guards to catch the dangerous cases. What you are choosing: speed, with a human on the exceptions.

## Rung 4, Agent-mediated

An outer agent can edit config, launch runs, operate approval policy, and narrate results through the CLI. That is possible as external automation, but it is not a distinct authenticated Harnessie mode. The outer agent has the operator's filesystem authority and sits outside the in-run role and ownership boundary.

Harnessie does not yet record authenticated operator-of-record and arbiter-of-record identities. An external agent could edit an arbitration record with the same authority as its human operator, so human authorship must be enforced outside Harnessie. Treat this rung as experimental, not as a stronger safety claim.

Risk accepted: no human eyes on the code by default. What you are choosing: maximum ease, maximum delegation.

## The invariant that holds across every rung

Within the run boundary, workers and verifiers cannot reach the decision record, and the harness never writes the Arbitration section. A contested phase halts until the operator-side record changes. This mechanically separates in-run agents from the operator, but it does not authenticate the operator as human. An external delegated agent with operator filesystem authority is not distinguishable from the human in the current audit format.

The intended product invariant remains that arbitration belongs to a human. The current enforcement proves only that Harness-managed agents cannot author it. Authenticated operator and arbiter identities are required before the external agent-mediated rung can claim the stronger invariant. See [GOVERNANCE](../GOVERNANCE.md) for the shipped in-run boundary.

## What exists today, and what does not

The mock run and governed autonomous execution are shipped. Narrate remains partial; approve-every-step is not implemented for ordinary write and execute tools; agent-mediated operation is external automation without authenticated seat identity; and the CLI does not yet print a per-rung trade-off banner. These are product gaps, not alternate names for existing flags.
