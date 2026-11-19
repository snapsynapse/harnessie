# Harnessie code review and security audit, 2026-11-18

Scope: repository-level runtime, verification, governance, transport, deterministic assurance and release readiness. Owning record: this report and its [machine-readable JSON](security-review-2026-11-18.json).

Reviewed source: `6c053dd8409e109310a124685d11e29e1e8e7885` on `codex/security-release-audit`, created from freshly fetched `origin/main`. Original branches and local-only commits `520cc08` and `27d0eb8` were preserved. No runtime source, version, model configuration or downstream repository was changed.

## Executive summary

Release recommendation: HOLD publication. Six high findings affect ownership, credential handling, evidence integrity, conversation isolation, approval precedence and reuse of accepted results. Passing existing checks does not cover these reproductions. Remediate the P1 items first, review the P2 acceptance boundaries, then run fresh independent adversarial verification and the complete release gates.

| Critical | High | Medium | Low | Total |
|---|---|---|---|---|
| 0 | 6 | 8 | 7 | 21 |

These are unique manually triaged findings, including correctness, assurance and low-applicability dependency issues. They are not raw scanner hit counts. Preconditions and evidence strength are explicit below; no live exploitation or provider inference occurred.

## Automated results and candidate validation

| Check | Observed result |
|---|---|
| Existing Python 3.13.9 environment | 1,335 passed, 43 skipped, 28 expected failures; environment differs from current release lock |
| Native Seatbelt focused suite | 50 passed, zero skipped outside the outer sandbox |
| Isolated hash-locked CPython 3.12 suite | 1,372 passed, 4 skipped, 28 expected failures; two subprocess examples initially failed because the new environment lacked the package installation |
| Corrected-environment example rerun | Both failures passed after editable installation; this is a focused rerun, not a claimed clean single full-suite run |
| Deterministic evals | 70/70 passed |
| Schema/manifests/ecosystem/docs/search | 9 documents, 21 outward files, 16 inward files, 4 components, 9 generated pages, 10 sitemap pages; all passed, zero search defects |
| Locked package gate | Passed installed-lock validation, no-isolation wheel/sdist build, Twine, artifact checks and fresh installed CLI/mock walkthrough |
| Dependency advisory audit | Runtime: zero known vulnerabilities. Dev and release: one setuptools advisory each, same unique issue |
| Tracked-source secret patterns | 349 files; 14 matches, all deliberate fake canaries; zero confirmed credentials |
| Credential-file history paths | No tracked env files or added env/key/pem paths found by the named history query |

The package rehearsal used unchanged source version 1.5.0. The gate removed its temporary distributions after checking them. It did not produce a newly versioned publishable candidate, tag, release, deployment or downstream update.

Bandit 1.9.4 analyzed 17,006 lines across `harness/` and `scripts/`: raw hits were 1 high, 4 medium and 59 low. The high B613 hit is the intentional bidi-detection regex. B108 is a private `/tmp` binding. Three B310 sites require real transport review and are covered by findings 002 and 012. LOW hardcoded-password hits are explanatory labels, not credentials; B110 is cleanup polling. Subprocess import/use warnings were reviewed in context. Scanner raw counts are not asserted vulnerabilities.

pip-audit 2.10.0 queried all three locked profiles. [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w) affects locked setuptools 84.0.0; 84.1.0 is the advertised fix. Its Windows legacy wheel-install precondition lowers applicability to this macOS/Linux tool. No Node dependency manifest exists to audit.

Raw scanner data, sanitized probe results and five reproducible offline scripts live in [the evidence directory](security-review-2026-11-18/). Scripts are diagnostic reproductions: a successful script exit is not a passing security gate, and vulnerable-observation booleans describe the reviewed baseline.

## Findings and mitigation recommendations

