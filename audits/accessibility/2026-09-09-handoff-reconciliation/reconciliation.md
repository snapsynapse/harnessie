# Harnessie accessibility handoff reconciliation

Status: processed locally on 2026-09-09. This is a current-source audit and handoff disposition, not production deployment, human assistive-technology acceptance or a WCAG conformance claim.

## Source

The temporary source queue was `handoffs/2026-09-07-accessibility-review.md`. It described the post-mitigation state after PR #13 and deferred 35 threat-model contrast candidates, one homepage video-caption applicability candidate and human manual checks.

## Claim reconciliation

| Handoff claim | Current observation | Verdict |
|---|---|---|
| Four confirmed keyboard issues and 22 homepage candidates were mitigated | The mitigation audit and current regression checks preserve the repairs. | DONE |
| PR #13 and its CI, CodeQL, Scorecard and Pages runs passed | GitHub and local history retain the cited successful receipts. | DONE |
| Latest release was 1.2.0 and no package release followed the mitigation | Releases 1.3.0, 1.3.1 and 1.4.1 followed. Current main is the verified 1.4.1 closeout. | DRIFTED |
| Ten live routes matched the mitigation revision | The dated receipt remains valid, but several release-document routes changed later. Current-source scanning was required. | DRIFTED |
| Thirty-six candidates remained | The current pre-repair scan found those 36 plus 27 guide-table candidates introduced by later documentation changes. | DRIFTED |
| The automated gate was inconclusive with no confirmed candidate-scan violations | The current pre-repair and post-repair scans also have zero confirmed violations and zero route errors. The raw gate remains inconclusive because clipped table content produces serious incomplete results. | DONE |
| Manual keyboard, actual 200% zoom/reflow, screen-reader, media and visual checks remained open | Automated measurement and bounded interaction evidence progressed the queue, but human browser and assistive-technology acceptance remains open. | PENDING, TRANSFERRED |
| GuideCheck remained required before package publication | The 1.4.1 release separately earned hosted GuideCheck Level 4 before publication. | DRIFTED, DONE ELSEWHERE |

## Historical receipt claims preserved from the handoff

