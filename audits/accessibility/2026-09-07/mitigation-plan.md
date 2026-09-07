# Harnessie accessibility mitigation plan

Status: steps 1-3 approved by Sam and implemented locally on 2026-09-07. Scope: Harnessie source repairs and verification for 1.3.0 preparation. The original scan and report remain unchanged baseline evidence. [Candidate results](../2026-09-07-mitigation/audit-2026-09-07.md) show zero confirmed violations, 22 resolved homepage candidates and 36 remaining review candidates. The major gate remains inconclusive.

## Baseline and proposed division

The [2026-09-07 audit](audit-2026-09-07.md) scanned all ten deployed sitemap routes with skill-a11y-audit 3.1.0 and axe-core 4.12.1. Live bytes matched main `2413c43278f08e128f80d711fd142a2286f3eaa2`. It found four confirmed serious keyboard-access issues and 58 incomplete candidates. Incomplete means review required, not a confirmed violation.

| Group | Baseline instances | Proposed treatment |
|---|---|---|
| Unfocusable scrolling code blocks and table | 4 confirmed serious | Repair shared documentation renderer and verify keyboard operation |
| Homepage contrast checks on non-text glyphs | 15 incomplete | Inspect adjacent meaning; correct decorative markup or measure meaningful symbols |
| Homepage contrast checks blocked by gradient | 7 incomplete | Simplify the affected panel background and measure text/link contrast |
| Threat-model table contrast obscured by clipping | 35 incomplete | Hand off full-width/scroll-position review after the focus repair; retain any unresolved instances |
| Homepage video caption applicability | 1 incomplete | Hand off actual media-content and accessible-alternative review |

The implementation packet targets all four confirmed issues and 22 of the 58 review candidates. It does not promise that 22 candidates will disappear or be accepted. Thirty-six candidates are initially assigned to the follow-up queue; rescanning determines the actual remainder.

## 1. Repair keyboard access to scrolling regions

Owner source: `scripts/build_docs_html.py`; regenerate its nine documentation HTML outputs together. Confirmed affected routes are `/quickstart.html`, `/agent-file-ownership.html`, `/ringer.html` and `/threat-model.html`; their exact selectors are in [manual-checks.md](manual-checks.md).

- Add native sequential keyboard focus to code blocks and table scroll containers using `tabindex="0"`. Keep native code/table semantics and a visible focus outline. Do not use positive tabindex or make the table cells separately focusable.
- Where a scroll container needs an accessible name, derive it from the nearest document heading or a concise code/table label. Do not add an ARIA region to every code block or create a page full of redundant landmarks.
- Prefer deterministic generated markup and CSS. Check the added tab stops on short blocks too; avoid introducing JavaScript-only access or a complex overflow-tracking subsystem for this repair.
- At normal and narrow viewports, verify Tab reaches each affected container, Arrow keys reveal its overflow, Shift+Tab/Tab leave it, focus is visible, and content remains readable and copyable. Preserve table headers and document reading order.

Acceptance: the four original `scrollable-region-focusable` instances are absent from a fresh scan; keyboard behavior is demonstrated for all four affected containers. Rerun all ten routes because the producer is shared. Newly introduced accessibility findings are not accepted automatically.

## 2. Resolve the bounded homepage contrast candidates

Owner source: `docs/index.html` only. Preserve product copy, guide version/trust artifacts, media assets and current release identity.

### Seven gradient candidates

The `bgGradient` candidates occur in `.install-featured`: its heading, two explanatory paragraphs, the GuideCheck link and three trust-chip containers. Replace the light green gradient with a similar opaque solid background, retaining the panel's layout. Give trust chips an opaque compatible fill if necessary for deterministic measurement. Measure the actual inherited text, muted-text and link colors against their resulting backgrounds; darken only a color that fails its applicable threshold.

Acceptance: all seven original targets have a supported contrast measurement with sufficient contrast, or a documented unresolved disposition. Verify ordinary text at 4.5:1 and qualifying large text at 3:1; inspect link/focus presentation as well. A vanished automated candidate alone is insufficient evidence if its text was removed or hidden.

### Fifteen glyph candidates

The `nonBmp` group contains eight checkmarks, three terminal status dots and four pipeline arrows. Source text beside these glyphs appears to carry their meaning, but verify that for each instance before editing.

- Hide only redundant decoration from assistive technology. Keep adjacent status text and the pipeline's understandable sequence intact. Do not blanket-hide `.g`, because that class also styles the terminal prompt.
- Prefer simple decorative CSS/SVG shapes or removal of redundant glyphs where that preserves the design and meaning. `aria-hidden` alone is not a contrast repair; assess whether a meaningful visual symbol still needs contrast.
- If a symbol conveys information absent from adjacent text, preserve that information with a readable label and adequate symbol contrast. Route an ambiguous case to the handoff rather than suppressing the audit rule.

Acceptance: every one of the 15 baseline targets has a per-target disposition: redundant decoration with preserved equivalent meaning, meaningful symbol with measured contrast, or unresolved review. Confirm that the visible wording and accessible reading order still explain each state and pipeline step.

## 3. Verify and reconcile the remaining queue

- Preserve `scan.json`, both baseline reports and their provenance hashes. Write the candidate rescan into a distinct directory, even if it runs on the same date.
- Use the same tool/rule-engine versions and all ten routes. Record the candidate source fingerprint, served local-build identity, viewport and actual gate status. A local preview pass is not a production deployment result.
- Check generated-doc freshness, existing renderer/documentation checks and the search contract. Add a focused regression only where it protects keyboard-access semantics; do not write tests that merely duplicate CSS strings.
- Inspect the four keyboard repairs at normal and narrow widths. Reconcile all 58 original candidates by route, rule and target; do not subtract counts without matching evidence or treat a changed selector as resolution.
- Update the temporary review handoff with the actual remaining candidates. Retain the 35 table contrast candidates and one video candidate until their review is completed, even if a layout change causes axe to stop reporting some of them without a documented reason.
- Report the four-confirmed-issue result separately from the overall major gate. That gate can remain inconclusive while serious/critical incomplete evidence is unresolved. Do not weaken it, accept a baseline or imply full conformance.

## Completion and boundaries

Sam approved steps 1-3 as one bounded local implementation packet. Completion means reviewed source changes, generated outputs, fresh Markdown/JSON evidence, per-candidate dispositions and an accurate remaining handoff. Commit, push, merge and deployment are separate delivery actions after review.

The [manual test plan](manual-checks.md) remains required for release acceptance. Full screen-reader testing, video-content decisions and unresolved table contrast are follow-up work. GuideCheck remains outside this implementation packet and required before 1.3.0 package publication. Placing work in a handoff or on the roadmap is not acceptance of that risk or permission to release.
