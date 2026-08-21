# Harnessie 1.1.0: the Golden Rule becomes inspectable

Harnessie 1.1.0 turns its ownership invariant into a memorable public contract and an executable proof:

Read together. Write only what you own.

## Highlights

- `harnessie ownership PATH --agent AGENT [--json]` explains the exact write decision used by the ownership ledger without claiming or changing the path. Human output names the governing lane, owner, pattern, reason, and remedy. JSON output uses schema version 1.
- The zero-model, zero-network ownership-collision example performs a real overwrite attempt through the built-in `write_file` registry and passes only when the second agent is denied, the original bytes survive, and the ledger still names the first writer.
- The website, README, Guide, `llms.txt`, `agents.json`, local CLI manifest, machine-readable changelog, assistant guide, roadmap, and project context now describe the same shipped 1.1.0 behavior.
- Search discovery and generated-page contracts added since 1.0.0 remain part of the release gate.

## Verification

- 433 tests passed with 1 environment-dependent skip.
- Deterministic eval scorecard: 50/50.
- Nine shipped authoring documents validated against schema v1.
- Outward trust manifest: 19 files. Inward manifest: 15 files.
- Nine generated documentation pages and ten-page search contract verified.
- Wheel and source distribution passed `twine check`, structural inspection, private-surface scrubbing, and fresh-install smoke.
- Ownership adversarial coverage includes workspace escapes, absolute paths, control characters, symlink resolution, invalid agents, declared-lane precedence, first-writer denial, allowed-decision false-positive checks, and proof that inspection does not mutate the ledger.

## Trust boundaries and release residuals

- `harnessie ownership` is an explanation surface, not an authorization grant. Enforcement remains in the registry, runner preflight, ownership ledger, and OS sandbox.
- Collaborative lanes deliberately allow co-editing, and operator-trusted in-process plugins remain outside child-process lane confinement.
- The 1.1.0 assistant guide and served copy are byte-identical and pinned by the provenance sidecar. The independently controlled DNS TXT anchor still names the 1.0.0 hash until the post-publication rotation, after which hosted GuideCheck must re-verify the new public bytes.
- Harnessie Verify v0.1.2 and the Homebrew formula initially remain on core 1.0.0. Their separately gated release train follows the core publication. Engine wrappers remain independently released at v0.1.0 because 1.1.0 consumes no new wrapper seam.

The complete change record is in [CHANGELOG.md](https://github.com/snapsynapse/harnessie/blob/v1.1.0/CHANGELOG.md#110-2026-08-20).
