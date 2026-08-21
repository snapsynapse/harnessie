# Harnessie's Golden Rule for agent work

Read together. Write only what you own.

Shared context makes a group of agents useful. Shared write authority makes their work fragile. Two agents can read the same artifact, form different plans, and contribute complementary results. If both can silently replace the same file, however, the last writer wins and neither agent can prove which work survived.

Harnessie calls its answer the Golden Rule for agent work. The memorable phrase is communications shorthand. The technical mechanism is ownership lanes, enforced below the prompt.

## What the rule means

An agent may use shared workspace context, but it may change only paths where the ownership ledger gives it write authority.

- Agent lanes assign paths to one named agent.
- Operator lanes are read-only to every agent.
- Collaborative lanes are an explicit shared-write exception chosen by the operator.
- Unlisted files follow first-writer-owns. The first agent to create a file becomes its owner.
- An agent that needs another agent's file changed calls `request_change` instead of overwriting it.

The operator remains the root owner. The operator can reassign a path or deliberately declare a collaborative lane. The rule constrains agents, not the human accountable for the run.

## The harness enforces it twice

A prompt can ask an agent to respect ownership. Harnessie makes refusal independent of whether the model cooperates.

1. Direct tool writes are checked against `OWNERSHIP.yaml`. A cross-lane write is refused with the owner's identity and the `request_change` remedy.
2. Child commands receive agent-specific read-only overlays for operator lanes, other-agent lanes, and other agents' first-writer claims. This covers shell calls, deterministic checks, and verifier execution. If the host cannot prove the required nested read-only confinement, the child process does not run.

Parallel workflow members execute in isolated phase workspaces. When a parallel group opts into declared `writes:`, every member must declare its intended paths and overlapping declarations refuse before workspace creation or model dispatch. Ownership lanes still apply inside each isolated phase workspace.

## How this differs from adjacent patterns

| Pattern | Write model | Where a collision appears |
|---|---|---|
| Prompt-only cooperation | Agents are asked not to interfere | A model can ignore or misunderstand the rule |
| Worktree isolation | Each parallel agent writes a separate checkout | Conflicts appear when results are integrated |
| Shared-state conflict detection | Multiple writers are allowed; stale or competing writes are rejected | At the attempted shared-state update |
| Harnessie ownership lanes | Write authority is declared or acquired by first write; cross-lane writes are denied | Before a direct write, inside child-process confinement, or before a declared parallel group dispatches |

Harnessie does not claim that cross-agent overwrite prevention is a unique problem or that ownership is the only valid coordination design. Its specific claim is falsifiable: within the shipped boundary, an agent cannot write across an ownership lane through a built-in direct write or a confined child process, and declared overlapping parallel writes refuse before dispatch.

## Boundaries and exceptions

- Collaborative lanes deliberately permit co-editing. Their writes are events, not exclusive claims.
- Parallel agents do not live-edit one shared active workspace. They work in isolated phase workspaces and their results are integrated after the group completes.
- Installed `harnessie.tools.v1` plugin implementations run in process as operator-trusted code. Registry policy mediates their calls, but ownership-lane OS confinement does not sandbox the implementation itself.
- Ownership governs writes, not truth. Deterministic checks and an independent verifier still decide whether owned work earns passage through the phase gate.

## Verify the claim

The enforcing paths are [harness/ownership.py](../harness/ownership.py), [harness/sandbox.py](../harness/sandbox.py), and the operator-owned [OWNERSHIP.yaml](../OWNERSHIP.yaml). The threat-model claim and proof references are collected in [Threat model](threat-model.md).

Literal
```bash
python3 -m pytest -q tests/test_ownership.py::test_cross_agent_write_denied_at_dispatch tests/test_ownership.py::test_run_shell_receives_agent_specific_readonly_roots tests/test_runner.py::test_parallel_declared_write_conflict_refuses_before_dispatch tests/test_sandbox.py::test_readonly_lane_backend_failure_blocks_child
```
These deterministic tests prove direct denial, compilation of agent-specific read-only roots, pre-dispatch parallel conflict refusal, and fail-closed behavior when lane confinement is unavailable. Platform-backed sandbox tests add a live interpreter probe when the required backend is present.

## The short version

Harnessie's Golden Rule for agent work is simple enough to remember and strict enough to test:

**Read together. Write only what you own.**

The rule is the explanation. Ownership lanes are the enforcement.
