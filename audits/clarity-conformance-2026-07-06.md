# Clarity Conformance — harnessie operator-facing docs — 2026-07-06

Source-mapped composite (WCAG 2.2, GOV.UK Service Standard, Nielsen heuristics, ISO-derived plain-language principles). Five dimensions, eight-level scale (no 0).

## Scope and assumptions

- Artifact: the operator-facing documentation set — README, ARCHITECTURE, GOVERNANCE, SECURITY, ROADMAP, EVALS, INTENT, CHANGELOG.
- Intended users: an engineer or operator adopting and running the harness (technical literacy assumed, per the repo's own audience posture).
- User job: understand what it is, run it, tell what state a run is in, predict what agents and tools will do before acting, and recover from a halted or contested run.
- Not in scope: the code's internal clarity, or end-user-of-a-built-product clarity (there is no such user; the operator is the user).

## Authorities applied

- Nielsen (visibility of system status, match to real world, error recovery) — primary, this is an operational tool.
- GOV.UK Service Standard (journey and handoff clarity) — the run lifecycle is a journey across phases and a human handoff.
- ISO-derived plain-language — the prose density question.
- WCAG 2.2/ACT — least applicable (no GUI); used only for doc navigability.

## Scorecard

| Dimension | Score | Evidence class | Quality |
|---|---|---|---|
| Offer clarity | 4 | manual | high |
| Boundary clarity | 4 | manual | high |
| State clarity | 4 | manual | high |
| Action predictability | 3 | manual | high |
| Recovery clarity | 3 | manual | medium |
| Total | 18 / 25 | — | — |

Conformance level: B — usable with light support and guardrails. No negative dimensions.

## Findings by dimension

Lowest dimensions first, per output rules.

### Recovery clarity — 3

Recoverable, but the contest/arbitration path needs interpretation. Strengths: resume is keyed on a journal ledger; declining is first-class and non-punished; NEXT.md is a deliberate handoff surface; the audit timeline reconstructs what happened. Friction: recovering from a `needs_arbitration` halt requires assembling lore from GOVERNANCE.md (the contest model), adversarial.py behavior, and the deterministic `DR-<phase>.md` resume keying — a first-time operator facing a halted contested phase must read several documents to know that arbitrating means editing a record and re-running. This is documented, but not in one recovery-oriented place. (Nielsen: help users recover from errors; GOV.UK: journey continuity.)

Fix (highest leverage): a single "When a run halts" section — one table mapping each halt status (`needs_human`, `needs_arbitration`, `stuck`, `budget`, `max_steps`) to the exact operator action that resumes it. Would lift this to 4.

### Action predictability — 3

Clear in normal conditions. The pipeline is deterministic and the retry ladder (reformulate → effort → tier → halt) is stated; consent-before-side-effects and allowlisted tools make the common path predictable; the structured refusal grammar makes denials legible. Friction: predicting a *specific* run's behavior requires cross-referencing four files — the workflow YAML, `config/models.yaml`, `OWNERSHIP.yaml`, and the role prompts in `agents/`. Each is documented; the prediction is distributed. (Nielsen: consistency and predictability.)

Fix: a worked "trace one phase end to end" walkthrough naming which file governs each decision point. The `examples/policy-compliance` example is close; make the file-to-decision mapping explicit there.

### Offer clarity — 4

Exceptionally clear and teachable. README's first paragraph is a complete definition; "Design in one breath" gives the whole pipeline in one sentence; Requirements are explicit about platform sandbox limits; INTENT §1–4 nails what it is and what is out of scope; ROADMAP non-goals are enumerated. Minor friction (caps it below 5): the opening sentence front-loads eleven features before the operating thesis (which lands in paragraph 2), so a newcomer meets "adversarial decision records" and "stamped provenance" before the mental model that makes them make sense.

### Boundary clarity — 4

Strong and explicit. Operator-versus-agent authority is a first-class concept (ownership lanes, operator-locked lanes agents cannot reach); INTENT §4 states scope boundaries; the `docs/`-is-public-versus-root-is-private split is documented; SECURITY.md is candid about honest limits (e.g. interpreter writes bypass the per-file check). Handoffs between phases are named. Doesn't reach 5 only because the operator/agent boundary detail is spread across README, GOVERNANCE, and OWNERSHIP.yaml rather than stated once canonically.

### State clarity — 4

A genuine design strength, well-documented. Every loop exit is a named diagnosis (`complete | declined | max_steps | budget | stuck | model_error | no_action | refusal`); `harnessie report` and `harnessie audit` render run state and a composite governance timeline; the journal is an explicit resume ledger. The harness is built to make state legible and the docs reflect that.

One currency defect (not a design flaw): README:57 still says shell-using workflows "fail closed until a Linux backend is wired," which now lags the committed 0.4 Linux backend (bwrap/firejail/docker). A reader checking whether Linux is supported gets a stale answer. Low effort to fix; refresh the Requirements paragraph when the 0.4 line is next touched.

## Support burden and adoption

Support burden: low-to-moderate. An engineer can adopt from README plus the one worked example. Support questions will cluster at two points: (1) the multi-file configuration model when predicting or changing run behavior, and (2) the contest/arbitration recovery path. Both are the two 3-scored dimensions.

Adoption recommendation: adopt with light guardrails (Level B). For a solo operator (the stated audience) the docs are more than sufficient. Before onboarding a second operator, add the two highest-leverage fixes below — they convert the two friction points into self-serve paths.

## Top fixes (priority order)

1. Add a "When a run halts" section: halt-status → resume-action table. Lifts recovery clarity 3 → 4. (highest leverage: turns the specialist-lore recovery path into a lookup.)
2. In the worked example, make the file-to-decision mapping explicit (which of the four config files governs each decision point). Lifts action predictability 3 → 4.
3. Refresh README:57 Requirements paragraph to reflect the committed Linux sandbox backends. Removes the one state-clarity currency defect.
4. Optional: lead README with the one-line operating thesis before the feature enumeration. Minor offer-clarity polish.

## Signature

`clarity: B (18/25) | offer 4 boundary 4 state 4 action 3 recovery 3 | burden low-moderate | adopt with light guardrails`