| ID | Severity | Finding |
|---|---|---|
| SEC-20261118-001 | HIGH | Hardlink aliases bypass ownership and workspace write confinement |
| SEC-20261118-002 | HIGH | Cross-origin redirects retain provider credentials |
| SEC-20261118-003 | HIGH | Admitted evidence is not bound to the bytes later read |
| SEC-20261118-004 | HIGH | Parallel Responses conversations share mutable replay state |
| SEC-20261118-005 | HIGH | Workflow preapproval overrides explicit or invalid approval policy |
| SEC-20261118-006 | HIGH | Resume reuses accepted results after task or goal changes |
| SEC-20261118-007 | MEDIUM | Raw tool secrets and PII enter the event log before containment |
| SEC-20261118-008 | MEDIUM | PII stripping can hide a recognized secret and retain it for rehydration |
| SEC-20261118-009 | MEDIUM | Resume resets cumulative spend and token accounting |
| SEC-20261118-010 | MEDIUM | Provider failure or refusal envelopes become executable tool turns |
| SEC-20261118-011 | MEDIUM | Absent provider usage is silently counted as zero |
| SEC-20261118-012 | MEDIUM | Transport, file and child-output limits truncate only after unbounded reads |
| SEC-20261118-013 | MEDIUM | Adversarial convergence ignores explicit stand-down |
| SEC-20261118-014 | MEDIUM | Model summary fabricates decision metadata and independence claim |
| SEC-20261118-015 | LOW | Final verifier boundary contradicts claim-level verdict instructions |
| SEC-20261118-016 | LOW | Unavailable check executable is classified as failed artifact |
| SEC-20261118-017 | LOW | Search checker decodes XML entities more than once |
| SEC-20261118-018 | LOW | Eval runners silently ignore unknown assertion fields |
| SEC-20261118-019 | LOW | Audit claims overstate detection without a trusted tail anchor |
| SEC-20261118-020 | LOW | Nonfinite numeric configuration passes validation |
| DEP-20261118-001 | LOW | Release tooling lock contains a setuptools advisory |

### SEC-20261118-001: Hardlink aliases bypass ownership and workspace write confinement

Severity: HIGH; priority: P1; OWASP A01:2021; type: security; status: new.

Location: `harness/tools/builtin.py:108`, `harness/tools/builtin.py:123`.

The direct write tool authorizes a resolved pathname, then truncates the existing inode. A hardlink inside an allowed lane can name an operator-owned inode or an inode outside the workspace. Path.resolve() does not distinguish hardlinks; the in-process write is outside the OS sandbox.

Preconditions: An admitted workspace contains a preexisting hardlink to a protected same-filesystem file. No control of environment variables or a real service is required.

Evidence: containment.py: both operator_lane_changed and outside_workspace_changed are true after successful write_file dispatch.

Mitigation: Use same-directory exclusive temporary files and atomic replacement so writes replace only the authorized directory entry; reject or explicitly handle multiply linked files and anchor directory traversal. Preserve permissions deliberately. Review shell-created hardlinks separately under native backends.

Regression/eval: Hardlink to operator lane, another agent claim and outside-workspace file; symlink/parent replacement variants; ordinary edits and deliberate legitimate hardlinks as compatibility controls.

### SEC-20261118-002: Cross-origin redirects retain provider credentials

Severity: HIGH; priority: P1; OWASP A07:2021; type: security; status: new.

Location: `harness/models/openai_compat.py:54`, `harness/models/anthropic.py:47`, `harness/models/openai_responses.py:74`.

All production adapters use the default urllib redirect handler. A 302 can move a credentialed POST to another origin while retaining Authorization or X-api-key headers.

Preconditions: The configured provider, proxy or endpoint redirects. This is conditional credential disclosure, not an arbitrary attacker-selected URL in a prompt.

Evidence: transport.py uses the actual HTTPRedirectHandler.redirect_request with synthetic headers: changes_origin, retains_authorization and retains_x_api_key are all true. No request was sent.

Mitigation: Reject redirects by default, reusing the pilot no-redirect design. Any supported redirect must use an explicit same-origin HTTPS policy and remove sensitive headers before crossing trust boundaries.

Regression/eval: 301/302/303/307/308, cross-origin and HTTPS downgrade, same-origin policy, custom credential headers, safe local positive controls.

### SEC-20261118-003: Admitted evidence is not bound to the bytes later read

Severity: HIGH; priority: P1; OWASP A08:2021; type: security; status: new.

Location: `harness/verify_evidence.py:65`, `harness/verify_standalone.py:253`, `harness/verify_standalone.py:313`.

Preflight verifies proof digests but stores paths. The evidence tool reopens those paths without a digest, no-follow or containment recheck. Checks execute after preflight, and evidence_root may be inside the mutable workspace. The final bundle digest is also reread from its path.

Preconditions: A check or another writer can modify an admitted proof or parent after admission. The direct repro swaps a proof for a symlink to a disposable outside-root file. A check can rewrite admitted evidence without a concurrent race.

Evidence: governance.py evidence_post_admission_swap returns ok=true and returned_outside_bytes=true.

