# Coordinated CodeQL Action update

Date: 2026-10-03 (America/Denver)
Base: `38ac73782e6f7f266fb7d75b4aafa304ce53e7db`
Scope: local GitHub Actions maintenance, approved with the offline pilot repair.

## Failure evidence

The four open Dependabot pull requests independently update subactions from
`v4.38.0` to `v4.38.2`:

| Pull request | Subaction | Observed CodeQL check |
|---|---|---|
| [#33](https://github.com/snapsynapse/harnessie/pull/33) | `init` | Failed |
| [#34](https://github.com/snapsynapse/harnessie/pull/34) | `upload-sarif` | Passed |
| [#35](https://github.com/snapsynapse/harnessie/pull/35) | `analyze` | Failed |
| [#36](https://github.com/snapsynapse/harnessie/pull/36) | `autobuild` | Failed |

The [#33 failed run](https://github.com/snapsynapse/harnessie/actions/runs/36697061137)
reports: `Loaded a configuration file for version '4.38.2', but running version '4.38.0'`.
Its diff updates `init` while leaving `autobuild` and `analyze` at `v4.38.0`.
The current [#35](https://github.com/snapsynapse/harnessie/actions/runs/36697259453)
and [#36](https://github.com/snapsynapse/harnessie/actions/runs/36697369459)
checks also fail; their diffs similarly mix versions. Those two logs were not
separately re-read for this maintenance record.

## Local change

- Pin all four subactions to `2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2` (`v4.38.2`).
- Add one Dependabot version-update group with pattern `github/codeql-action/*`.
- Preserve workflow events, permissions and other steps, and the existing pip configuration.

Authenticated GitHub API reads verified that the upstream
[`v4.38.2` tag](https://github.com/github/codeql-action/releases/tag/v4.38.2)
points to annotated tag object `88585263c0627ee42c0e1c5143a112c8d6f4aa18`, which
peels to the pinned commit. All four existing pull request diffs use that commit.
The tag object is unsigned; this check establishes ref identity, not signature verification.

GitHub's [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups)
documents that matching dependency names are combined in one pull request and
that `patterns` supports `*`. The default grouping scope is version updates.
Unrelated actions and the pip ecosystem remain outside this group.

## Verification

- Fetched `origin`; base `main` was clean and zero ahead/behind both upstream and `origin/main` before editing.
- Parsed both modified workflows and Dependabot configuration with PyYAML 6.0.3.
- Compared parsed workflows against `git show HEAD:<path>`, allowing only the four pin replacements. Passed.
- Compared parsed Dependabot configuration against the base, allowing only the CodeQL group. Passed.
- Checked the group pattern against all four subaction names and unrelated checkout, upload-artifact, Scorecard and similarly prefixed action names. Passed.
- Ran `git diff --check` on the three configuration files and this audit. Passed.
- `actionlint` was unavailable and was not installed.

Hosted CI has not run against this combined candidate. The green check on #34
does not execute the modified Scorecard workflow, which runs on main pushes and
its schedule. Hosted CodeQL and Scorecard acceptance remain unverified until
the candidate is delivered and those workflows execute. Existing pull requests
were not changed, closed or merged. This maintenance produced no commit or push.
