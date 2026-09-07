# Next stable release preparation

Scope: Harnessie core, with downstream sequencing references. Prepared 2026-09-07. Sam approved the 1.3.0 preparation scope on 2026-09-07 and clarified that the completed work is the skill-a11y-audit 3.1.0 tool release. The Harnessie audit must still be performed using that tool. Markdown plus JSON output is approved. GuideCheck remains outside this implementation tranche, but its final matching result is required before 1.3.0 package publication, including PyPI and Homebrew. This is local preparation authority, not stable-release publication authority.

## Verified preparation baseline

- Remote main: `2413c43278f08e128f80d711fd142a2286f3eaa2`, refreshed from origin. The local `codex/patch-lock-generator` source tree is identical to that merge before this preparation document.
- Latest GitHub release is v1.2.0. No open core PRs were returned by the live query.
- Maintenance delivery: [PR 10](https://github.com/snapsynapse/harnessie/pull/10) and [patched tooling PR 12](https://github.com/snapsynapse/harnessie/pull/12).
- Exact-main [CI](https://github.com/snapsynapse/harnessie/actions/runs/34163730953), [CodeQL](https://github.com/snapsynapse/harnessie/actions/runs/34163730901), [Scorecard](https://github.com/snapsynapse/harnessie/actions/runs/34163730934), and [Pages](https://github.com/snapsynapse/harnessie/actions/runs/34163730494) report success. These precede final release content and do not qualify a future candidate.
- Offline ecosystem inspection finds clean local downstream checkouts: Verify Action at `bc6f94f93cad`, core pin 1.2.0; Homebrew at `07135adfb0bf`, core pin 1.2.0; engine wrappers at `9eab8ac9bea4`, independent version 0.1.0. This is local inspection, not refreshed downstream provider evidence.

## Work that can proceed now

1. Review the draft release copy below and the compatibility boundaries against existing implementation and acceptance fixtures.
2. Use the version map below to prepare one coordinated release tranche after shared-file ownership is released. Do not perform a bulk substitution: historical evidence and minimum supported versions must retain their original versions.
3. Prepare the core artifact and downstream verification sequence below. No external model is needed for the deterministic candidate checks.
4. Keep sole-maintainer branch protection as its existing independent proposal. It is not a reason to expand this release or delay drafting.

## Draft release copy

The editable candidate copy is now [RELEASE_NOTES-1.3.0.md](../RELEASE_NOTES-1.3.0.md). It preserves pending evidence explicitly and does not claim 1.3.0 has shipped.

## Version and public-surface map

The package identity and guide identity are coupled by `tests/test_version_sync.py`. The current tranche leaves guide changes out of scope, so retain coherent 1.2.0 source metadata until the approved release preparation reaches the coordinated guide update. Do not bump only package metadata and break the parity contract.

| Group | Files or producer | Required treatment |
|---|---|---|
| Package identity | `pyproject.toml`, `harness/__init__.py` | Advance together to the accepted candidate version. Dependency-input fingerprints exclude version-only changes; validate locks afterward. |
| Release narrative | `CHANGELOG.md`, `RELEASE_NOTES-1.3.0.md` | Cut Unreleased at the actual release date, preserve prior history, record exact evidence and compatibility boundaries. |
| Product and operating claims | `README.md`, `OBSERVER.md`, `ROADMAP.md`, `NEXT.md`, `PROJECT_CONTEXT.md`, `CLAUDE.md`, `INTENT.md` | Reconcile current-source versus stable claims; preserve historical version references. |
| Site source and landing page | `docs/GUIDE.md`, `docs/getting-started.md`, `docs/quickstart.md`, `docs/ringer.md`, `docs/index.html` | Coordinate with concurrent owner; describe the offline observer and current stable package consistently. Preserve evidence-bundle minimum version 1.2.0 where applicable. |
| Generated pages | `scripts/build_docs_html.py` | Regenerate HTML from Markdown after final source edits; do not hand-edit generated pages. |
| Machine resources | `docs/agents.json`, `docs/api/v1/index.json`, `docs/changelog.json`, `docs/llms.txt`, `docs/llm.txt` | Update current version and command declarations together; preserve historical changelog entries and alias byte parity. |
| Guide trust bundle | `assistant-guide.txt`, `docs/.well-known/assistant-guide.txt`, `docs/.well-known/assistant-guide-manifest.txt`, `docs/MANIFEST.yaml` | Final guide bytes, version, review date, applies-to, registry URL, sidecar digest/length, release URL, and manifest pins must agree. DNS and hosted verification follow publication of those exact bytes. |
| Checks | `tests/test_version_sync.py`, `tests/test_public_machine_resources.py`, `tests/test_guide_artifacts.py`, `tests/test_trust_manifest.py` | Reconcile command expectations where behavior changes; run existing parity checks. Do not change assertions merely to hide inconsistent source claims. |

## Integration and release sequence

1. Run the Harnessie audit with the released skill-a11y-audit 3.1.0. Live GitHub release metadata confirms publication at 2026-09-07T23:27:23Z; tag v3.1.0 resolves locally to `6af2c95a56ff058cddf0c6febc71512db1d6d19b`. Use all ten sitemap routes, retain source/live-byte provenance, apply the total-current-major gate, and preserve Markdown plus JSON findings. This audit qualifies the existing site baseline; changed release routes need revalidation.
2. Confirm accessibility evidence identifies routes, tested revision, date, OS, browser, and assistive technology, including keyboard navigation, 200% zoom/reflow, and a screen-reader pass. Changed routes may require focused revalidation after release content edits. The prior one-time waiver is not fresh evidence.
3. Apply the coordinated version/docs/trust tranche. Run focused parity checks, the full release gate, and its locked-build variant where appropriate. Check authoring documents, inward/outward manifests, generated documentation, search contracts, ecosystem state, package metadata, archive inventory, and clean-consumer behavior. Record results at the final content, not at this draft baseline.
4. Build and install the candidate wheel outside the checkout. Exercise offline observation of a halted run and verifier input refusals using deterministic fixtures. Existing fresh-install smoke already exercises the observer; use its result rather than duplicating a synthetic success claim.
5. Resolve any current live Siteline release requirement under `RELEASE_CHECKLIST.md` using dated evidence; the existing 2026-08-05 result is historical. Confirm whether the concurrent task covers this separate check.
6. Review the final candidate and obtain release authority for the exact version and publication targets. Commit/PR approval does not itself publish a package. Require exact-candidate CI before signing/tagging and publication.
7. Before publishing the GitHub Release or invoking package recovery, complete the separately scoped GuideCheck checkpoint for final served bytes, sidecar, repository pins, DNS TXT and hosted verification. The `release: published` event starts the package workflow, so the gate precedes that event. If tag identity is needed for the guide, use the authorized immutable tag while leaving the GitHub Release unpublished. Then build once from the release tag, attest all four final asset classes, verify the original build identity before attachment, and use the protected PyPI publisher. Download and independently verify all four published assets. Never re-attest downloaded historical bytes as a new build.
8. Propagate only after core publication: update Verify Action's tested default pin, exercise its seven current CI scenarios, then release its separately chosen version and stable-major tag. The scenarios cover failing checks, cannot-verify refusal/advisory behavior, evidence intake, fresh-check gating, stale evidence refusal, and unsafe-trigger refusal. Preserve the stated evidence-bundle minimum of 1.2.0.
9. Update Homebrew using the immutable new PyPI source archive and digest; run upgrade/install, strict audit, formula test, linkage, and CLI smoke. Leave engine wrappers on their independent release train unless a changed integration seam requires their own qualification.
10. Confirm the guide has not changed since the pre-publication receipt. Record completed delivery, any intentional downstream lag, and remaining external evidence honestly. GuideCheck is not a post-PyPI closeout task for 1.3.0.

## Questions and remaining boundaries

- Accepted: 1.3.0 scope, Harnessie audit using released a11y-audit 3.1.0 with Markdown plus JSON, and GuideCheck required before package publication while outside this implementation tranche.
- Resolved: the completed task delivered the audit tool; no completed Harnessie site or manual audit was claimed.
- Completed: [automated ten-route baseline audit](accessibility/2026-09-07/audit-2026-09-07.md), source/live-byte provenance and targeted manual plan. The approved [local mitigation](accessibility/2026-09-07-mitigation/audit-2026-09-07.md) resolves four serious violations and 22 candidates. The gate is inconclusive on 36 remaining candidates. Still pending: their review, manual tests, coordinated version/guide files, exact-candidate qualification, separately scoped GuideCheck, hosted provenance acceptance and stable-release publication authority.
- Prepared locally: this packet, draft 1.3.0 notes, current-work routing in `NEXT.md`, and the explicit pre-publication GuideCheck checkpoint in `RELEASE_CHECKLIST.md`. No version bump, guide rotation, provider policy, downstream pin, tag, package publication or external model call occurred.
