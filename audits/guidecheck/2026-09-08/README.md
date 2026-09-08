# GuideCheck verification and 1.3.0 preparation

Scope: Harnessie core. Sam unblocked GuideCheck on 2026-09-07 local time and applied the DNS change himself through Namecheap. Evidence timestamps below are UTC on 2026-09-08. Package publication remains on hold.

## Current 1.2.0 guide: external gate completed

The [initial hosted receipt](hosted-1.2.0-before-dns.json) reported Level 3 because DNS still advertised the 1.1.0 guide hash. The served 1.2.0 guide, sidecar and repository copy already agreed. After Sam replaced the existing TXT record, the [DNS response](dns-after.json) and [fresh hosted receipt](hosted-1.2.0-after-dns.json) matched the current bytes:

| Property | Observed result |
|---|---|
| Hosted verification time | 2026-09-08T01:15:44.006688Z |
| Guide version / selected profile | 1.2.0 / 0.7.1 |
| Guide bytes | 7,947 |
| SHA-256 | `ff77d219add6f1cf6a22c4570830f9fbd70cedd59f3caa933fbd0c7ae3733421` |
| Level / blocking findings | 4 / 0 |
| Matching evidence | Fetched sidecar, DNS TXT, repository file |
| Warnings | Missing `X-Content-Type-Options: nosniff` and HSTS response headers |

The hosted tool retains the frozen legacy report contract for a guide declaring profile 0.7.1. Its legacy `level5_ready: true` field is not proof of runtime enforcement; the receipt explicitly says Level 5 is not evaluated. This is neither profile-2.0.0 conformance nor a software-safety assessment. DNSSEC was not established: the DoH response has `AD: false`.

The current Namecheap record is type `TXT Record`, host `_assistant-guide`, TTL `Automatic`, with one value:

Literal
```text
v=1; sha256=ff77d219add6f1cf6a22c4570830f9fbd70cedd59f3caa933fbd0c7ae3733421; url=https://harnessie.com/.well-known/assistant-guide.txt
```

No package, tag, guide bytes, or DNS settings were changed by the assistant. Public status-copy edits are local preparation until delivered and deployed.

## Separate 1.3.0 candidate: local preparation complete

[Candidate guide](candidate-1.3.0/assistant-guide.txt), [sidecar](candidate-1.3.0/assistant-guide-manifest.txt), [promotion values](candidate-1.3.0/promotion.json), and [local verifier result](candidate-1.3.0/local-result.json) are prepared outside the served tree. Root and served guides retain their coherent published 1.2.0 identity. Promote the candidate with the coordinated package/version/docs tranche in [release preparation](../../release-preparation-2026-09-07.md); do not copy only one guide or advertise an unpublished package as stable.

Changes in the candidate:

- Select GuideCheck profile 2.0.0 and matching sidecar selectors, with verifier range `>=2.0.0, <3.0.0`.
- Use guide version 1.3.0, its future package URL and the reviewed date.
- Add only a read-only `OBSERVER.md` action. Explain that observation writes derived output and does not resume, approve or certify a run. Preserve all five deferred feature boundaries from AIDR-0009.
- Remove stale expected test counts. Require actual outcomes and revision identity.
- Correct the claim that budget ceilings imply an offline, zero-cost run: the configured routing includes live providers.
- Replace the claim that the guide removes execution risk with its actual advisory limits. Repository matching corroborates bytes but is not a qualifying independent anchor under profile 2.0.0.

The released [GuideCheck 2.0.0](https://github.com/snapsynapse/guidecheck/releases/tag/v2.0.0), published at 2026-09-08T01:04:20Z, is available in the clean local checkout at commit `0991c18ec6dd8b966d67bab9802f6559e7e74b91`. The candidate evaluates under `corrected-content-1` and `1.0.0-strict`: Level 3, valid matching sidecar, zero warnings, and one expected Level 4 blocker, `anchor.independent.missing`. No fetched independent evidence exists for these unpublished bytes. The report says `Proceed? no`; it is not a hosted acceptance receipt.

The candidate is 7,766 ASCII bytes, SHA-256 `5e00fa6903e0d42c49e9a25c08eec19116b04bf01ee0daf8c4d7d754b58b0793`. The future DNS value is in the explicitly marked draft promotion file. Do not apply it while the current 1.2.0 guide is live. Any edit invalidates these hashes and the local result.

Reproduce the local candidate check using the complete GuideCheck 2.0.0 checkout:

Replace: GUIDECHECK_CHECKOUT -> absolute path to the verified GuideCheck 2.0.0 checkout
Customize
```bash
python3 "GUIDECHECK_CHECKOUT/scripts/guidecheck_verify.py" audits/guidecheck/2026-09-08/candidate-1.3.0/assistant-guide.txt --manifest audits/guidecheck/2026-09-08/candidate-1.3.0/assistant-guide-manifest.txt --require-profile-version 2.0.0 --level 3 --pretty
```

## Final candidate acceptance order

1. Finish the remaining approved release content and accessibility acceptance. Promote final guide/version/docs/trust changes together and qualify the exact candidate. Replace current Level 4 claims with pending status whenever guide bytes change; the current receipt must not qualify new bytes.
2. Deliver and deploy the final guide and sidecar through reviewed source changes. Independently compare the served bytes and repository copy to the candidate digest.
3. If needed, create the authorized signed `v1.3.0` tag without publishing a GitHub Release. The candidate sidecar points to `https://github.com/snapsynapse/harnessie/tree/v1.3.0`, which identifies the tagged source without requiring a published GitHub Release. Check actual URL reachability and tag-to-commit identity; do not infer them from a syntactically valid manifest. No such tag existed at this verification baseline.
4. Give Sam the exact final Namecheap value. He replaces the existing record. Read public DNS and run hosted verification with `required_profile_version: "2.0.0"` so policy mismatch refuses rather than silently selecting legacy evaluation.
5. Require the dated hosted result to match guide, sidecar, repository, selected profile and qualifying DNS evidence, with Level 4 and zero blocking findings. Preserve warnings and their dispositions. The current CLI/API does not independently establish the reachability of `immutable-release-url`; record the explicit URL check in addition to the receipt.
6. Only after all remaining release gates and publication approval may a GitHub Release trigger packaging. PyPI, Verify Action and Homebrew follow their existing sequence. Changing guide bytes restarts this checkpoint.

The current 1.2.0 anchor is closed. Final 1.3.0 promotion, tag/URL identity, deployment, DNS rotation and hosted acceptance remain open. This packet does not waive the 36 accessibility review candidates or manual release checks.

## Preparation validation

The final local checks passed: 26 guide/version/machine-resource/trust tests, 21 outward and 16 inward manifest entries, nine generated documentation pages, and the ten-page search contract with zero defects or infrastructure failures. The [candidate artifact checks](candidate-1.3.0/artifact-checks.json) verify byte limits, hash/selector parity, eight bounded read-only action targets, and the expected local-only anchor limitation. Guide actions were not executed. No runtime code changed, so the full package-building gate was not rerun for this documentation/evidence tranche.
