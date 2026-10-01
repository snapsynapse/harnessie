# Claude Haiku context policy offline implementation

Date: 2026-10-01
Scope: approved offline implementation, rehearsal and verification
Status: implemented and rehearsed; zero live allowance

## Decision

Sam approved a separately versioned full-evidence policy for the existing Claude Code pilot. `claude-max-haiku-context/v2` permits only the exact first-party `claude-haiku-4-5-20251001` identity as additional unclassified usage while the requested and attributed answer model remains `claude-fable-5-1`.

The approved candidate ceilings are:

| Boundary | Ceiling |
|---|---:|
| Haiku cache-inclusive input per invocation | 96,000 tokens |
| Haiku output per invocation | 256 tokens |
| Haiku cache-inclusive input per run | 256,000 tokens |
| Haiku output per run | 2,048 tokens |
| All-model reported tokens per run | 800,000 tokens |
| Claude calls | 8 total, at most 4 per stage |
| Automatic retries | 0 |
| Encoded input per invocation | 256,000 bytes |
| Cumulative evidence per invocation | 256,000 bytes |

These are post-response acceptance and stop thresholds, not provider billing caps. Reported usage is retained before a refusal. Exact-limit use is accepted, and the next reservation or any one-token overage refuses and latches the run.

The previous `claude-max-haiku-overhead/v1` policy remains unchanged at 4,096 cache-inclusive Haiku input tokens and 256 Haiku output tokens per invocation. The default exact-model-only policy also remains unchanged. Callers cannot construct a fourth permissive selector.

## Authority boundaries

This approval covered local source, tests, documentation, a synthetic offline rehearsal and a Git commit. It did not authorize inference, a nonzero live allowance, billing-route changes, account changes, push, release or deployment.

The policy does not prove what Haiku does internally, what content it receives or whether it influences Fable. All material disclosed to this Claude Code route must remain appropriate for both reported Anthropic identities. The current first-party OAuth contract is necessary but not sufficient for dispatch. A final live packet must still contain fresh evidence that the request consumes included Max allowance, that usage credits are off and that the CLI identity and auth class have not drifted.

## Offline full-evidence rehearsal

The four-stage workload rehearsal used the real pilot encoders, deterministic injected responses and socket refusal. Each participant made four turns in each of its two stages. Every stage read all 17 declared evidence files before returning a labeled synthetic position or objection.

- 16 of 16 encoded requests were admitted.
- Maximum evidence size was 196,632 bytes.
- Maximum encoded request size was 219,150 bytes.
- The workflow stopped at `needs_arbitration`.
- Live model calls were zero.
- The synthetic Haiku profile totaled 207,702 input tokens and 144 output tokens across eight Claude fixtures.
- The synthetic token profile is a budget-path fixture, not provider evidence or a usage prediction.
- The request journal contains 16 valid records with tail `394e6899a45a7e968593684553155153a241ead2a07eea7a917a36109953ea6d`.

The retained report is `runs/pilot-haiku-context-v2-2026-10-01/runs/pilot-haiku-context-v2-offline-2026-10-01/operator/workload-sizing.json`, with canonical parsed-JSON SHA-256 `7b97349341dcb47240710296175e9bd2b8929a7e88d08e8b2fc78e634dc805ed`.

## Verification

Focused tests cover the frozen selector, unchanged v1 policy, exact per-call and run-wide boundaries, one-token overages, raw-usage retention, execution-manifest drift, zero-authority refusal and complete offline workload rehearsal.

- Pilot suite: 197 passed.
- Full offline suite: 908 passed, 9 skipped, 28 expected failures.
- Deterministic eval scorecard: 66 of 66 passed.
- Dependency locks, generated docs and offline search checks passed.
- Isolated build, wheel and sdist inspection, metadata check and fresh-install smoke passed.
- `git diff --check` passed.
- Independent read-only review found and caused correction of a legacy 40-call and 20-call-per-stage validator ceiling. Re-review confirmed that exact and lower limits pass while 9 participant calls or 5 calls per stage refuse. Its focused suite passed 73 tests.

## Next separate gate

Prepare one exact final live candidate from the reviewed sources. Before asking for execution approval, refresh and bind the CLI executable, version, first-party OAuth class, local Qwen identity, included Max allowance and credits-off evidence. Keep `live_allowance` at zero until Sam approves that sealed candidate. A later live result still requires Sam's human arbitration and does not authorize push, release or deployment.
