# Harnessie 1.4.1: offline open-record AIDR export

Prepared on 2026-09-08 UTC. Publication is pending. Package and assistant guide both use 1.4.1; the published core remains 1.3.1 until this release completes. Version 1.4.0 was intentionally skipped.

Harnessie 1.4.1 adds deterministic export of a supported open contested-phase record to an explicitly named AIDR file. It carries recorded dissent into a separate artifact while preserving the original decision and its run state.

## Included

- `harnessie export-aidr RUN_ID PHASE --output decisions/AIDR-NNNN-short-slug.md --arbiter HUMAN_HANDLE` requires an unused destination in the project's existing `decisions/` directory and a declared human arbiter. It prints JSON and exits 0 for completed export or 2 for refusal.
- The exporter accepts a strict subset of generated open records and their single emitted event-journal reference. Arbitration content, decided metadata, ambiguous Markdown/YAML, unresolved or broken evidence, unsafe paths, symlinks, and destination ID collisions refuse. Some records accepted by the runtime contain unsupported formatting and therefore cannot be exported; the exporter does not silently rewrite them.
- Repeated reviewer roles retain distinct participant-instance labels and original-role provenance. Recorded position prose and objections survive. Source and evidence hashes bind the consumed snapshot; validated output is created exclusively after the input bytes are rechecked.
- The [executable example](examples/aidr-export/README.md) runs actual workflow code with scripted mock actors, invokes the installed export CLI, checks the result against the pinned AIDR 0.1.0 reference linter, and verifies source preservation and continued human-arbitration halt. It also demonstrates safe refusal of unsupported source formatting. Export itself has no Node dependency; reference-linter acceptance uses Node.
- Platforms without the required POSIX locking and file primitives return `unsupported_platform` with exit 2 before project reads or writes. Native Windows export is unsupported.
- Engineering docs, user instructions, machine discovery, and the assistant guide describe the same export boundary and source limitations. Four deterministic exporter eval cases cover admissible open dissent, partial arbitration, namespace collision, and broken evidence.

## Authority and evidence limits

Export is an operator-issued file write outside the runner, ownership ledger, tool registry, consent lock, and approval policy. It makes no model or provider calls, but it is not a read-only operation. An assistant invoking it needs authorization for the destination write. The command does not author or import arbitration, approve a decision, or resume the original run. The exported record remains open with empty Arbitration.

Model/provider metadata and arbiter declarations are reported identities, not authenticated authorship. Export-time hashes do not prove the source matches its original generation, that reviewers saw identical inputs, or that review was independent. Structural validation does not judge whether a question is decidable or an objection was adequately answered. Existing objection text is truncated upstream to 500 characters, event copies to 200; export cannot recover missing text or round attribution. Source and destination directories must remain operator-controlled. The [export contract](AIDR_EXPORT.md) documents the complete supported subset and filesystem limits.

## Verification status

The complete local candidate gate passed: 718 tests, one live-provider skip, 28 expected failures, 66/66 evals, manifests and schemas, isolated distributions, metadata/artifact inspection and a fresh installed consumer. [Release execution](audits/release-1.4.1.md) tracks the subsequent exact-commit and publication gates.

The dated [pre-release completion audit](audits/aidr-pre-release-completion-2026-09-08.md) records 718 passed tests, one live-provider opt-in skip, 28 expected failures for deferred features, and 66/66 deterministic evals. It also records independent focused verification and a fresh installed-wheel walkthrough. These results describe that reviewed snapshot, before the final 1.4.1 version and release-document changes; they are not a claim that the final release gate has passed.

The subsequent [1.4.1 preparation audit](audits/version-1.4.1-preparation.md) records 32 focused tests, 66/66 evals, local wheel/source builds, artifact inspection, and fresh installed-wheel smoke for its versioned snapshot. Final exact-commit CI, release-artifact inspection, original-build provenance, GitHub/PyPI publication, and post-publication checks remain pending.

The local 1.4.1 GuideCheck result achieved Level 3 with `anchor.independent.missing` unresolved. Current hosted Level 4 acceptance remains pending. The [1.3.1 hosted receipt](audits/release-1.3.1/guidecheck-prepublication.json) is historical evidence for different guide bytes. No new hosted or accessibility conformance pass is claimed here.

## Deferred work and downstreams

Accessibility remains deferred for this session. The prior queue retains 35 table-contrast candidates, one video-caption applicability candidate, and manual checks; earlier evidence does not establish acceptance for newly changed routes.

Verify Action 0.2.1/stable `v0` currently pins core 1.3.1, and Homebrew currently serves 1.3.1. Their separate propagation and verification await core publication. Engine wrappers remain on their independent 0.1.0 release train.

Live review panels, arbitration import, broader source-format support, bidding, commentary, follow mode, automatic runner integration, model selection, and provider-policy changes remain deferred. No real human arbitration record was changed by the exporter delivery.
