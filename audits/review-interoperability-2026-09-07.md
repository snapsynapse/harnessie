# Controlled review and AIDR interoperability

Date: 2026-09-07. Scope: Harnessie runtime assessment and synthetic proof, not an exporter, live panel, or external conformance claim. Runtime base: `d64d985`; observer preparation retained separately from `feature/bidding-and-observer` at `9b30f40`.

## Enforcement map

| Requirement | Current mechanism | Limit or next contract |
|---|---|---|
| Identical frozen packet | `_run_adversarial_phase` gives each initial role the same rendered task | Shared workspace files can change during review. No frozen content manifest or immutable snapshot is established by this path. A pilot must provide an explicit snapshot and hashes. |
| Actual evidence access | Position roles can use admitted read tools | Access is a capability, not proof a reviewer read each source. A pilot must record evidence references and exposure. |
| Initial context separation | `_run_role` creates a fresh loop for each initial position; peer prose is introduced only in objection tasks | Role prompts differ; orchestrator roles receive the memory index. Shared filesystem access is not blind-review isolation. Independently launched coding applications are outside this mechanism. |
| Read-only review | Runtime denies the registry's side-effect tools for positions and objections | Installed plugins are operator-trusted code. This does not sandbox arbitrary external controllers. Existing `test_position_agents_are_read_only` proves built-in write refusal. |
| Bounded objections | Declared `rebuttal_rounds`, with early exit after a quiet round | A quiet round is not empirical evidence of adequate challenge. Initial and objection artifacts must retain their stage labels. |
| Assembly | Runtime writes positions and objections into a run decision record | Repeated role instances receive distinct heading labels but retain the underlying `agent` value. Exports need an explicit participant-instance mapping. |
| Mandatory human halt | `arbitration: human` bypasses the convergence success branch | The shipped three-panel example selects convergence. Use explicit human mode for a mandatory-human pilot; leave the existing example's documented semantics intact. |
| Resume | Existing record is linted; structural `human-arbitrated` eligibility permits resume | Status alone is insufficient. Runtime does not authenticate the editor or judge whether reasons address objections. |
| Verification | Evidence-bound standalone verification produces required-claim results and exit 0/1/2 | A verified change is not approval of the decision or authority to publish it. |

## Synthetic proof

`tests/test_adversarial.py` now includes agreement under explicit human mode, refusal on resume without arbitration, byte preservation of the decision record, a sentinel preventing reviewer redispatch, and refusal after a status-only edit. The existing successful arbitration/resume test supplies synthetic human metadata as a fixture. No real decision is arbitrated by these tests.

Result: 20 adversarial tests passed locally. These are tests of existing behavior, not a runtime behavior change. They do not prove external human identity or shared-file confidentiality.

A temporary one-position runtime-record probe also ran against the reference AIDR linter: raw `DR-decide` failed its required AIDR identifier grammar; a separate synthetic `AIDR-9999` candidate with only that identifier mapped passed, with no earned claims. The source bytes remained unchanged (SHA-256 `e5c252e30eb4ef9a57672101706a8f5e6e1339ed1f9b4826070e5be33d9434c5`). That number exists only in temporary synthetic output and reserves no real ID. This narrow fixture does not validate multi-participant mapping, human provenance, destination collision handling or a production exporter.

## Proposed export mapping

Target: AIDR SPEC 0.1.0 and reference linter inspected from checkout `a67c41d`. Its working tree contains additional review artifacts; this assessment consumes the normative spec and reference tools only.

| Source | Proposed destination | Required refusal or qualification |
|---|---|---|
| Run ID plus `DR-phase` and record digest | Evidence reference; operator-reserved `AIDR-NNNN` filename and `id` | Never allocate by blindly taking the next number across concurrent writers. Check destination-directory uniqueness and use exclusive creation. |
| Title, context, rendered task | Title, Context, Question | Preserve substance; require a single decidable question. Do not export a mutable file reference as a frozen packet claim. |
| Position label and agent role | Unique participant-instance label and metadata, with original role retained in provenance | Disclose any mechanical mapping. Do not rewrite or invent reviewer prose. |
| Reported model and provider | Same reported identities | Do not infer different providers from different model names or claim authenticated identity. |
| Initial prose and objections | Separate position/objection sections | Preserve dissent, exposure, stage and source links. Objections addressed to the record stay addressed to the decision. |
| Open status | Open status and empty Arbitration | Convergence and verifier success never create arbitration. |
| Existing human-authored arbitration | Exact attributed text, only if separately authorized for export | Structural lint is insufficient to establish human authorship; missing or conflicting provenance blocks this path. |
| Run evidence | Resolvable source-relative or explicitly rooted references and hashes | Relocating a record must not break proof links. Recheck source digest before publishing output. |

A future exporter must stage output outside the final destination, lint under a pinned target contract, refuse existing destinations and unsafe paths, then publish using exclusive creation. Every failure must leave source evidence and existing destination bytes unchanged. Tests must cover missing identities, malformed state, namespace collision, symlink escape, unresolved evidence, and false arbitration claims before implementation. No exporter is implemented in this pass.

## Disposition

Use file links and `harnessie verify` as the present integration seam. A live controlled-panel pilot, exporter, new scheduler, terminal controller, or external conformance claim requires its own accepted scope. The mapping does not amend Turnfile or AIDR and does not retroactively improve old review provenance.
