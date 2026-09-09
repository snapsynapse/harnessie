# Controlled-review live pilot packet

Status: approved by Sam on 2026-09-09 as the next active Harnessie tranche. Operational readiness is AMBER pending frozen inputs, exact participant identities, provider reachability, egress permission and a spend ceiling. No live model call is authorized by this packet alone.

## Purpose

Exercise the shipped contested-review, mandatory-human halt and open-record AIDR export path against one real decision. Preserve disagreement and exposure evidence without treating configured provider names as authenticated identity or allowing models to arbitrate.

Proposed pilot question:

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

## Inputs still required

- Confirmation of the exact pilot question.
- Two exact model/provider instances and reachable configuration.
- Explicit external-egress scope and maximum spend.
- A disposable project root containing the reviewed frozen evidence packet.

The current canonical configuration names Anthropic `claude-fable-5` and local OpenAI-compatible `qwen3.6:35b-mlx`, but this assessment did not establish Anthropic credentials or local endpoint/model reachability. Do not substitute a provider silently.
