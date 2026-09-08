# Harnessie 1.3.0: offline run observation and release integrity

Release scope authorized by Sam. Publication is in progress; exact results are recorded in [release execution](audits/release-1.3.0.md). Source and guide identity are 1.3.0.

## Included changes

- Offline `harnessie observe RUN_ID` verifies an existing journal snapshot and writes cited JSON and Markdown summaries while preserving source bytes and halted or incomplete states. Successful observation means the summary was produced, not that the run passed. It makes no model calls.
- Structured verdict parsing refuses non-string claim statuses and evidence paths containing NUL without uncaught exceptions. Bounded deterministic property tests and minimized ordinary regression fixtures cover these cases.
- Reviewed runtime, development and release locks enforce dependency versions and SHA-256 hashes in controlled environments. uv 0.11.15 addresses the entry-point traversal advisory found during lock adoption. A separate package job retains public-constraint consumer coverage.
- The release workflow attests the final wheel, source archive, CycloneDX SBOM and checksum file, and verifies expected repository, workflow, tag and commit identity before asset handoff or recovery. Hosted acceptance is pending a qualifying release execution.
- The approved accessibility mitigation makes generated code blocks and scrolling tables keyboard-focusable with visible focus, simplifies the homepage panel background, and preserves status text while replacing redundant glyphs with decorative shapes. Local checks resolve four serious violations and 22 review candidates; Sam deferred the remaining 36 table/video candidates and manual acceptance as nonblocking follow-up.

## Compatibility and boundaries

- AIDR-0009 continues to defer bidding, commentary, follow mode, automatic runner integration and model selection.
- Verdict parser identity advances to 3. Prior parser-specific scorecard claims require new evidence against this parser identity.
- Historical release assets without original build provenance, including 1.2.0 assets, refuse on the new recovery path and require a separately reviewed recovery decision.
- Dependency locks cover controlled Python dependencies, not the host, interpreter bootstrap or an entirely hermetic build.
- Existing 1.x authoring and plugin compatibility contracts remain in effect. The observer does not grant approval or alter routing.

## Release evidence to complete

| Evidence | Status |
|---|---|
| Final release revision and signature | Pending |
| Exact-candidate tests, evals, manifests, generated docs and package consumer | Pending; maintenance CI is earlier baseline evidence |
| Integrated a11y source and automated findings | [Baseline audit](audits/accessibility/2026-09-07/audit-2026-09-07.md) completed: 4 serious violations and 58 incomplete candidates; [local mitigation](audits/accessibility/2026-09-07-mitigation/audit-2026-09-07.md) resolves all 4 violations and 22 candidates; gate remains inconclusive on 36 candidates, explicitly deferred by Sam for this release |
| Keyboard, 200% zoom/reflow and screen-reader evidence | [Targeted manual plan](audits/accessibility/2026-09-07/manual-checks.md) prepared; tests not performed; Sam explicitly deferred this review for 1.3.0 |
| Final guide bytes, sidecar, repository pins, DNS TXT and hosted GuideCheck | Current 1.2.0 guide reverified separately; [profile-2.0.0 candidate](audits/guidecheck/2026-09-08/README.md) prepared locally. Final served/DNS/hosted acceptance required before package publication |
| Live discovery/Siteline evidence | Pending reconciliation against release checklist |
| Four final release-asset digests and original-build verification | Pending |
| PyPI integrity, attestations and clean public-index consumer | Pending |
| Verify Action and Homebrew propagation | Pending core publication and their own checks |

The GitHub Release must remain unpublished until the GuideCheck checkpoint passes because its publication event starts the package workflow. A signed tag and guide deployment, if separately authorized for that checkpoint, do not establish package publication. Verify Action follows core publication; Homebrew follows the immutable PyPI archive. Engine wrappers retain their independent release train.

Preparation baseline and file map: [release preparation](audits/release-preparation-2026-09-07.md). Operational gates: [release checklist](RELEASE_CHECKLIST.md).
