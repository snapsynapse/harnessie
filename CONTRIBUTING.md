# Contributing to Harnessie

Thanks for your interest. Harnessie is a security-first, brain-agnostic harness, and its guarantees live in code at the tool and registry layer, not in prompts. Contributions are held to that same standard: a change is done when its behavior is proven, not merely written.

## Getting set up

Requires Python 3.11 or newer.

```bash
git clone https://github.com/snapsynapse/harnessie.git
cd harnessie
pip install -e ".[dev]"
```

Prove the harness works before changing it. The suite and the eval scorecards run against a deterministic mock brain with no network.

```bash
python3 -m pytest -q              # unit + integration suite
python3 -m harness.cli eval       # deterministic eval scorecards
```

## The change discipline

Harnessie uses an eval-first change process. Read [EVALS.md](EVALS.md) for the scenario schema.

1. Eval-first for behavior changes. Add or update a scenario that fails before your change (red) and passes after (green). A denial surface without a scenario asserting its structured outcome is not covered.
2. Assert on structured outcomes, not prose. Tests and evals key on stable fields (a refusal's `error` and `boundary`, a phase's stop condition), not on message wording, so a rephrase does not break the suite.
3. Keep policy in the harness. Role permissions, consent, ownership, and sandboxing are enforced at dispatch, so no prompt can opt out. Do not move a guarantee into a role prompt.
4. Fail closed. A control that cannot be enforced on a platform is refused, never skipped. New capabilities follow the same rule.
5. Green before commit. `python3 -m pytest -q` and `python3 -m harness.cli eval` both pass on the commit you propose.

## Consequential and contested changes

Direction-setting or contested decisions are recorded, not just merged. Harnessie keeps AIDR-style decision records under `decisions/`, with independent positions and human-only arbitration. If your change alters a design invariant or a named non-goal (see [INTENT.md](INTENT.md) and [ROADMAP.md](ROADMAP.md)), open or reference a decision record rather than deciding it inside the pull request.

## Style

- Write code that reads like the surrounding code: match its naming, structure, and comment density.
- Comment only to state a constraint the code cannot show. Do not narrate what the next line does.
- Markdown: plain headings, bare `https` URLs, no em dashes.

## Submitting a pull request

- One focused change per pull request.
- Update [CHANGELOG.md](CHANGELOG.md) under the unreleased section.
- Update the docs that describe the behavior you changed (README, ARCHITECTURE, GOVERNANCE, SECURITY, EVALS) in the same change.
- Describe what you changed, the evidence it works (cite the tests and eval scenarios), and any known limitations.

## Questions

Open a GitHub issue with the question label. For anything security-sensitive, see [SECURITY.md](SECURITY.md) for the harness's threat model before filing.
