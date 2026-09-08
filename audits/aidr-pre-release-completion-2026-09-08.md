# AIDR pre-release completion

Date: 2026-09-08. Scope: Harnessie core, local completion before the 1.4.0 release candidate. Sam approved this packet after merging PR #18 as `5c157999af2aaaa5eec67752f5a3cf023132d5bd`. Branch: `codex/aidr-pre-release-completion`. Published core and downstream pins remain 1.3.1. No publication is claimed by this record.

Version selection after this snapshot: Sam selected 1.4.1 for package and guide. The development-guide identity and artifact digests below describe the earlier verification snapshot. Current version evidence is in [1.4.1 preparation](version-1.4.1-preparation.md).

## Completed scope

- Platforms lacking POSIX locking, required flags, file functions or declared descriptor/no-follow capabilities now refuse with `unsupported_platform` before reading or writing project data. A fresh-process missing-`fcntl` test covers the original import failure. Native Windows export remains unsupported.
- The [executable example](../examples/aidr-export/README.md) uses the actual `WorkflowRunner` and two scripted mock actors with repeated roles and dissent. It invokes the installed export CLI, checks the output with the pinned AIDR 0.1.0 linter, verifies unchanged run inputs through export/lint, and demonstrates that resuming the original run still requires human arbitration. Resume itself appends normal runtime events. A second actual mock run deliberately produces unsupported formatting and verifies safe refusal.
- The fresh-wheel smoke runs that same example outside the checkout, removes `PYTHONPATH`, and verifies that Harnessie was imported from the fresh virtual environment. The source distribution includes the example and pinned reference files; the runtime exporter has no Node dependency.
- Architecture, governance, security, eval documentation, user guide, README, exporter contract and changelog describe the same operator-issued write boundary and qualified provenance. Capability declarations, CLI discovery and language-model discovery expose the source-only command. Generated guide HTML and outward manifest pins match their producers.
- Current planning distinguishes completed 1.3.1 publication, the merged exporter, this completion pass and future candidate/publication gates. The earlier implementation audit remains unchanged as dated evidence for earlier bytes.

## Validation

| Check | Observed result |
|---|---|
| Full suite, Python 3.13.9 on macOS with OS sandbox access | 718 passed, 1 skipped, 28 expected failures |
| Deterministic evals | 66/66 passed |
| Focused exporter, CLI, demo and pinned reference tests | 144 passed, independently rerun |
| Machine discovery, version identity and guide artifact tests | 24 passed |
| Authoring validation | 9 documents valid |
| Outward and inward manifests | 21 and 16 files valid |
| Ecosystem inspection | Four components inspected; core/downstream 1.3.1 pins match, wrappers remain 0.1.0 |
| Generated docs and offline search | Nine pages current; ten sitemap pages, zero defects |
| Dependency locks | Runtime, development and release definitions valid |
| Development wheel and source distribution | Build, Twine and artifact inspection passed |
| Fresh installed-wheel consumer | Passed, including real mock runner, installed export, pinned lint, preservation and continued human halt |
| Independent final review | PASS: 168 focused tests, fresh-wheel smoke, guide receipt, generated docs, trust pins and all 32 source/two artifact digests |
| Diff whitespace | Passed |

The one skipped test requires explicit live-provider opt-in. The 28 expected failures are deferred features. No live provider evaluation ran. Platform absence was simulated in fresh processes and isolated tests; no native Windows host was exercised. Initial integration checks caught a guide line longer than 120 bytes and a renamed planning heading required by an existing eval; both were corrected. Incorrect options used while invoking two existing check scripts were corrected without changing the scripts or their contracts.

The package artifacts retain source version 1.3.1 solely for development verification. They are different bytes from published 1.3.1 distributions and must not be uploaded as replacements. [Machine-readable state](aidr-pre-release-completion-2026-09-08/state.json) records reviewed source and artifact digests.

## Guide identity and trust boundary

The changed source guide has a distinct development identity, `1.4.0-dev.1`; the package remains 1.3.1. Its registry URL names that stable package, explicitly explained in the guide. The sidecar targets the future 1.4.0 tag. GuideCheck profile 2.0.0 permits a future immutable release URL during authoring and requires reachability at publication. The version test permits this development identity only while source publication is pending and no current hosted receipt is claimed; it requires finalization when the package reaches that target version.

The [local reference result](aidr-pre-release-completion-2026-09-08/guidecheck-local.json) achieved Level 3 under profile 2.0.0: 8,052 bytes, a matching local sidecar, and no content findings. It exits 1 with one blocking finding, `anchor.independent.missing`, because no fetched qualifying independent anchor exists for these new bytes. This is an expected unresolved publication gate, not a clean hosted pass. The [1.3.1 hosted Level 4 receipt](release-1.3.1/guidecheck-prepublication.json) is preserved as historical evidence for different bytes. No DNS or hosted state changed in this packet.

## Next release packet and deferred scope

Prepare the 1.4.0 candidate by finalizing package/guide versions, changelog and release notes; run the complete release gate and inspect the exact artifacts. Commit/PR delivery, merge, signed tag, package publication, hosted deployment and downstream propagation remain distinct delivery steps. After final guide deployment, refresh its independent anchor and obtain exact-byte hosted acceptance before claiming current Level 4.

Accessibility remains deferred for this session and its handoff is untouched. The earlier 1.3.1 disposition does not establish manual acceptance for newly changed routes. Before new publication, complete the changed-route checks required by the release checklist or record Sam's explicit release-specific disposition. No fresh accessibility pass is claimed.

Live review panels, arbitration import, broader source formats, bidding, commentary, follow mode, runner integration, model selection, MCP and provider policy remain outside this packet. No real human arbitration record was changed.
