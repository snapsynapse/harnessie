---
name: Bug report
about: A behavior that does not match what the harness documents
title: ""
labels: bug
assignees: ""
---

## What happened

A clear description of the behavior you observed.

## What you expected

What you expected instead, and where the docs led you to expect it (link the section if you can).

## Reproduction

Steps, and the smallest workflow or command that triggers it:

```bash
# e.g. python3 -m harness.cli run workflows/... --goal "..."
```

If a run is involved, the stop condition and the relevant lines from `harnessie audit <run_id>` are more useful than a screenshot.

## Environment

- OS and version:
- Python version (`python3 --version`):
- Harnessie version or commit:
- Sandbox backend, if shell was involved (`python3 -c "from harness import sandbox; print(sandbox.backend_name())"`):

## Anything else

Logs, the failing eval scenario, or a hypothesis about the cause.
