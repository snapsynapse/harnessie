---
name: verification-gates-fail-closed
type: decision
source: initial architecture session 2026-07-06
date: 2026-07-06
---

# Verification gates fail closed

Anywhere the harness cannot prove an outcome, it treats it as failure: unparseable verifier verdicts fail, denied approvals fail, a needs_human phase halts the workflow before later phases build on unverified work. Rationale: with cheap or open-source workers, the dominant failure mode is confident, plausible, wrong output; the harness's value is refusing to let that compound.
