# Controlled-review offline follow-up

Date: 2026-10-03 (America/Denver)
Base: 38ac73782e6f7f266fb7d75b4aafa304ce53e7db
Scope: approved offline pilot repair, Qwen smoke preparation and coordinated CodeQL maintenance
Original delivery: local changes only. Subsequent authorized local commits are 4dd08f6 (CodeQL) and da050e1 (pilot). The separately approved [Qwen smoke](pilot-qwen-smoke-result-2026-10-03.md) subsequently completed. No push or release occurred.

## Implemented and reviewed

Three implementation workers owned separate file sets. Separate reviewer contexts inspected the artifacts and acceptance criteria, ran independent checks and reported no outstanding actionable findings. This is review separation within the current agent session, not evidence of model-family diversity.

- [Claude admission contract](pilot-continuation-contract-2026-10-03.md): the v6 intermediary reports output exhaustion and requests continuation. The stream does not authenticate preservation between its two assistant identities. Single-identity admission remains unchanged. Otherwise valid responses now refuse when aggregate reported output across all models exceeds the configured limit, preserving captured bytes and accounting and latching subsequent attempts.
- [Reviewer budget guidance](pilot-output-budget-guidance-2026-10-03.md): each encoded request communicates the actual delegate output ceiling and concise-report guidance. Required evidence, citations, uncertainty and position/objection fields remain required. Tests retain all 17 sources and the four-stage order.
- [Qwen smoke driver and proposal](pilot-qwen-smoke-preparation-2026-10-03.md): preparation-only CLI, fixed synthetic request, separate exact-proposal approval, private exclusive evidence, durable attempt guard, strict local identity/blob checks, no retry and complete accounting. Parent review found and corrected an initially weaker metadata capture before independent acceptance. The one-call proposal remains unexecuted.
- [Coordinated CodeQL update](codeql-coordinated-update-2026-10-03.md): all four subactions pin the verified 4.38.2 commit, with a CodeQL-only Dependabot group. Existing PRs #33-36 are unchanged. Hosted candidate CodeQL and Scorecard results are pending delivery.

The independent admission reviewer reproduced the four original failures against the base adapter in memory, then verified the repaired tests. The guidance reviewer similarly reproduced both original failures against the base notice and reviewer role. The smoke reviewer tested malformed accounting, concurrent attempt exclusion and persistence failures using injected responses with network blocked.

## Integrated verification

The core and pilot suites were partitioned to avoid running the same tests twice. All test and evaluation commands disabled live provider opt-in. No inference was dispatched during this offline tranche; the subsequent live smoke has its own linked approval and result.

| Check | Observed result |
|---|---|
| Core suite, excluding source-only pilot tests | 710 passed, 9 skipped, 28 expected failures; 16.19 seconds |
| Entire pilot suite after integration | 254 passed; 17.07 seconds |
| Deterministic evaluations | 66/66 passed |
| Public trust manifest | 21 files verified |
| Inward manifest | 16 files verified |
| Generated documentation | 9 pages current |
| Offline search contract | 10 sitemap pages; zero defects and infrastructure failures |
| Workflow/Dependabot semantic comparison | Only four pins and CodeQL group changed |
| Whitespace | git diff --check passed |

Reproduce the two test partitions with the configured repository interpreter.

Literal
```bash
PYTHONDONTWRITEBYTECODE=1 HARNESSIE_LIVE=0 .venv/bin/python -m pytest -q -p no:cacheprovider --ignore-glob='tests/test_pilot*.py'
```

Literal
```bash
PYTHONDONTWRITEBYTECODE=1 HARNESSIE_LIVE=0 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pilot*.py
```

The earlier two intermittent transport timing failures did not recur in the integrated pilot run or the independent transport checks. Their underlying cause remains unresolved. The nine core skips and 28 expected failures are retained; these results do not assert coverage for those unavailable or deferred cases. Actionlint was unavailable and was not installed.

## Evidence and remaining gates

The admission reviewer verified the v6 fourth capture against its recorded SHA-256, all four captures against their receipt hashes/lengths, the 26 sealed packet files and the proposal/consumed-approval binding. The original refused outcome remains intact. No pre-work whole-directory hash manifest exists, so these checks do not establish a complete historical-directory immutability proof.

After code stabilized, the parent performed separate read-only local Ollama metadata and blob checks, then generated the private Qwen smoke candidate recorded in its audit. Readback confirmed the canonical proposal digest, exact request bytes/hash, all 63 implementation hashes, self-consistent identity and zero live allowance. Only request.json and proposal.json exist; there is no approval or attempt. Metadata checks are not inference evidence.

At the offline checkpoint, the next gate was Sam's separate approval of the exact local smoke proposal while identity evidence was fresh. That gate and one successful smoke are now recorded in the linked result audit. A new full panel still needs fresh Claude account/allowance/credits-off evidence, verified browser/CLI account correspondence, Qwen identity and separate approval. V6 cannot be retried. Human arbitration follows a completed panel and open-record export. Broader runtime capabilities remain in the existing roadmap sequence.

The implementation and initial documentation were subsequently committed locally as 4dd08f6 and da050e1 under Sam's "Commit locally then proceed" instruction. The smoke outcome and current pickup state are recorded separately. origin/main remains at the base above. The CodeQL candidate needs hosted checks after separately authorized delivery; there is no new package or downstream release. The temporary pilot handoff remains because full-panel work is still pending.
