---
title: "AI Decision Records (AIDR) Specification"
version: "0.1.0"
status: ratified
last_updated: 2026-07-02
description: "A single-file markdown format for recording decisions involving AI agents: independent positions, preserved dissent, and human arbitration."
tags: [aidr, specification, governance, decision-records, agents]
---
# AI Decision Records (AIDR) Specification

Version 0.1.0 (ratified 2026-07-02). The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as described in RFC 2119.

## 1. Purpose

An AI Decision Record (AIDR) captures one consequential decision made with the participation of AI agents. It records the question, each participant's independent position, objections, and the human arbitration that resolved them, in one plain markdown file that survives tool changes.

AIDR answers two questions that execution logs and chat transcripts answer poorly: who objected before we acted, and who had the authority to resolve the disagreement.

## 2. Design rules

1. One decision, one file. An AIDR is not a session log, task tracker, or transcript.
2. Plain markdown plus YAML frontmatter. Readable and writable without tooling.
3. Positions are first-class. A dissenting position is not an error state.
4. Dissent is never deleted. Records are superseded, not rewritten.
5. Arbitration is human. An agent MUST NOT author the Arbitration section.
6. Vendor-neutral. No field requires any particular model, provider, or runtime.

## 3. File conventions

- Records live in a `decisions/` directory at the repository or project root. Other locations MAY be used; a repository SHOULD use one location consistently.
- Filename: `AIDR-NNNN-short-slug.md` where NNNN is a zero-padded sequence number unique within the directory.
- Encoding is UTF-8. The file MUST begin with YAML frontmatter delimited by `---` lines.

## 4. Frontmatter fields

Required:
- `id`: the record identifier, e.g. `AIDR-0007`. MUST match the filename prefix.
- `title`: short noun phrase naming the decision.
- `status`: one of `open`, `arbitrated`, `superseded`. See section 6.
- `date`: ISO 8601 date the record was opened.
- `arbiter`: the human (name or stable handle) holding decision authority for this record. MUST identify a human, not an agent.

Optional:
- `decided`: ISO 8601 date of arbitration. Required when `status` is `arbitrated` or `superseded`.
- `supersedes`: id of an earlier record this one replaces.
- `superseded_by`: id of the later record that replaces this one. Required when `status` is `superseded`.
- `tags`: list of free-form labels.

## 5. Body sections

Sections appear in this order. Headings are level-2 (`##`) with these exact names.

### 5.1 Context (required)

Why this decision exists and what is at stake. SHOULD be under 200 words. Links to supporting material belong in Evidence, not here.

### 5.2 Question (required)

A single decidable question, stated so that a reader can tell whether any given position answers it. One sentence SHOULD suffice. If the question changes materially, open a new record.

### 5.3 Positions (required)

One level-3 subsection per participant, heading `### Position: <participant-label>`. Each position MUST include a metadata list:

- `agent`: participant label, unique within the record.
- `model`: model identifier as reported by the participant, or `human` for a human participant.
- `provider`: model vendor or `human`.
- `stance`: one of `recommend`, `oppose`, `alternative`, `abstain`.
- `summary`: one-sentence statement of the position.

Prose follows the metadata list. Requirements:

- A record MUST contain at least one position.
- Each position MUST be authored by the named participant, without seeing other positions first where practical. If a position was formed after reading others, it MUST say so in its prose.
- A record claiming independent multi-model review (see section 7) MUST contain at least two positions whose `provider` values differ.

### 5.4 Objections (optional section, required content when dissent exists)

One level-3 subsection per objection, heading `### Objection: <participant-label> to <position or decision reference>`. An objection MUST name a concrete failure mode, contradiction, or risk. Generic preference is a stance in Positions, not an objection.

If any participant disagreed with any position and that disagreement is not already captured as an `oppose` or `alternative` position, it MUST be recorded here. Objections are never removed once recorded.

### 5.5 Arbitration (required when status is arbitrated or superseded)

Authored by the human named in `arbiter`. MUST include a metadata list:

- `decided_by`: the arbiter's name or handle.
- `date`: ISO 8601 date of the decision.
- `decision`: one-sentence statement of what was decided.

Prose follows, and MUST address every objection recorded above it: accepted, rejected with reason, or deferred with a named follow-up. Agreement among agents MAY inform the decision but does not substitute for it.

### 5.6 Evidence (optional)

Links to supporting material: diffs, benchmarks, prior art, related records, runtime traces. Each entry SHOULD say what the link is evidence of.

## 6. Status lifecycle

- `open`: positions are being gathered. The Arbitration section is absent or empty.
- `arbitrated`: the arbiter has decided. The record is now append-only except for `superseded_by`.
- `superseded`: a later record replaced this one. The original text is preserved unmodified; only `status` and `superseded_by` change.

There is no rejected status. A decision not to act is still an arbitrated decision.

## 7. Conformance

A file is a conforming AIDR when it satisfies every MUST in sections 3 through 6.

A conforming record additionally qualifies for the following named claims:

- `independent-positions`: at least two positions with distinct `provider` values, each recorded before arbitration.
- `dissent-preserved`: at least one `oppose` or `alternative` position or one objection exists, and the Arbitration prose addresses it.
- `human-arbitrated`: `status` is `arbitrated` and the Arbitration section satisfies section 5.5.

Claims are verifiable by any party from the file alone. The reference linter is `tools/aidr-lint.mjs`; conformance is defined by this specification, not by the tool.

## 8. What AIDR is not

- Not a session protocol. Multi-agent session lifecycle, mailboxes, and turn coordination are out of scope. For a full session governance protocol, see Turnfile (https://turnfile.work/), of which AIDR is the minimal single-artifact expression.
- Not an execution format. AIDR records positions and decisions, not tasks or commands.
- Not a consensus claim. Agreement among models is recorded evidence, never authority.

## 9. Relationship to prior art

AIDR extends the Architecture Decision Record tradition (Nygard ADRs, MADR) to decisions where AI agents hold positions. Agent Decision Records (AgDR, me2resh/agent-decision-record) documents decisions an AI coding agent makes during development; AIDR is complementary and addresses the case AgDR does not: multiple independent agent positions, first-class dissent, and required human arbitration. See PRIOR_ART.md.