Mitigation: Snapshot bounded immutable evidence and bundle bytes at admission, and serve/hash that snapshot. If reopening is unavoidable, use anchored no-follow descriptors and verify the exact consumed bytes and containment.

Regression/eval: Post-admission content/file/parent replacement, check-modified proof, bundle replacement, outside-root symlink, unchanged-proof positive control.

### SEC-20261118-004: Parallel Responses conversations share mutable replay state

Severity: HIGH; priority: P1; OWASP A04:2021; type: security; status: new.

Location: `harness/runner.py:207`, `harness/runner.py:701`, `harness/models/openai_responses.py:32`, `harness/models/openai_responses.py:165`.

The runner caches one model object per spec while parallel loops share it. A delayed A response can overwrite B replay state after B has completed, while the object still identifies B as its current conversation. B follow-up then transmits A prompt/output and drops its own original context and instructions.

Preconditions: Two concurrent phases use the same openai-responses tier. No malformed provider response is needed.

Evidence: responses-race.py uses deterministic thread barriers and a fake opener: b_followup_contains_a_private_input=true, b_followup_omits_b_original_input=true, instructions_still_b=false.

Mitigation: Give each loop/conversation its own adapter and replay state. A lock around an individual complete() call alone does not preserve histories across interleaved conversations.

Regression/eval: Barrier-driven same-tier concurrent loops, delayed responses, repeated tool turns, failures and sequential conversation reuse. Assert no cross-conversation input, output or instructions.

### SEC-20261118-005: Workflow preapproval overrides explicit or invalid approval policy

Severity: HIGH; priority: P1; OWASP A01:2021; type: security; status: new.

Location: `harness/runner.py:1007`, `harness/approval.py:63`.

The handler grants approve_tools before consulting the explicit approval policy. This contradicts the policy contract that explicit deny wins and bypasses malformed-policy denial as well.

Preconditions: An operator-supplied workflow includes a preapproval and a separately supplied policy denies that tool. This is a composition/precedence defect, not a claim that workflows are untrusted by default.

Evidence: governance.py supplies a deny for expire_fact plus workflow preapproval; the fact is actually archived.

Mitigation: Evaluate invalid-policy and explicit-deny results first. Consider workflow grants, policy allows and TTY only after mandatory denial checks.

Regression/eval: Global/phase deny crossed with workflow grant, policy allow and TTY; malformed policy plus grant; valid allow positive control.

### SEC-20261118-006: Resume reuses accepted results after task or goal changes

Severity: HIGH; priority: P1; OWASP A08:2021; type: security; status: new.

Location: `harness/runner.py:327`.

Ordinary resume skips any passed phase with the same name. It does not bind the prior acceptance to workflow/goal/rendered task/criteria or current artifact bytes.

Preconditions: The same run ID is resumed after contract or artifact drift. This can happen accidentally; it does not require rewriting the hash chain.

Evidence: governance.py changes the task and goal, then resumes with an empty mock brain: skipped_resume, zero model calls, old report reused.

Mitigation: Persist a versioned run contract and relevant input/artifact digests, validate them before reusing completed phases, and refuse incompatible resumes with a new-run remedy. Do not silently rerun side effects.

Regression/eval: Changed goal/task/check/criteria/upstream report/artifact, reordered phases, unchanged resume positive control.

### SEC-20261118-007: Raw tool secrets and PII enter the event log before containment

Severity: MEDIUM; priority: P2; OWASP A09:2021; type: security; status: new.

Location: `harness/loop.py:195`, `harness/loop.py:220`, `harness/tools/builtin.py:94`.

tool_result logs the first 300 characters before the containment call. read_file returns raw content. A subsequent secret_egress halt prevents the next model call but does not remove the credential already in events.jsonl. Recognized PII is also logged before stripping.

Preconditions: An agent reads an in-workspace file containing a recognized credential or PII near the beginning. Local logs then carry sensitive material and may later be shared.

Evidence: containment.py: raw_value_in_events=true for both credential and email; credential stops at secret_egress after one mock call, PII completes after two.

Mitigation: Contain/redact before every event emission and model boundary; log only safe kind labels and metadata on refusal. Audit other exception/refusal/event paths for the same ordering.

Regression/eval: Read-file, evidence-reader, plugin and shell results with canaries at multiple offsets; inspect every artifact and captured model request, not only final stop status.

### SEC-20261118-008: PII stripping can hide a recognized secret and retain it for rehydration

