# Modes: the ease and safety ladder

An AI harness is easier to watch than to explain, and easier to trust once you can see exactly how much of it is real. Harnessie runs at five named modes. Each one trades ease of use against a single thing: how much a human has their eyes on the code before it runs.

The point of naming them is choice. Every mode states, in plain language, what is real, what is not, and which risk you are accepting, so you pick the rung on purpose instead of discovering the trade-off after the fact. Start at the bottom and climb at your own pace. Nothing pushes you up a rung.

## The trade-off axis

There is one axis: human eyes on the code. At the bottom, nothing real happens and you simply watch. At the top, real work runs with a human never having read it first, trusting the gates and a delegated agent instead. Neither end is wrong. The lower rungs are safer and slower; the higher rungs are easier and faster and accept more risk. The ladder makes the exchange rate visible.

Two things never move, no matter how high you climb. Deterministic gates and the sandbox run at every rung. And a contested decision is always arbitrated by a human. The easiest mode still cannot decide a contested question for you.

## The ladder at a glance

| Rung | What is real | Your role | Risk you accept | Status |
| --- | --- | --- | --- | --- |
| 0 Watch | Nothing. Mock brain, no network, no side effects, zero dollars | Watch a harness work end to end | None | Shipped |
| 1 Narrate | Real brains reasoning; side effects disabled | Watch real agents think and verify | None of consequence | Partial |
| 2 Approve every step | Full run, halts at every side effect | Read the diff, approve or decline each one | Only what you personally approve | Shipped |
| 3 Approve on exception | Full run, halts only at named conditions | Review the exceptions, not every line | Code you did not read may run inside the gates | Shipped |
| 4 Agent-mediated | Full run, an agent holds the operator seat | Supervise in natural language | A human may never read the code first | Possible now |

## Rung 0, Watch

The gentlest entry. A mock brain, no network, no side effects, and no money spent. You watch a real harness decompose a goal, hand work to workers, and gate results through verifiers, with nothing at stake. This rung exists to make the concept concrete before you touch anything.

Mechanism: the zero-dollar mock run scaffolded by `harnessie init`. See [Getting started](getting-started.md).

Risk accepted: none. What you are choosing: understand the idea first.

## Rung 1, Narrate

Real models reason about your goal, but every side effect is disabled and each gate and disagreement is explained inline. You see genuine cognition, real verification, and real contested decisions, while nothing touches your files or system. This is the honest bridge between watching a mock and running the real thing.

Risk accepted: none of consequence, because no side effect executes. What you are choosing: see real thinking without real results. This rung is partly present today and is called out as a gap in the [INTENT](../INTENT.md); it is being built out.

## Rung 2, Approve every step

A real run. Every side-effecting phase halts and shows you the command, the diff, and the verifier evidence. Nothing proceeds without your yes. This is maximum eyes-on-code and the true-safety pole of the ladder. It is slower by design, and it is the rung where a newcomer can read real changes with a stop button on every one, so approving something you do not understand is structurally impossible.

Mechanism: `--approve-interactive`. The [User guide](GUIDE.md) covers the halt-and-recover table.

Risk accepted: only what you read and approve. What you are choosing: full control, more of your time.

## Rung 3, Approve on exception

The run proceeds autonomously and halts only at named conditions: a budget ceiling, a verifier failure, a contested decision, or a prompt-injection quarantine. You review the exceptions the harness raises rather than every line. This is faster, and it is honest about its cost.

Mechanism: a headless approval policy via `--approval-policy`. The dangerous classes it leans on are documented in the [Threat model](threat-model.md).

Risk accepted: code you did not personally read may execute inside the sandbox and gates before you see it; you are trusting the automatic guards to catch the dangerous cases. What you are choosing: speed, with a human on the exceptions.

## Rung 4, Agent-mediated

An outer agent holds the operator seat. It edits config, launches runs, approves by the policy you set, and narrates results back to you in plain language. You supervise the supervisor. This is the easiest and most delegated mode, and it accepts the most risk, stated bluntly: a human may never read the code before it runs. You are trusting the gates and a delegated agent operator at once.

This rung is possible today by pointing any capable agent at the CLI. What makes it safe to offer is the invariant below, plus two audit fields that record who actually held each seat.

Risk accepted: no human eyes on the code by default. What you are choosing: maximum ease, maximum delegation.

## The invariant that holds across every rung

The operator seat and the arbiter seat are different seats. The operator seat, orchestration and approvals, may be occupied by a delegated agent acting on your instruction. The arbiter seat may not. When agents disagree on a contested decision, the harness stops and escalates to a human, even at Rung 4 where an agent is driving everything else. It records the decision as a human arbitration in a hash-chained audit log, and it marks operator-of-record, human or delegated-agent, and arbiter-of-record, always human, as distinct fields so the timeline can prove who held each seat.

That is why the most delegated mode is still safe to offer. The easiest rung cannot decide a contested question for you. This is design invariant 13; see [GOVERNANCE](../GOVERNANCE.md) and the human-only arbitration rule the harness dogfoods in its own decision records.

## What exists today, and what does not

Most of the ladder is already the harness you can install. The mock run, step-by-step approval, and exception-only approval are shipped mechanisms, not promises. The honest gaps, recorded openly, are the Narrate rung, the operator-of-record and arbiter-of-record audit fields, and the plain-language trade-off banner each rung should print before it runs. Where a claim on this page is not yet true in code, it says so. That is the same rule the rest of this site follows: every safety claim points at something you can check.
