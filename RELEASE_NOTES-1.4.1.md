# Harnessie 1.4.1: offline open-record AIDR export

Published on GitHub on 2026-09-08 UTC at signed tag `v1.4.1`, pointing to `296deed2f91cd4c8eeecad82b83f137dd029ea26`, with original-build assets attached. Both PyPI distributions match those assets, pass publisher-attestation verification and install from the public index in a fresh Python 3.13 environment. Package and assistant guide both use 1.4.1. Version 1.4.0 was intentionally skipped.

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

The [release execution audit](audits/release-1.4.1.md) records the local candidate gate, exact-commit CI, artifact validation, installed-consumer checks, and deployment evidence. CI, CodeQL, Scorecard, and Pages passed on release commit `296deed`. The earlier [completion](audits/aidr-pre-release-completion-2026-09-08.md) and [version preparation](audits/version-1.4.1-preparation.md) audits remain dated evidence for their own snapshots. All four GitHub assets passed provenance verification against the signed tag and release commit. Both PyPI distributions passed publisher verification; the fresh public-index consumer passed the installed export example. Verify Action 0.2.2 passed all seven exact-merge fixtures.

The final 8,036-byte guide earned [hosted GuideCheck Level 4 under profile 2.0.0](audits/release-1.4.1/guidecheck-prepublication.json) with zero blocking findings and a qualifying DNS anchor. Its frozen SHA-256 is `7ab4c0a952109ea10257b1a9859533778261291605ce386708bccb305bbf09dc`. The [1.3.1 receipt](audits/release-1.3.1/guidecheck-prepublication.json) remains historical evidence for different guide bytes. Guide conformance does not establish software safety or accessibility conformance.

## Deferred work and downstreams

Accessibility remains deferred for this session. The prior queue retains 35 table-contrast candidates, one video-caption applicability candidate, and manual checks; earlier evidence does not establish acceptance for newly changed routes.

Verify Action 0.2.2 and stable `v0` pin core 1.4.1 at `9f18d70017f395ef4d15ac5746e30ac633f00f8e`. Homebrew 1.4.1 passed strict audit, a real upgrade, formula and linkage tests, and the installed exporter demonstration; it is published in tap merge `953760f3968200f99658bfb068609532cb9fbf4d`. Engine wrappers remain on their independent 0.1.0 release train.

Live review panels, arbitration import, broader source-format support, bidding, commentary, follow mode, automatic runner integration, model selection, and provider-policy changes remain deferred. No real human arbitration record was changed by the exporter delivery.

## Original release assets

| Asset | SHA-256 |
|---|---|
| `harnessie-1.4.1-py3-none-any.whl` | `2094c7793a0fde76226d5782b0785311d9dbc955998a0c7237580f43b1066dd5` |
| `harnessie-1.4.1.tar.gz` | `4348ca226397a79d317dc619374b75019a43f8f660b30d3410d83d2cbf925d85` |
| `harnessie-1.4.1.SHA256SUMS` | `11476d68a6e6f82f7e205457d11262e2eedb456cc90380ad25ec25796384b229` |
| `harnessie-1.4.1.cdx.json` | `228a15e401cd337dc8acd7bc2264ea176162d02d2f13e0490e2a94cb9e1307c2` |