Severity: MEDIUM; priority: P2; OWASP A02:2021; type: security; status: new.

Location: `harness/boundary.py:182`.

guard_egress strips PII before scanning secrets. A credential whose suffix matches the credit-card detector can lose its recognizable shape, enter the strip map and later be reconstructed.

Preconditions: A recognized credential overlaps a PII pattern. The repro uses a synthetic Anthropic-shaped prefix and a Luhn-valid numeric suffix.

Evidence: containment.py: recognized_before_strip=true, guard_returned_without_halt=true, mapping_entries=1, rehydration_reconstructs_secret=true.

Mitigation: Detect/refuse secret spans on the original text before PII replacement and validate mappings never contain secret material. Preserve PII-only behavior.

Regression/eval: Every credential kind crossed with overlapping email/phone/card patterns and offsets, plus ordinary PII and nonsecret numeric positive controls.

### SEC-20261118-009: Resume resets cumulative spend and token accounting

Severity: MEDIUM; priority: P2; OWASP A04:2021; type: security; status: new.

Location: `harness/runner.py:169`.

Each runner constructs a fresh Budget without replaying historical usage. A resumed run therefore starts with full configured headroom despite prior usage.

Preconditions: A run with prior spend is resumed. This differs from the documented per-call overshoot residual: the entire earlier accumulated spend is lost.

Evidence: governance.py logs 100000 tokens and $5 for the prior run; the resumed counters are zero.

Mitigation: Reconstruct cumulative usage from validated history before dispatch, refuse unknown/malformed accounting, and bind budget changes to explicit recorded operator action.

Regression/eval: Exhausted resume makes zero calls; exact partial headroom; repeated resumes; parallel usage counted once; missing usage handling.

### SEC-20261118-010: Provider failure or refusal envelopes become executable tool turns

Severity: MEDIUM; priority: P2; OWASP A08:2021; type: security; status: new.

Location: `harness/models/openai_compat.py:129`, `harness/models/anthropic.py:117`, `harness/models/openai_responses.py:142`.

Tool presence overrides content_filter/refusal or is checked ahead of failed/cancelled/incomplete status. The normalized turn can reach tool dispatch or task_complete despite a blocked provider status.

Preconditions: A provider or compatibility server returns a contradictory tool-bearing error/refusal envelope. The adapters are responsible for rejecting malformed states.

Evidence: transport.py: all three blocked envelopes become tool_use and retain task_complete.

Mitigation: Give terminal refusal/failure precedence and reject contradictory envelopes while preserving available accounting separately. Validate response and individual tool item status.

Regression/eval: Provider status x tool-presence x usage matrix, truncated and contradictory envelopes, valid tool-use positive controls; assert zero dispatch on refused/error turns.

### SEC-20261118-011: Absent provider usage is silently counted as zero

Severity: MEDIUM; priority: P2; OWASP A09:2021; type: security; status: new.

Location: `harness/models/openai_compat.py:136`, `harness/models/anthropic.py:124`, `harness/models/openai_responses.py:199`.

All production adapters accept absent usage as empty data and default absent counters to zero. Metered runs continue with unverifiable accounting.

Preconditions: A provider omits usage or one counter. Some local compatibility services legitimately lack accounting, which needs an explicit unmetered mode rather than an implicit zero.

Evidence: transport.py: missing_usage_accepted and missing_usage_counted_as_zero are true for all three adapters.

Mitigation: Represent unknown accounting explicitly; fail closed for metered runs or require an explicit unmetered policy. Preserve received counters even if unrelated parsing fails.

Regression/eval: Missing/null/partial/negative/bool/string/nonfinite counters, known-zero positive control, malformed result with intact usage, no retry after accounting uncertainty.

### SEC-20261118-012: Transport, file and child-output limits truncate only after unbounded reads

Severity: MEDIUM; priority: P2; OWASP A04:2021; type: security; status: new.

Location: `harness/models/openai_compat.py:57`, `harness/models/anthropic.py:57`, `harness/models/openai_responses.py:77`, `harness/verify.py:111`, `harness/tools/builtin.py:177`, `harness/tools/builtin.py:94`, `harness/verify_evidence.py:65`.

Production HTTP success/error reads are unbounded, read_file/read_evidence read full files before slicing, and subprocess capture_output accumulates all output before truncation. Socket timeout is not a whole-call deadline. Large or slow data can exhaust memory or monopolize a run.

