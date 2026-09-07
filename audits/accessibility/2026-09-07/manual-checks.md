# Harnessie accessibility review and manual checks

Status: not performed. This is a targeted test plan derived from the 2026-09-07 automated audit, not manual acceptance evidence. The release owner must record results for the final changed routes before 1.3.0 publication. The 1.2.0 waiver does not carry forward.

## Confirmed findings and source repair

| Route | Element | Confirmed issue | Repair location |
|---|---|---|---|
| `/quickstart.html` | `pre:nth-child(19)` | Horizontal code scrolling is not keyboard-focusable | `scripts/build_docs_html.py` code-block renderer |
| `/agent-file-ownership.html` | `pre:nth-child(24)` | Horizontal code scrolling is not keyboard-focusable | Same code-block renderer |
| `/ringer.html` | `pre:nth-child(14)` | Horizontal code scrolling is not keyboard-focusable | Same code-block renderer |
| `/threat-model.html` | `.table-wrap` | Horizontal table scrolling is not keyboard-focusable | `scripts/build_docs_html.py` table wrapper |

Recommended bounded repair: make overflowing code/table containers reachable by keyboard, with visible focus and useful accessible context; regenerate all affected HTML from the producer. Check that Arrow keys scroll the focused container, Tab exits it, and focus order stays understandable. Avoid treating an axe pass alone as a working keyboard experience. The repair has not been applied by this audit.

## Review the 58 incomplete candidates

- Homepage: 22 serious `color-contrast` candidates. Inspect every target in `scan.json`, including checkmark glyphs and content whose contrast axe cannot calculate. Establish whether each conveys information or is redundant decoration. Measure actual foreground/background contrast where meaningful; do not assume every glyph is exempt.
- Threat-model page: 35 serious `color-contrast` candidates in the wide table, including clipped or partially obscured cells. Scroll the table through its full width and inspect each reported cell on its actual background. These are unresolved measurements, not 35 proven contrast failures.
- Homepage video: one critical `video-caption` candidate. Determine whether the mascot clip has speech, meaningful audio or visual information requiring an equivalent alternative. Muting a video does not establish that its content needs no captions. If it is purely decorative, record that content review and use appropriate decorative semantics. Otherwise provide the required caption or alternative. Verify the existing animation pause control and reduced-motion behavior.

Do not silently suppress these findings with a baseline. The current major gate reports failure because four confirmed issues exist. Removing those four alone would leave the serious/critical incomplete review unresolved.

## Manual test plan

| Method | Routes and actions | Criteria to review | Evidence required |
|---|---|---|---|
| Keyboard navigation | All ten sitemap routes: Tab/Shift+Tab through skip link, navigation, links, section navigation and controls; focus/scroll the four affected regions; activate links and homepage pause/resume; confirm focus can leave every control | 2.1.1, 2.1.2, 2.1.4, 2.4.1, 2.4.3, 2.4.7, 3.2.1, 3.2.2 | Route, control, expected behavior, actual behavior and pass/fail |
| Zoom and reflow | All ten routes at 200% browser zoom; additionally inspect narrow 320 CSS-pixel width, text spacing and both orientations. Prioritize navigation, code and threat-model table; essential two-dimensional content must remain operable | 1.3.4, 1.4.4, 1.4.10, 1.4.12, 1.4.13 | Browser/window dimensions, zoom level, clipping/overlap and reachability results |
| Screen reader | All ten routes: headings, landmarks, reading order, links and current navigation. Prioritize homepage glyphs/video/pause control, code blocks and the threat-model table's headers and cells | 1.1.1, 1.3.1, 1.3.2, 2.4.4, 2.4.6, 2.5.3, 4.1.2, 4.1.3 | Screen reader/version, browser/version, route and observed announcements |
| Visual and contrast review | Homepage and threat-model targets listed above; all routes for focus indicators, link differentiation, text-as-images and hover/focus content | 1.4.1, 1.4.3, 1.4.5, 1.4.11, 1.4.13 | Target, measured values, context and disposition for every incomplete candidate |
| Media, timing and motion | Homepage mascot video: inspect actual content, pause/resume, autoplay and reduced-motion behavior. Check the remaining routes for timed or flashing content rather than inheriting an automated N/A | 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.4.2, 2.2.1, 2.2.2, 2.3.1 | Media content review, motion preference, controls and any documented not-applicable rationale |
| Content and cognitive review | All routes: sensory-only instructions, understandable headings/link purpose, consistent navigation and identification, alternative ways to find documentation | 1.3.3, 2.4.5, 2.4.6, 3.1.2, 3.2.3, 3.2.4 | Route-specific issues or observed pass with a bounded rationale |
| Input and interaction applicability | Confirm whether any audited route has forms, pointer gestures, motion activation, or change/error feedback. No form violations were reported; inspect applicable interactions before marking criteria not applicable | 1.3.5, 2.5.1, 2.5.2, 2.5.4, 3.3.1, 3.3.2, 3.3.3, 3.3.4 | Applicable controls and tests, or explicit scope-based not-applicable rationale |
| Independent tool comparison | Compare axe DevTools findings on the four affected routes using a recorded rule-engine version. Do not interpret version differences as a site regression | Automated result cross-check; 4.1.1 review where applicable | Tool/version, routes, counts and explained discrepancies |

## Receipt template

Record tester, UTC date, exact source revision and served-byte digest, OS/version, browser/version, screen reader/version, viewport and zoom, tested routes, each result, and any unresolved limitations. Store screenshots or other evidence with their test identifiers. A checklist completed against today's baseline must be reassessed for routes changed by the final release tranche.
