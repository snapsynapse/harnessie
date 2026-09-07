# Terminal smoke-test record

Date: 2026-09-04. Evidence: operator reports in the session and the four saved readiness reviews. This is a retrospective record, not a new launch test.

| Surface | Runtime version at launch | Prompt receipt | Repository access | Persisted review |
|---|---|---|---|---|
| Codex CLI | Not captured | Evidenced by review | Full, reported by reviewer | [Codex](aidr-0009-readiness-review-codex-2026-09-04.md) |
| Claude Code | Not captured | Evidenced by review | Full, reported by reviewer | [Claude](aidr-0009-readiness-review-claude-code-2026-09-04.md) |
| Antigravity CLI | `agy` 1.1.26 observed during setup | Evidenced by review | Full, reported by reviewer | [Antigravity](aidr-0009-readiness-review-antigravity-2026-09-04.md) |
| Ollama, Qwen | Ollama version not captured; model tag `qwen3.8:latest` supplied by operator | Evidenced by review | None; summary-only input | [Qwen](aidr-0009-readiness-review-qwen3-8-2026-09-04.md) |

Exact serving model revisions for the hosted sessions were not uniformly captured. Current version commands cannot reconstruct those missing historical facts. The Qwen transcript was persisted separately; direct Ollama conversation did not prove filesystem write capability.

Observed: the operator opened four tabs, supplied the review prompt, and saved four reports. Setup included CLI help checks and prompt-file shell expansion. The initial startup instructions needed correction before the later reports were obtained.

Untested: repeatable fresh authentication, exact resume targeting, automated tab creation, unattended orchestration, mailbox delivery, enforced cross-runtime write ownership, and automatic report collection. The review used unequal lane briefs and repository access, so agreement is not a controlled model comparison or calibration result.

For a future reproducibility run, record runtime versions, serving model identifiers where available, branch/HEAD, prompt hash, input-access level, report path, and operator-observed startup outcome before executing the task. Do not capture credentials or full environment dumps.