Preconditions: A provider, check or admitted file generates excessive or slow-trickling data. No live stress test was performed.

Evidence: transport.py records resp.read() invoked with no size. Remaining call sites were directly inspected; no exhaustion payload was run.

Mitigation: Stream with byte ceilings and overflow sentinel, use whole-call supervision, bound both stdout and stderr, and supervise/clean the process group. Reuse tested pilot concepts without copying unchecked assumptions.

Regression/eval: Exact-limit/one-over success and error bodies/files, false Content-Length, slow trickle, large stdout/stderr and exited-parent live-pipe fixtures; check cleanup and bounded memory.

### SEC-20261118-013: Adversarial convergence ignores explicit stand-down

Severity: MEDIUM; priority: P2; OWASP A04:2021; type: security; status: new.

Location: `harness/adversarial.py:57`, `harness/runner.py:1199`.

The parser coerces no_new_objection with bool(), while the runner ignores it. Empty objection lists count as quiet even when the participant explicitly says false or omits the marker.

Preconditions: Recommending positions are followed by empty objections with false/missing stand-down.

Evidence: governance.py: such a decision returns passed.

Mitigation: Require literal boolean true and an empty validated objection list from every participant for quiet convergence. Missing/false/malformed responses continue only within bounds or require arbitration.

Regression/eval: False/missing/string/null stand-down, nonempty objections plus true, malformed objection items and unanimous literal-true positive control.

### SEC-20261118-014: Model summary fabricates decision metadata and independence claim

Severity: MEDIUM; priority: P2; OWASP A08:2021; type: security; status: new.

Location: `harness/adversarial.py:134`.

Model-controlled summary text is interpolated as unfenced Markdown metadata. Newlines/headings can introduce invented positions/providers. The linter then derives independence from the rendered structure.

Preconditions: An adversarial participant places record syntax in its summary, rather than only in fenced prose.

Evidence: governance.py: one actual position yields no lint errors and an independent-positions claim after an injected heading/provider.

Mitigation: Render summaries as escaped single-line scalars; derive trusted claims from structured PositionRecord objects, and separately lint imported text. Validate all interpolated fields.

Regression/eval: LF/CRLF headings, metadata lists, frontmatter and fence syntax; actual metadata cardinality equals structured input; invented providers cannot earn claims.

### SEC-20261118-015: Final verifier boundary contradicts claim-level verdict instructions

Severity: LOW; priority: P3; OWASP A04:2021; type: correctness; status: new.

Location: `harness/roles.py:81`, `harness/verify_standalone.py:73`.

The structured default verifier prompt is followed by a generic boundary demanding legacy passed/reasons JSON. Evidence bundles reject that legacy shape.

Preconditions: Model-backed evidence-bundle verification. This is a directly confirmed prompt composition conflict, not a measured live model failure rate.

Evidence: governance.py: the composed prompt contains claims instructions but ends by requiring legacy boolean JSON.

Mitigation: Separate behavior constraints from mode-specific serialization and compose a single explicit output contract.

Regression/eval: Inspect the actual composed prompts for each mode; strict claim verdict and legacy-criteria fixtures; no live model call needed.

### SEC-20261118-016: Unavailable check executable is classified as failed artifact

Severity: LOW; priority: P3; OWASP A04:2021; type: correctness; status: new.

Location: `harness/verify.py:128`, `harness/verify_standalone.py:317`.

Missing executable is converted into a failed check and exit 1, although the standalone contract assigns blocked/infrastructure cases to cannot-verify exit 2.

Preconditions: A configured check program is not installed. The safe repro bypasses only the sandbox wrapper for a nonexistent executable; nothing executes.

Evidence: governance.py: missing check returns exit_code=1, expected_cannot_verify=2.

Mitigation: Introduce structured check outcomes for completed failure, blocked infrastructure, timeout and resource stop; avoid classifying via message prefixes.

Regression/eval: Nonexistent binary, malformed command, permission error, timeout, sandbox refusal, genuine executable exit-1 positive control.

### SEC-20261118-017: Search checker decodes XML entities more than once

Severity: LOW; priority: P3; OWASP A08:2021; type: correctness; status: still_open.

Location: `scripts/check-search.mjs:54`.

The chained decoder handles amp before lt/gt. Nested escapes therefore change meaning, and apostrophe/numeric references are incomplete.

Preconditions: A local sitemap or metadata contains nested or numeric XML references. This is a retained handoff defect, not a demonstrated runtime security compromise.

