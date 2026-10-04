# Controlled-review panel v4 and v5 results

Date: October 3, 2026 (America/Denver)
Implementation: b610383bc82fc9ca056487ff7a0cb04358901f2f
Status: both approved attempts stopped before completing a position; no further live authority remains.

## Panel v4

Approved manifest: 928d5e3b7787590100f8750894cad5b038bf73acc6bc19e8e7b9e74108ba2906.

One Fable inference completed. The second reserved attempt refused before inference with auth_identity_drift. The manifest was bound to claude.ai:max:firstParty; a subsequent read-only metadata check returned claude.ai:oauth:firstParty with the same Claude Code 2.1.287 executable hash. The refused receipt did not retain the differing raw auth object. Six subsequent metadata checks, alternating ordinary and pilot-filtered environments, consistently returned first-party OAuth. The underlying reason for the metadata transition remains unknown. No API-key fallback was observed, and the strict auth guard was not changed.

Known first-call usage was 5,593 tokens including cache. The ledger retained unknown usage for the pre-inference refusal and marked accounting incomplete. Qwen was not called. No position, export or arbitration was completed. No retry occurred.

## Panel v5

Approved manifest: 4457404991b376bd5f4563ec4ae35825017bdeb5f3594dc03a1849a09fac3cf5.

The new candidate retained the same evidence and limits and bound fresh first-party OAuth metadata. Shared Comet inspection confirmed Max (5x), available Fable allowance and Usage credits off. Browser and CLI account equality was not independently compared. The billing display is point-in-time evidence and must be refreshed for future execution.

All four Claude inference responses passed transport, stream, model, auth and usage validation. Auth remained claude.ai:oauth:firstParty. The reviewer used its calls as follows:

1. Request the evidence index.
2. Request three governing documents.
3. Request seven additional evidence files.
4. Request the remaining seven evidence files.

The runner stopped at max_steps after four calls because no task_complete report had been submitted. The final seven tool results had no subsequent inference turn for consumption or synthesis. All 17 sources were requested and returned, but this does not establish a completed review. Qwen was not called; no completed position, objection exchange, AIDR export or arbitration exists.

Reported usage: 8 input, 3,826 output, 92,338 cache-creation input and 7,272 cache-read input tokens, totaling 103,444. No Haiku usage was reported. Accounting is complete; subscription dollar charge remains unknown. All four request-metrics records were admitted. Ledger integrity passed for 18 records and runner-chain integrity passed for 29 events. No retry occurred.

## Next work

The offline workload rehearsal prescribed three reading turns and a fourth completion turn. It proved that scripted schedule fits, but not that a live reviewer would follow it. Keep auth and resource limits unchanged. Make the four-call reading-and-reporting schedule explicit to reviewers, including batched reads and reservation of the final call for task_complete, then test the revised instructions offline. A further live attempt requires a new sealed packet and explicit approval. Prompt changes have not been implemented by this record.

Private evidence remains under runs/pilot-candidate-2026-10-03/ and runs/pilot-candidate-v5-2026-10-03/. Each contains the proposal, approval and retained outcome. These consumed runs remain immutable and are excluded from Git delivery.
