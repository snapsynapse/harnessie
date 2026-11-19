# Harnessie 1.5.1 security repair

Harnessie 1.5.1 repairs the findings in the November 18 security audit. The release workflow builds and attests the wheel, source distribution, CycloneDX SBOM and checksum record from the signed `v1.5.1` tag. The [release execution record](audits/release-1.5.1.md) tracks the exact commit, artifacts and publication checks.

## Security repairs

- Close the 20 runtime and documentation findings in the [November 18 audit](audits/security-review-2026-11-18.md): ownership and hardlink confinement, provider redirect handling, evidence byte binding, parallel Responses isolation, approval precedence, resume reuse binding, tool-result containment, budget replay and unknown usage, bounded reads and deadlines, adversarial stand-down, decision-record escaping, verifier contracts and exit classification, search decoding, eval validation, audit-chain claim accuracy, and numeric validation. The [1.5.1 changelog](CHANGELOG.md#151-2026-11-19) lists the exact behavior changes and refusal names.
- Raise the build backend floor and refresh the hash-locked dev and release profiles from setuptools 84.0.0 to 84.2.1, resolving the audit's remaining dependency finding. The runtime dependency lock is unchanged.
- Prevent a credential prefix cut by the `read_file` or `run_shell` output ceiling from reaching a model or event log. An unfinished trailing non-whitespace token is withheld at each cut, including an ordinary long token. Full recognized credentials remain redacted, and the selected containment boundary can still halt egress.
- Exclude proxy CONNECT handshake bytes from provider-request accounting. A proxy failure before the provider request is a known-zero network error; a request that may have reached the provider retains unknown-usage handling.

## Compatibility and limits

- A deterministic check that never launched now returns CANNOT VERIFY (exit 2). A launched check that fails, times out, or escapes cleanup remains FAILED (exit 1). Downstream Verify Action, Ringer and Harbor consumers must verify this contract against the released core before changing their pins.
- A reused passed phase now refuses resume when its bound contract or output has drifted. Older journals cannot reuse passed phases. A provider turn with unknown usage stops metered execution and requires a new run.
- The output cap may withhold an entire oversized single-token JSON value or URL. Raw `proofs/check-*.txt` remain operator artifacts containing unredacted check output. A detached `setsid` descendant that closes its pipes can outlive the transaction. Resume does not bind model configuration, memory, ownership, approval or boundary configuration. The HTTPS proxy CONNECT handshake is outside the transport watchdog. See [SECURITY.md](SECURITY.md) for the full operating limits.

## Verification and remaining limits

The [candidate verification receipt](audits/release-1.5.1-candidate-2026-11-18.md) records 2,319 passing tests, 76 passing evals, native macOS Seatbelt coverage, a passing hash-locked 1.5.1 build, artifact inspection and a fresh-install smoke against the retained wheel. All three lock profiles had no known vulnerabilities at query time. Exact-commit CI passed on the merged security and adoption source; the release workflow verifies the signed tag and builds its own artifacts. The local GuideCheck result is Level 3. Hosted verification and the independent DNS anchor are tracked separately in the release execution record; an earlier guide receipt does not cover the 1.5.1 bytes.
