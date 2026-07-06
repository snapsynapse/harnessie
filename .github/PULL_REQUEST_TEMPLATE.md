## Summary

What this changes and why.

## Evidence it works

Cite the tests and eval scenarios that prove the behavior. For a behavior change, the eval-first rule applies: a scenario that failed before and passes after.

## Checklist

- [ ] `python3 -m pytest -q` passes
- [ ] `python3 -m harness.cli eval` passes
- [ ] Tests and evals assert on structured outcomes, not message wording
- [ ] Docs updated in the same change (README, ARCHITECTURE, GOVERNANCE, SECURITY, EVALS as applicable)
- [ ] CHANGELOG.md updated under the unreleased section
- [ ] If a design invariant or named non-goal changed, a decision record under `decisions/` is opened or referenced

## Known limitations

Anything a reviewer should know that the change does not cover.
