# Accessibility Audit Project Context

## Project

- name: Harnessie
- base_url: https://harnessie.com/
- repo_root: .
- app_root: docs

## Audit Scope

- standards: WCAG 2.1 AA
- scan_mode: full
- include_routes:
  - https://harnessie.com/
  - https://harnessie.com/quickstart.html
  - https://harnessie.com/getting-started.html
  - https://harnessie.com/ladder.html
  - https://harnessie.com/guide.html
  - https://harnessie.com/compare.html
  - https://harnessie.com/agent-file-ownership.html
  - https://harnessie.com/brains.html
  - https://harnessie.com/threat-model.html
  - https://harnessie.com/ringer.html

## Output Configuration

- output_mode: markdown+json
- report_path: audits/accessibility/2026-09-07/audit-YYYY-MM-DD.md
- json_path: audits/accessibility/2026-09-07/audit-YYYY-MM-DD.json

## Regression Gate

- fail_on: major
- baseline_policy: No baseline acceptance or automatic refresh.

## References

- conformance_docs: RELEASE_CHECKLIST.md
- manual_testing_guide: audits/accessibility/2026-09-07/manual-checks.md
