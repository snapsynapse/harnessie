# Seatbelt Unix-socket security review, 2026-11-11

## Scope and reconciliation

Sam authorized independent review and testing of `520cc08f83d5a65ea8a6cb130b10be98f17b65af`, repairs, commit and push, with no inference. The original clean `security/seatbelt-unix-socket` checkout was one ahead and one behind fetched main. Its branch and commit were preserved. The selected patch was applied onto current main `184421f72c639a5cbabd91d5b54a6cdab90c25d1` in an isolated review branch, without merging unrelated history.

## Findings and disposition

The original production rules correctly deny outbound filesystem Unix-socket access when network is enabled, with an exact `/private/var/run/mDNSResponder` exception. No production-policy defect was found in the tested boundary. The original statement that local IPC stays closed was too broad: network opt-in still permits TCP/IP, including loopback; Mach IPC is unrestricted. Source comments, security guidance and changelog now state that narrower boundary. Standalone `verify --allow-network` is distinguished from verifier shell tools.

The original tests covered stream connection denial only. New regressions cover stream connect, datagram connect/send and datagram sendto, across canonical, `/tmp`, relative and symlink paths with network both disabled and enabled. Each endpoint has an unsandboxed positive control that delivers a payload. Native tests also substitute a disposable endpoint for the resolver literal, prove that exact exception usable, deny a neighboring endpoint, and check both TCP permission states. Servers use bounded operations and context cleanup without daemon threads.

An independent read-only verifier separately loaded exact committed profiles and used its own disposable fixtures on Darwin 25.6. All nine baseline network-enabled Unix cases reached the fixture on `184421f`, reproducing the gap. The selected patch denied all 24 Unix cases across both network states; all 12 substituted-resolver positive cases and the TCP permission checks passed. Independent final review and execution of the expanded suite passed 50 tests with no skips, on the hashes below. The parent independently passed the same 50-test suite.

## Offline acceptance

- Full native-capable suite: 1,374 passed, four skipped, 28 expected failures. Native Seatbelt security tests were not skipped.
- All 70 deterministic evals passed; configuration validation covered nine documents.
- Outward manifest: 21 files; inward manifest: 16 files; ecosystem manifest: four components; generated docs: nine pages. All passed.
- Wheel and sdist built without build isolation, passed Twine validation, release artifact inspection and private-term checks. The wheel passed the fresh-venv installed CLI/mock walkthrough with no live calls.
- Whitespace and exact-path private-term checks passed. Private scrub patterns were not printed.

No inference, physical model metadata, real service control socket, external internet, real DNS service, Mach IPC or inherited socket test was performed. Resolver-literal substitution proves matching and precedence on this host, not live DNS or HTTPS acceptance. Linux behavior remains unchanged and its Unix-socket exposure remains unprobed. Other macOS versions need their own native evidence.

## Independently verified source identity

| File | SHA-256 |
|---|---|
| `harness/sandbox.py` | `4fe50a52aa69fe2e8e7d4f8c6521e46527726860db01fda065c0beccd31421cb` |
| `tests/test_sandbox.py` | `ea6a947b8958117f046d73e28104feacbd96d87e9cb3335d722798f4aea9b463` |
| `SECURITY.md` | `fb225848ed1ae9972e640d783474e667dfb1219b5ad18ef3bbf636cc8ed5086c` |
| `CHANGELOG.md` | `263baa08a019fd6b154f705706a267d2690216d7a25ce5d9867d0e9f12779a82` |

## Delivery boundary and next use

This is source delivery, with version 1.5.0 unchanged and the change recorded under Unreleased. No tag, GitHub Release, PyPI package or downstream update was published. Installed 1.5.0 consumers do not acquire this repair from a source push; a separately selected patch release and downstream update would distribute it.

Changing `harness/sandbox.py` also changes the implementation identity bound by the earlier zero-authority Qwen preparation. Do not reuse or silently reseal that preparation. Any later Qwen execution still requires fresh physical metadata, a new proposal with current implementation hashes, independent verification and Sam's explicit one-call approval. The 1,200-second and 4,096-token limits and zero-retry policy remain unchanged.
