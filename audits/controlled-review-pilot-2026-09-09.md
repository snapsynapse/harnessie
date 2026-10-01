# Controlled-review live pilot packet

Status: approved by Sam on 2026-09-09 as the next active Harnessie tranche. Local preparation and synthetic transport checks are complete. The [2026-10-01 full-workload sizing](pilot-workload-sizing-2026-10-01.md) proves the declared evidence fits the byte envelope. The approved [Claude Haiku context policy](pilot-haiku-context-policy-2026-10-01.md) now encodes and rehearses the exact full-evidence per-call and run ceilings offline. The [Claude authentication-contract repair](pilot-claude-auth-contract-2026-10-01.md) recognizes the current first-party OAuth status without treating it as Max billing proof; fresh included-allowance and credits-off evidence remain mandatory. Live readiness remains AMBER pending fresh billing evidence, final disclosure review and one sealed execution approval. No live model call is authorized by this packet alone.

## Purpose

Exercise the shipped contested-review, mandatory-human halt and open-record AIDR export path against one real decision. Preserve disagreement and exposure evidence without treating configured provider names as authenticated identity or allowing models to arbitrate.

Confirmed pilot question:

> Should Harnessie proceed with a bounded bid-record contract after its named exposure and budget gates, while leaving dispatch selection unchanged?

## Frozen packet

Use a disposable dedicated project root containing only the pilot material. Do not run reviewers against this repository's existing ignored `workspace/`, which can contain unrelated historical briefs.

Freeze and hash before the first model call:

- the exact question and evidence index;
- AIDR-0009, its design draft and preparation audit;
- the four recorded readiness reviews;
- `tests/test_bidding.py` and `evals/pending/bidding.yaml`;
- relevant routing, budget, containment and design-invariant sources;
- the pilot workflow, models configuration and role prompts;
- the Harnessie Git revision.

Record the same hashes after the panel. Any unexplained drift invalidates the pilot.

## Runtime contract

- Derive a dedicated two-panel workflow from the shipped example without modifying that example.
- Set `arbitration: human`, `arbiter: Sam Rogers` and one bounded rebuttal round.
- Use two explicitly named model/provider instances. Distinct configured providers are useful diversity evidence but are not authenticated identity or blind-review proof.
- Require explicit approval for the named external egress and a declared pilot spend ceiling before dispatch.
- Preserve stage labels, participant-instance mapping, evidence citations, objections and the event-chain head.
- Expect the panel command to halt at `needs_arbitration`; model agreement does not bypass the human gate.

## Acceptance evidence

1. Preflight cost preview and explicit provider, egress and budget approval.
2. Frozen-packet manifest with matching pre-run and post-run SHA-256 values.
3. Exact participant model, provider, endpoint class and effort metadata.
4. A `needs_arbitration` result with stage-preserved positions and objections.
5. A passing `harnessie audit` result and recorded chain head.
6. Reviewer evidence citations plus an exposure note distinguishing access from proof of reading.
7. Successful export of the still-open run decision through the 1.4.1 exporter and passing pinned AIDR 0.1.0 lint.
8. Sam-authored arbitration in the exported canonical AIDR.

Export must occur before arbitration because the 1.4.1 exporter refuses an arbitrated source record. Arbitration in the exported AIDR does not flow back into the original run. The source run remains halted unless Sam separately arbitrates its source decision record; that limitation is pilot evidence for later runner and AIDR integration work.

## Inputs and authority still required

- Completed offline: `claude-max-haiku-context/v2` encodes 96,000 Haiku cache-inclusive input tokens and 256 output tokens per invocation, 256,000 Haiku input and 2,048 output tokens per run, 800,000 all-model reported tokens per run, eight Claude calls and zero retries. The full-evidence rehearsal admitted all 16 requests and made zero live calls. The execution proposal still carries zero live allowance.
- Actual participant serving-identity and usage evidence. Intended instances are Claude `claude-fable-5-1` through the unmodified Claude Code Max CLI and local Ollama `qwen3.8:latest`; configuration and account metadata are not inference proof.
- Explicit final external-egress scope, per-participant/stage invocation and retry ceilings, timeouts and output limits. Subscription dollar cost remains unknown, not zero.
- Human acceptance of the exact final disposable packet and its externally retained seal. The prepared rehearsal has zero live allowance and is not final live authorization.

The canonical configuration still names Anthropic `claude-fable-5` and local OpenAI-compatible `qwen3.6:35b-mlx`. The preparation deliberately uses separate pilot configuration; it does not change global defaults, the public provider registry or stable schemas. September 17 read-only checks found the existing Max login and local Qwen metadata available. Silent model or billing-route substitution remains forbidden.