- Signed mitigation source: `8d89e417b0c9deb4f7c565f3af10b858a439e8ee`, with a valid GitHub signature verification.
- Delivery: [PR #13](https://github.com/snapsynapse/harnessie/pull/13) merged at 2026-09-07T23:56:21Z as `a734a8f28fd9955b3a152ed15e96742b3c370a92`.
- Exact-merge provider receipts: [CI 34171678049](https://github.com/snapsynapse/harnessie/actions/runs/34171678049), [CodeQL 34171678056](https://github.com/snapsynapse/harnessie/actions/runs/34171678056), [Scorecard 34171678062](https://github.com/snapsynapse/harnessie/actions/runs/34171678062) and [Pages 34171677463](https://github.com/snapsynapse/harnessie/actions/runs/34171677463) passed.
- The optional PR model verifier skipped checkout and invocation because its configuration was absent. It supplied no model-review evidence.
- At handoff time no package release followed the mitigation and the latest release was 1.2.0. That boundary later drifted through the separately verified 1.3.0, 1.3.1 and 1.4.1 release sequence.
- Baseline identity: remote-main `2413c43278f08e128f80d711fd142a2286f3eaa2`; skill-a11y-audit 3.1.0 at `6af2c95a56ff058cddf0c6febc71512db1d6d19b`; axe-core 4.12.1; Puppeteer 25.10.0; viewport 1280 by 800; raw scan SHA-256 `2d160291f52102089dfd863ad1c979d20bd6d5231386cc358733f5ffe54a85af`.
- Historical candidate accounting: 58 baseline incomplete nodes reconciled as seven measured contrast resolutions, 15 redundant-decoration resolutions and 36 pending nodes. The tracked mitigation artifacts preserve the complete mapping and eight automated keyboard cases.
- Historical live readback: all ten routes matched the merged mitigation source at 2026-09-07T23:58:33.133237+00:00. An initial Python DNS lookup failed; a subsequent curl readback succeeded with normal certificate verification. That was deployment-byte evidence, not a second accessibility scan.

| Historical route | Served SHA-256 |
|---|---|
| https://harnessie.com/ | `c47b8cfbc4dafe1a03430b5f725e6b1fa73a34779b5dca45b7db04f592ac63da` |
| https://harnessie.com/quickstart.html | `608f6b4e58f7ebd4e92f72909219f63d7576573dd20d1cddba52fb037027c968` |
| https://harnessie.com/getting-started.html | `66c7abba86e5fc0a937e69697d54279ab75e10322ad2242ca2fc0c05713a8893` |
| https://harnessie.com/ladder.html | `5938942da15423dfc5ecc863f375b8871bb6a295d9c50308eaa064b5b54d4dd6` |
| https://harnessie.com/guide.html | `09760afaff502d06071ed9f1fbf3e54a9fdbc84a9ebf29c0f4fbea0091d17f31` |
| https://harnessie.com/compare.html | `6f0158f9536568db903fc5427387ab374a034be1ed15b5715f7a2fb6060d6d65` |
| https://harnessie.com/agent-file-ownership.html | `38835a8f6fac83812450375fd567a4ade523fe730cc97dc131973666ec326172` |
| https://harnessie.com/brains.html | `65d38309959329fcebf7c37997a8a040ab5849517b00882792547d0e85b6993b` |
| https://harnessie.com/threat-model.html | `55814f09a68f22b01517fa8a0e77e976784e702f5bfb032e1dff58e729e9550f` |
| https://harnessie.com/ringer.html | `4db1b55924a43ff9cc0059ea787f0a35896a1c30e18fa746c0c4fc78ea33a5be` |

## Current-source audit

The initial 2026-09-09 scan covered all ten configured routes with skill-a11y-audit 3.1.0, axe-core 4.12.1 and Puppeteer 25.10.0.

| State | Confirmed violations | Blocking incomplete | Route errors | Detail |
|---|---:|---:|---:|---|
| Before repair | 0 | 63 | 0 | Homepage video 1; guide contrast 25 and link cue 2; threat-model contrast 35 |
| After repair | 0 | 60 | 0 | Guide contrast 25; threat-model contrast 35 |

The scanner correctly remains inconclusive because its background calculation cannot see through horizontally clipped table content. No threshold or baseline was lowered.

## Dispositions and repairs

### Sixty clipped-table contrast candidates

[review-after.json](review-after.json) records an explicit disposition for each of the 60 selectors and 180 individual measurements at widths 1280, 640 and 375. Width 640 is documented only as a 200% reflow proxy. Each target was brought into the horizontal scroll viewport before measurement. Wide cells can still require horizontal movement at narrow width; this is why actual human zoom/reflow remains in the transferred queue.

- Result: 60 `resolved_measured_contrast` dispositions.
- Minimum observed ratio: 6.08:1.
- Required ratio: 4.5:1.
- Confirmed contrast defects: 0.

### Two guide-table links

Both links had adequate contrast against the page background, but their 2.40:1 difference from surrounding text was below the 3:1 color-only distinction. The documentation renderer now gives links inside table cells the same persistent underline as prose and list links. The post-repair scan no longer reports `link-in-text-block` candidates.

### Homepage mascot video

[media-evidence.json](media-evidence.json) establishes that the served ten-second derivative has one video stream and no audio stream. Representative frames show animated branding that duplicates the static fallback and nearby content without adding instructional, status or functional information. The video is therefore marked decorative while the static image alternative and separate pause/play control remain.

The unserved original contains an audio track. Its semantic audio content was not assessed because local transcription dependencies and model weights were absent and the audio is outside the published surface. If that original is ever served, its audio and caption requirements must be reviewed before deployment.

### Keyboard and motion regression evidence

The supplemental browser review records eight passing overflow-container cases across desktop and narrow layouts. Tab reaches each repaired container, focus is visible, ArrowRight scrolls, Tab and Shift+Tab exit, and text remains unchanged. The homepage animation also pauses, resumes, reflects state in its accessible label, and removes autoplay under reduced-motion preference.

## Remaining authoritative queue

The temporary handoff is exhausted by completing or transferring every item. Human-owned acceptance remains in `NEXT.md`, with procedures in `audits/accessibility/2026-09-07/manual-checks.md`:

1. Human all-route keyboard and focus-order review.
2. Actual 200% browser zoom/reflow and orientation review.
3. Screen-reader review with recorded browser and assistive-technology versions.
4. Independent axe DevTools comparison with a recorded rule-engine version.
5. Content, cognitive, text-spacing, hover/focus and interaction-applicability checks.
6. Re-review the original audio-bearing video only if that asset enters a served surface.

These are post-release evidence tasks, not a retroactive blocker on the separately verified 1.4.1 release. No issue was created, no deployment occurred and no full-conformance claim is made.

## Evidence inventory

- `scan.json`: current-source pre-repair raw scan.
- `scan-after.json`: post-repair raw scan.
- `audit-2026-09-09.md` and `.json`: generated report and machine-readable evidence matrix.
- `review-driver.cjs`: supplemental measurement and interaction driver.
- `review-before.json`: evidence of the two link-cue failures before repair.
- `review-after.json`: per-candidate contrast dispositions and post-repair interactions.
- `media-evidence.json` and `media-frames/`: media stream and visual applicability evidence.
- `guide-*.png` and `threat-model-*.png`: right-scroll table views at the three measured widths.
