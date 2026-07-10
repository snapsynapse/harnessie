# Harnessie and Ringer

If you found Harnessie through Ringer, you are in the right place. The two are built to fit together.

## The same conviction

Ringer and Harnessie start from the same belief, reached independently: a frontier model earns its tokens on orchestration and judgment, most execution does not, and the only result worth trusting is one that has been checked by running it, never one an agent claims is done. Ringer says it plainly: the check is the contract, and exit code zero is the only thing it believes. Harnessie holds the identical line at its gate.

When two tools arrive at the same core conviction on their own, it is usually because the conviction is right. So this is not a rivalry. It is two tools on one foundation, leaning in different directions.

## Different emphasis

Ringer optimizes the swarm. Parallel execution across a set of engines (Codex CLI, Grok Build, OpenCode, or your own), local by default, a live dashboard, throughput. It is the fastest way to get a lot of mechanical, verifiable work done cheaply and in parallel on your own machine.

Harnessie optimizes governance. An independent verifier agent on top of the deterministic check, decisions that preserve dissent for a human to arbitrate, a containment boundary that lets you reach for a cloud model without letting sensitive data reach it, and a hash-chained audit of every agent and operator action. It is the harness for when the work itself must be governed, not just executed.

Same foundation, opposite leans. Ringer goes wide and fast. Harnessie goes careful and accountable.

This division is not only our framing. Declining to ship an official sandbox and credential policy, Ringer's maintainer [drew the same line](https://github.com/NateBJones-Projects/ringer/pull/20#issuecomment-4938695178): "the operator owns the security policy of the runtime they attach." Harnessie is built for the operator's side of that line.

## How they compose

- A shared standard. Both speak AIDR, the one-file decision-record format: independent positions, preserved dissent, human arbitration. A decision recorded alongside Ringer reads the same as one Harnessie writes, and AIDR's recipes include a [worked example running a position sweep as a Ringer swarm](https://github.com/snapsynapse/aidr/blob/main/RECIPES.md).
- Independence, then governance. Ringer's whole model is running a task across independent engines, which is exactly the raw material a governed decision needs: several genuinely independent takes. Harnessie's contested-decision mode turns independent outputs into a decision record with dissent preserved and a human arbitrating. Ringer produces the independence; Harnessie governs it into a call you can defend.
- Divide the run. Use Ringer for mechanical throughput, and Harnessie for the steps that need a contained boundary, an independent model-verifier, or an audit you can hand to someone else.
- A verifier in Ringer's own language. `harnessie verify` is a standalone command with Ringer's native contract: exit code zero is the only pass. Point it at a workspace and a claims file; it runs your deterministic checks sandboxed, then a fresh-context model tests each claim against the artifacts. Because it is just an exit code, it drops into a Ringer manifest as a task's `check`:

```json
{
  "key": "governed-step",
  "spec": "...task for the worker engine...",
  "check": "harnessie verify --workspace {taskdir} --criteria acceptance.md --models models.yaml"
}
```

The worker's own claims stop being the evidence; a model that never saw the worker's reasoning has to reproduce them. Fail-closed: 0 verified, 1 failed, 2 cannot-verify (nothing was observed, so nothing is asserted). For GitHub-hosted repos the same contract ships packaged as a one-file-install Action: [harnessie-verify-action](https://github.com/snapsynapse/harnessie-verify-action).

## Verifying an agent-produced pull request

The same command reviews PR-shaped work anywhere. The recipe: check out the PR head, stage its diff alongside it (`git diff <base>..HEAD > PR.diff`, so the verifier can judge change-surface claims without git), distill the PR body's claims into a criteria file, then:

```
harnessie verify --workspace <checkout> --criteria claims.md \
  --check "python3 -m pytest tests/ -q" --models models.yaml
```

The report answers claim by claim: reproduced, refuted, or not verifiable in this environment, with the evidence named. The first public run of this recipe [refuted a claim in its own author's pull request](https://github.com/NateBJones-Projects/ringer/pull/4), which was the point: a verifier that has never failed its own author is a rubber stamp. The decision record behind the feature (four providers' independent positions, preserved dissent, human arbitration) is public: [AIDR-0006](https://github.com/snapsynapse/harnessie/blob/main/decisions/AIDR-0006-standalone-verifier-surface-for-agent-produced-prs.md).

## If you came from Ringer

You already have parallel execution and verification-by-check. Harnessie adds four things, for when you need them:

- An independent verifier agent, not only a shell check: a fresh-context model that judges the artifact against your acceptance criteria and can only pass or fail it, never wave it through. Available inside a governed run, or standalone as `harnessie verify`.
- A containment boundary: PII stripped to placeholders before any model sees it, a secret in an outbound payload halts the run, and free-text-sensitive work stays on the models you control. Use a frontier model without handing it your data.
- Decisions, not only tasks: when a step is a judgment call rather than an implementation, run it as a contested decision with preserved dissent and human arbitration.
- A tamper-evident audit: a hash-chained log of every action, agent and human, that you can verify and hand to a reviewer.

If you never need those, Ringer alone is the lighter tool, and that is the honest recommendation.

## See also

- [How Harnessie compares](compare.md) to agent frameworks and guardrail tools, for the wider landscape.
- [Ringer](https://unlock-ai.natebjones.com/guides/ringer), by Nate Jones.