Evidence: assurance.py evaluates the current function: nested XML escape decodes twice.

Mitigation: Patch only the decoder using upstream asset v7 single-pass XML/numeric decoding, retain local adaptations, and route production canonical parsing through the same contract when changed.

Regression/eval: Nested amp escape, apos, decimal/hex numeric references, invalid Unicode, whitespace around loc and encoded live canonical.

### SEC-20261118-018: Eval runners silently ignore unknown assertion fields

Severity: LOW; priority: P3; OWASP A08:2021; type: assurance; status: new.

Location: `harness/evals.py:267`.

Most scenario kinds run only a fixed subset of expectations without rejecting unsupported expect_* keys. A misspelled or unsupported security assertion can produce green despite never being tested. Observer/AIDR cases already reject unknown assertions.

Preconditions: An eval author adds or misspells an expected security condition.

Evidence: assurance.py: a loop scenario with expect_impossible_security_property passes unchanged.

Mitigation: Validate a versioned per-kind scenario schema, reject unknown fields/duplicate IDs, require nonvacuous assertions, and add mutation checks proving every expectation can fail.

Regression/eval: Unknown/misspelled assertion for every kind, wrong types, duplicate scenario IDs, inverted assertions on every shipped fixture.

### SEC-20261118-019: Audit claims overstate detection without a trusted tail anchor

Severity: LOW; priority: P3; OWASP A08:2021; type: assurance; status: new.

Location: `harness/events.py:9`, `harness/audit.py:5`.

A prev-linked chain cannot detect edits to its terminal event or suffix truncation without a separately trusted tail/count. Documentation says any edit/deletion is detected while disclosing only whole-file rewrite as a limit.

Preconditions: An actor can modify the event file. This is an inherent unanchored-chain residual and a claim/test gap, not a new privilege bypass.

Evidence: governance.py: edited_tail_accepted=true and truncated_tail_accepted=true.

Mitigation: Narrow claims to linked interior changes. Optionally verify an externally trusted terminal digest/count or signed completion receipt; do not store the only anchor beside the mutable log.

Regression/eval: Interior edit, last-event edit, suffix truncation, empty log and trusted-tail mismatch; retain valid-resume positive control.

### SEC-20261118-020: Nonfinite numeric configuration passes validation

Severity: LOW; priority: P3; OWASP A05:2021; type: correctness; status: new.

Location: `harness/schema.py:79`, `harness/runner.py:138`.

YAML NaN/infinity passes numeric schema comparisons and simple <=0 checks. Nonfinite dollar ceilings/rates invalidate dollar accounting comparisons.

Preconditions: Operator-authored config includes .nan/.inf. Token limits still apply; no unlimited-spend remote exploit is claimed.

Evidence: assurance.py: NaN budget validates and does not exhaust even with large spend.

Mitigation: Reject nonfinite numeric values recursively before schema use; enforce finite nonnegative accounting updates and explicit ceiling semantics.

Regression/eval: NaN/+inf/-inf, negative/bool/string counters and rates, finite zero/positive controls.

### DEP-20261118-001: Release tooling lock contains a setuptools advisory

Severity: LOW; priority: P3; OWASP A06:2021; type: dependency; status: new.

Location: `requirements/dev.txt:748`, `requirements/release.txt:982`.

pip-audit flags setuptools 84.0.0 for GHSA-xmj3-9gf7-h52w; fixed in 84.1.0. Advisory describes Windows legacy wheel-install metadata path traversal creating fixed-content __init__.py outside the destination.

Preconditions: The vulnerable legacy installation path runs on Windows with a crafted wheel. Harnessie supports macOS/Linux shell workflows; this is a low-applicability build-tool maintenance finding, not runtime compromise on this host.

Evidence: Fresh pip-audit JSON retained. No exploit was run and no real credential accessed.

Mitigation: Refresh both hash-locked tooling profiles to 84.1.0 through the repo lock generator, review the lock delta and run installed-lock, build and fresh-install gates.

Regression/eval: Lock manifest consistency, supported-platform resolution, zero-advisory rescan and package smoke.

## Deterministic assurance work beyond individual fixes

The highest-value addition is an adversarial contract suite that traverses the real adapters, runner, registry, evidence consumer and event sink. Assert denied side effects, consumed bytes and retained accounting, rather than matching reassuring prose or merely counting tests.

