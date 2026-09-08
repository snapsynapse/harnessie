# Offline open-record AIDR export

Date: 2026-09-08. Scope: Harnessie core, local implementation. Sam accepted this packet after deferring accessibility for this session. Baseline: `f1e5be1ca2cd964b5b2e6a7dcf0f007e215bf679`, stable release 1.3.1. Publication is outside this packet.

## Accepted contract

Export one existing open `runs/RUN_ID/decisions/DR-PHASE.md` into an operator-selected, unused `decisions/AIDR-NNNN-short-slug.md`. Require an explicit declared human arbiter. Preserve recorded positions and objections; map repeated role instances to unique participant labels and retain original roles. Bind the consumed source record and event journal with SHA-256. Preserve the source, journal and runner state. Make no model calls and never resume the run.

Reject non-open records, any arbitration content or decision metadata, ambiguous parsing, missing identity fields, unresolved evidence, broken event chains, symlinks, unsafe paths, and existing IDs including different slugs. Stage and validate output before exclusive atomic creation, serialize cooperating exporters, and recheck consumed source/evidence before publishing the local file. Refusal must not alter existing files or expose a partial final artifact.

The target is AIDR SPEC 0.1.0 at `a67c41d339d3e70bc3baaf07e652f9cf9d13a5bb`. The Python runtime validates a strict supported subset without requiring Node. Unmodified reference tools and their license are pinned with SHA-256 under `tests/fixtures/aidr-0.1.0/` for independent acceptance tests. The specification remains authoritative over the linter.

## Evidence limits

- Participant identities are reported routing metadata, not authenticated identities. The arbiter argument is a human designation by the caller, not proof of humanity.
- Runtime position contexts are separate, but shared-file access is not blind-review isolation. Export must qualify existing source assertions rather than manufacture independence evidence.
- Existing objection text is truncated to 500 characters and event copies to 200. Export preserves recorded text; it cannot recover original responses or missing round attribution.
- Export-time hashes bind the snapshot consumed. The runtime did not bind the original assembled record digest, so these hashes cannot authenticate original generation.
- A conforming structure, convergence, or successful export supplies no arbitration or permission to resume/publish. Nonempty arbitration is refused, never silently stripped.
- Local filesystem safety depends on supported no-follow/descriptor and atomic-publication primitives. Coordination covers cooperating exporters, not arbitrary processes with authority to rewrite the entire project.

## Validation

Acceptance was written before implementation: the pinned-reference digest test passed; both actual-runner export acceptance cases and the new governance eval test failed with `ModuleNotFoundError` because the exporter did not exist. The cases exercise repeated roles, dissent, byte preservation, network/runner sentinels, reference lint and an original run that remains halted after export.

Final local results:

| Check | Observed result |
|---|---|
| Full suite, Python 3.13.9 on macOS with OS sandbox access | 708 passed, 1 skipped, 28 expected failures |
| Deterministic evaluations | 66/66 passed, including four new export cases; inverted expectations fail |
| Independent scoped verification | PASS; 135 focused exporter, CLI and pinned-reference tests plus separate adversarial probes |
| Authoring/schema validation | 9 documents valid |
| Trust/inward/ecosystem manifests | 21 trust files, 16 inward files, 4 ecosystem components valid |
| Generated docs and offline search | 9 generated pages current; 10 sitemap pages, zero defects |
| Dependency lock consistency | Runtime, development and release lock definitions valid |
| Local wheel/source build | Built with the development lock's installed build backend, without build isolation; Twine and artifact inspection passed |
| Installed-wheel consumer | Fresh environment passed scaffold, manifests, observer and exporter; duplicate export refused and existing/source/evidence bytes survived |
| Diff whitespace check | Passed |

The one skipped test requires explicit live-provider opt-in. The 28 expected failures belong to deferred features. No live model evaluation ran. Initial environment failures came from missing Hypothesis and pip; the development lock and bundled pip bootstrap restored the test environment. An initial installed export refused macOS's symlinked temporary path; the smoke fixture now uses its canonical temporary root, preserving the exporter guard.

Independent review found and reproduced a real ambiguity: indented/setext Arbitration headings and an unclosed code fence could publish despite the section parser seeing an empty Arbitration. The repaired strict subset refuses unquoted ATX/setext/list-nested headings, fences, raw HTML/comments and ambiguous Unicode separators. Publication-level regressions prove refusal, zero final/staging files and input preservation. Additional independent probes covered directory replacement, symlink replacement and duplicate evidence references. These restrictions are documented in [AIDR_EXPORT.md](../AIDR_EXPORT.md).

[Machine-readable verification state](aidr-export-implementation-2026-09-08.json) records source digests and the local artifact hashes. The artifacts retain the checkout's version field 1.3.1 for this smoke test; they are development builds and are not the published 1.3.1 distributions. The wheel's exporter bytes match the independently reviewed source.

## Delivery boundary

Accessibility and its handoff remain deferred and untouched. Live panels, arbitration import, model selection, bidding, runner production changes, downstream version bumps, provider changes and external publication are outside this packet.
