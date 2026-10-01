# First guarded live panel attempt

Scope: the recommended live panel authorized by Sam, using the Claude Max subscription with usage credits off and Qwen only through local Ollama. Human arbitration and Git delivery remain separate.

## Authority and readiness

Sam explicitly approved the live panel, then approved turning usage credits off. The operator clicked the enabled switch; a confirmation dialog appeared and the page changed before an operator confirmation click could be made. A fresh navigation to the Usage page verified the switch and checkbox unchecked. This proves the saved off state; it does not establish who completed the dialog. The Max (5x) account displayed Fable weekly usage at 0%, session usage at 2%, balance USD 0 and auto-reload off. No enable, credit purchase or spending-limit change was made. A later read-only post-run browser check was unavailable because the shared page/context had closed; the fresh pre-dispatch observation remains the billing evidence.

Both identities passed before dispatch. Claude Code 2.1.261 reported first-party Max authentication. Local Ollama server 0.34.2 served metadata for `qwen3.8:latest` with digest `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643` and local blob paths. No model download, service change or remote Qwen route was used.

Operator manifest and approval: `runs/pilot-live-approved-20260920T043028Z/`. Manifest digest: `bc4b8951f52a5423f7b52ce0df76f71fd944aed63caf8508f773cddb4c00ddfd`. Frozen input seal: `626322d26c8bca5dd1afaf351612336eaa038aef504b106ad80f445dcfece742`. Candidate limits were unchanged: eight calls per participant, four per stage, 400,000 aggregate reported tokens, and the bounded Haiku exception.

## Observed outcome

The run is incomplete. The first Claude position invocation returned a stream the adapter rejected as `stream_malformed`. The workflow reported `stage_failed`; no accepted position, objection, exported decision or human arbitration resulted. The exact failure branch cannot be reconstructed from retained evidence.

- Provider dispatches: Claude 1; Qwen 0. The run stopped before local Qwen inference.
- Reported usage: 1,752 input, 539 output, 5,395 cache-creation input, 0 cache-read input tokens. All-model aggregate: 7,686.
- Reported Fable usage: 2 input, 521 output, 5,395 cache-creation input tokens.
- Reported Haiku usage: 1,750 input and 18 output tokens. Policy disposition was `not_evaluated` because stream validation failed first. Usage identities do not establish accepted answer attribution.
- Actual subscription dollar cost remains unknown. Provider list-price equivalents in raw modelUsage are not billed-dollar evidence.
- Operator ledger: valid, six records, tail `e5fd06bd64f6a41b5dddcd94fdc1ca34591df3072519558de0916307601d1448`.
- Runner chain: valid, nine events. Two loop error events represent one provider invocation followed by a latched refusal, not a second dispatch.

Outcome and receipts: `runs/pilot-dispatch-candidate-2026-09-19/runs/pilot-2026-09-19-panel/`. Runner events: its sibling `pilot-2026-09-19-panel-workflow/`. Independent read-only forensic review confirmed these counts and chains. No automatic retry or manual redispatch occurred.

## Architecture finding and next work

The stop and accounting boundaries worked. Diagnostic evidence retention was insufficient: `ClaudeCodePilot.complete` parses process stdout in memory and retains usage maps, but does not persist the full stream or precise parser-failure context. Stderr is discarded. The broad failure code alone does not justify relaxing parser checks or attributing the failure to Haiku, a provider change, or any specific event.

Next recommended offline repair: retain bounded provider-response bytes before parsing in an operator-private artifact, link its hash/path and capture status to the durable receipt, and record a precise parser-failure reason without weakening model/tool/session binding. Test capture-write failures, malformed responses, limits and zero additional dispatch. Any sanitized derivative must be clearly distinguished from exact captured bytes. Do not scan unrelated provider sessions for lost output.

The consumed run is single-use. Preserve it unchanged. After offline repair and independent review, prepare a new exact manifest and obtain a new execution decision; the failed run is not resumable and remaining numerical headroom does not authorize a retry. Usage credits should remain off under Sam's instruction. No commit, push, release or deployment occurred.

## Subsequent repair

The [offline response-retention repair](pilot-response-retention-2026-09-19.md) is implemented and independently verified. It does not recover this run's lost stream or change its incomplete outcome. The linked record owns the new execution proposal and current approval boundary.