| Priority | Proposed eval or script | Evidence and acceptance target |
|---|---|---|
| P2 | EVAL-LIFETIME: Add a native backend process-lifetime fixture: an exited parent with detached child/pipe must not mutate workspace after the transaction returns or evade blast-radius accounting. | Static subprocess.run lifecycle review and shim-only reviewer observation; native descendant-lifetime bypass was not established. Do not count as a confirmed sandbox escape. |
| P3 | EVAL-DIRECTORIES: Define directory creation/deletion/mode accounting, then add cases. _delta compares entries but not directories; creating an empty directory passes zero file/edit/byte limits. | assurance.py; present counters are files/bytes, so treat as contract precision and resource-bound extension rather than claiming existing file counter arithmetic is wrong. |
| P2 | EVAL-BLAST-RESOURCES: Bound snapshot resource cost and exercise oversized preexisting trees/special files, rollback failure, metadata and hardlink semantics. | Static _snapshot reads whole regular files; artifact-volume limits are post-operation net snapshots, not peak disk/memory limits. |
| P2 | EVAL-ATIF-PARALLEL: Add real parallel-run ATIF acceptance to check interleaved role/step attribution and refusal behavior. | Coverage gap from serial trajectory assumptions; no attribution exploit claimed. |
| P3 | CHECK-DOWNSTREAM-PINS: A deterministic script should compare in-repo dogfood Action/core pins with the authoritative downstream receipt, while allowing deliberately documented version exceptions. | .github/workflows/verify-pr-claims.yml:43 still references Action 0.2.2; current receipt says 0.2.3. |
| P1 | CHECK-NATIVE-COVERAGE: Require an explicit native-backend coverage receipt for security release gates, and fail required suites if all native cases skip. Add controlled filesystem Unix-socket fixtures for Linux bwrap/firejail. | Default outer-sandbox run skipped 43 tests; native elevated run executed 50 Seatbelt tests. Linux filesystem Unix-socket exposure is disclosed but unprobed. |
| P2 | CHECK-RELEASE-CLAIMS: Require fresh-install checks that bind release version, outward/inward hashes, actual package bytes and release-critical claim/check configuration. | Build, installed consumer, source delivery and human acceptance are distinct; existing candidate gates do not exercise the new adversarial findings. |

Each confirmed finding has a concrete regression recommendation above. Promote critical cases into the published deterministic eval corpus as well as focused unit tests. Add mutation checks that invert each supported expectation and require failure, so a green scorecard cannot silently omit the asserted property.

## OWASP coverage and applicability

The 2021 crosswalk is retained for comparability with the July audit, rather than presented as the latest OWASP edition. Harnessie is a CLI/library, not an inbound web service; server CORS, sessions and route rate limits are not applicable. Static Pages header warnings are known hosting residuals and were not re-audited live.

| Category | Coverage |
|---|---|
| A01 | Ownership and approval bypasses (001, 005). |
| A02 | Secret/PII transform ordering (008); no new custom cryptographic primitive finding. |
| A03 | Command arrays, safe YAML and structural Markdown injection reviewed; metadata integrity issue reported under A08 (014). |
| A04 | Resume/conversation/resource/adversarial/contract behavior (004, 009, 012, 013, 015, 016). |
| A05 | Finite numeric config gap (020); fail-closed defaults reviewed. |
| A06 | Setuptools tooling advisory; runtime audit clean. |
| A07 | Outbound credential redirects (002); no inbound account/session surface. |
| A08 | Content-addressed evidence, cached acceptance, record structure, XML/eval/audit claim integrity (003, 006, 010, 014, 017, 018, 019). |
| A09 | Event privacy and unknown accounting (007, 011). |
| A10 | Outbound destinations are operator configured; no arbitrary agent-supplied fetch URL found in production adapters. Redirect credential risk is reported under A07. |

## Privacy and isolation

Three tested privacy boundaries need repair: raw tool content reaches events before containment (007), secret/PII overlap enters a reversible map (008), and concurrent Responses histories can mix (004). Exported decision prose and whole-file log rewrites remain documented operator-review boundaries. No real secrets, private captures, model reasoning or credential stores were accessed for the audit.

## Delta from prior audit

Prior SEC-001 is resolved: runner.py:374 and :766 call guard_result for prior-model reports. tests/test_runner.py::test_prior_phase_report_is_quarantined_into_next_task passed in the full suite. No other historical security claims are assumed current.

