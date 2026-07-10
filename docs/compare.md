# How Harnessie compares

Harnessie is often mistaken for yet another agent framework. It isn't one, and the difference is the whole point.

Agent frameworks answer one question well: how do several agents work together? Guardrail tools answer a different one: how do I filter a single model's output? Harnessie answers a third that neither of the others owns: how do I trust what a group of agents produced, and contain what they were allowed to touch, on models I choose to run?

You can use Harnessie's ideas next to an orchestrator, or use Harnessie as the harness. This page is about where it fits, and where it honestly does not.

## Three categories, not one race

- Orchestration frameworks (LangGraph, CrewAI, AutoGen / AG2, the OpenAI and Claude Agent SDKs). Best at composing multi-agent workflows: handoffs, group chat, hierarchical managers, optional critic and reflection agents. Their collaboration is cooperative by design. Agents help each other converge.
- Guardrail and safety tools (Guardrails AI, NeMo Guardrails, Lakera). Best at wrapping a model with input and output controls: validators, policy rails, prompt-injection defense. They sit around one model, not across a multi-agent result.
- Harnessie. A harness that treats agent work as governed, not merely executed: an independent verifier that can only pass or fail, decisions that preserve dissent for a human to arbitrate, a containment boundary so sensitive data never leaves the models you control, and a hash-chained audit of all of it. Brain-agnostic by test: a model earns a tier by passing a scorecard, not by assertion.

The categories are complementary. The comparison below is not a scoreboard; it is a map of what each category ships natively versus what it leaves you to build.

## What is native, and what you build yourself

As of mid-2026. Frameworks move quickly; verify current capabilities before relying on this.

| Capability | Orchestration frameworks | Guardrail tools | Harnessie |
|---|---|---|---|
| Multi-agent orchestration (handoffs, roles, group chat) | Native, and their core strength | Not their job | Native, deliberately minimal (orchestrator / workers / verifier) |
| Independent verifier that can only fail-closed, with no access to the worker's reasoning, blocking progress until it passes | You build it (critics are cooperative and share state) | Output validators, but not a phase gate across a multi-agent run | Native |
| Contested decisions that preserve dissent verbatim and let only a human arbitrate | You build it (frameworks assume machine consensus) | Not their job | Native (AIDR-shaped decision records) |
| Structured PII stripped before egress; secrets halt the run; free-text-sensitive work never leaves models you control | You build it | Partial: PII and injection validators exist (for example Guardrails AI, Lakera), but as filters on one model, not never-egress routing across the run | Native (containment boundary plus contained routing) |
| Brain-agnostic by scorecard: a model is admitted to a tier only by passing a test | Model-agnostic by config, but not gated by a passing scorecard | Not their job | Native |
| Hash-chained, tamper-evident audit of every agent and operator action | You build it | Logging, not a verifiable chain | Native |
| Fails closed when a control cannot be enforced (no sandbox backend, no budget ceiling) | Varies; usually best-effort | Varies | Native, by policy |

The pattern: orchestration frameworks are excellent at the middle row and leave the rest to you; guardrail tools own a slice of one row; Harnessie ships the whole column and keeps it identical underneath any brain.

## When to reach for something else

A comparison page that only argues for itself is not worth reading. Harnessie is the wrong tool in real cases:

- You need fast multi-agent prototyping and do not need verification, containment, or an audit trail. Reach for CrewAI or LangGraph; they are lighter and have far more examples.
- You only need to validate one model's output (schema, toxicity, PII on a single call). Guardrails AI or a provider guardrail is simpler than a whole harness.
- You are all-in on one provider and want that vendor's managed tracing and handoffs. The OpenAI or Claude Agent SDK will have less friction.
- You want a large ecosystem, plugins, and a big community today. Harnessie is new and small on purpose; it competes on the mechanisms, not the mindshare.

Harnessie earns its place only when you need the integrated, verifiable, contained whole, on models you control, and want the guarantees to live in code rather than in a prompt.

## The honest alternative: assemble it yourself

Nothing here is magic. You could build most of it: take LangGraph for orchestration, hand-roll a fresh-context verifier that fails closed, bolt on Guardrails AI for PII, write your own placeholder-based egress boundary, add a hash-chained event log, and maintain a scorecard for every model you swap in.

Harnessie is that assembly, already built, tested, and proven brain-agnostic across eight providers and eleven models, with the safety living at the tool layer where no prompt can switch it off. If the assembly is worth your weeks, build it. If it is worth a `pip install`, that is what this is.

Open source, Apache-2.0. Read every line, self-host it, owe no one.

If you arrived here from Ringer, there is a dedicated page on [how Harnessie and Ringer fit together](ringer.md).