The July review covered 3,368 lines and one low finding. This audit scanned 17,006 Python lines, inspected additional critical paths and reproduced issues with separate reviewers. The counts reflect different scope and are not a measured regression rate. Search-decoder finding 017 was already queued separately; the other current findings are newly recorded here.

## Remediation sequence

| Stage | Work | Completion evidence |
|---|---|---|
| P1 | 001-006: inode-safe writes, no credential redirects, immutable evidence, per-conversation adapters, deny precedence, resume contract binding | Each repro must become a refusing/isolated result, with legitimate positive controls and an independent adversarial pass |
| P2 | 007-014: event ordering, secret transforms, cumulative/unknown usage, response status, bounded resources, explicit convergence and trusted record metadata | End-to-end evals prove no leaked canary, unauthorized dispatch, fabricated independence or lost accounting |
| P3 | 015-020 and dependency item: prompt/check contracts, XML, eval schema, audit claim precision, finite config, tooling lock | Focused deterministic regressions, reviewed lock refresh, zero-advisory supported profiles and docs aligned to behavior |
| Release | New repair version and release metadata only after disposition of blockers; downstream Action/wrapper/tap work follows published core | Full installed locked suite, native coverage receipt, package/provenance checks and separate publication authority |

Effort: each localized fix is a bounded tranche; resume identity/accounting and process supervision require broader contract work. No reliable time estimate is asserted before design/review. Maintain eval-first behavior changes and preserve the original local work.

## Handoff reconciliation

| Queue | Observed state and disposition |
|---|---|
| Repository-state review | Security-first direction and old branch preservation verified. Durable priority, source identity and this audit are transferred into NEXT; temporary review handoff is removed after destination verification |
| Qwen review | Wire-budget and Seatbelt source repairs are present on main. Prior attempt is consumed; new implementation identity invalidates old preparation. Keep handoff pending; no inference, reseal or metadata call |
| README verifier-first | Rewrite remains pending, including stale downstream paragraph. Keep handoff and its trial acceptance requirements; do not present mock proof as independent review |
| Sponsors | Root SPONSORS.md remains absent. Keep handoff; optional README Sponsor link remains an owner choice |
| Search decoder | Defect independently reproduced and recorded as 017. Keep handoff until its patch/review/merge boundary is satisfied |

## Positive controls

- Native Seatbelt boundary suite: 50 passes, no skips.
- Default network denial and per-agent read-only overlays, with fail-closed backend admission.
- Strict evidence-bundle required-claim coverage and malformed verdict refusal.
- Explicit consent-aware dispatch and retained human arbitration state.
- Pilot consume-once guards, bounded private captures, no-redirect transport and strict usage handling.
- SHA-pinned GitHub Actions, hash-locked release dependencies and original-build provenance verification.
- July interphase-report quarantine finding repaired and regression covered.

## Methodology and limits

Three independent scoped review contexts inspected containment/tools, verification/governance, and model/pilot/release paths. The parent reproduced their retained scripts and reviewed eval/plugin/blast-radius/config machinery. This is a code/security assessment, not an authenticated cross-vendor release approval or a claim of exhaustive proof over every path.

No live model/provider calls, paid inference, real service control sockets, production data actions or outbound attack traffic occurred. Dependency installation/advisory queries used public registries. No Linux backend, live DNS/Mach IPC or Windows exploit was exercised. Detached-process accounting, parallel ATIF behavior and Linux filesystem Unix-socket exposure remain specifically identified validation gaps, not confirmed new sandbox escapes.

Bubblewrap itself notes that sandbox protection depends on invocation policy and that a visible service socket can enable commands outside the sandbox; this supports adding controlled Linux IPC fixtures, not claiming a host-specific exploit from static configuration alone. See the [upstream security discussion](https://github.com/containers/bubblewrap/blob/main/README.md). The category crosswalk uses [OWASP 2021 primary material](https://github.com/OWASP/Top10/blob/master/2021/docs/en/index.md).

Tools and checks: Bandit 1.9.4; pip-audit 2.10.0; existing Python 3.13.9 and isolated hash-locked CPython 3.12; pytest, native Seatbelt, all 70 evals, schema/manifest/ecosystem/docs/search checks, lock consistency, package inspection and installed smoke. Exact structured results and evidence SHA-256 values are in the companion JSON.

Issues created: none. Runtime remediations: none. Commit/push/tag/release/deployment: none. Audit outputs and NEXT queue changes are left uncommitted for review.
