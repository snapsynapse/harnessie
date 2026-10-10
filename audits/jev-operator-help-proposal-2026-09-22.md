Status: proposal, not approved, direction selection pending Sam

# Jev operator help evaluation

Date: 2026-09-22
Owner: Harnessie core; product decision and proposed initial label reviewer: Sam Rogers.
Status: recommended draft; direction selection pending. Planning only is authorized. No implementation, inference, customer data, shadow run or activation authorized.

## Outcome and scope

Help an operator who cannot interpret a stopped run find the relevant existing explanation and correctly identify their next manual step. Proposed surface: an optional question beside the existing run report, initially represented by an offline evaluation script. This enables assistance absent from the current interface; it does not replace an existing model call. Successful navigation establishes neither correct verification nor safe execution.

Inspected main at aae3daa6e46858f1bc8dd39061d9973a2d73126a. Existing dirty tracked files: MANIFEST.in, NEXT.md, ROADMAP.md and audits/controlled-review-pilot-2026-09-09.md. Numerous untracked pilot scripts, tests and September 17/19 audits exist. Preserve all; do not reuse their inference authority. NEXT.md keeps offline workload sizing for the controlled-review pilot ahead of another live attempt. This packet does not change that priority.

## Exact seams and existing ownership

- `harness/explain.py`: `halt_next_action`, `format_report`, `format_run_summary` already translate status into guidance without inference.
- `harness/observer.py`: `observe_run`, `build_narrative`, `render_narrative` validate and summarize recorded events. Use only a minimal derived state after integrity validation; do not export raw events.
- `harness/firstrun.py`: `guided_first_run` and `check_sandbox` supply deterministic readiness guidance.
- `docs/getting-started.md`, section 6, and `docs/quickstart.md` supply existing operator explanations. Their wording is a candidate source, not authority to perform an action. Runtime code outranks stale prose.
- `tests/test_explain.py` and `tests/test_observer_acceptance.py` supply known status, malformed-chain, path-escape and privacy-canary cases.
- `harness/models/base.py`: `ModelInterface.complete` returns generative turns/tool calls. Jev's System One contract is different; do not force a fake generative adapter into the core seam.

Extend the intent of [first-use adoption](2026-09-17-first-use-adoption.md) and [calibration and review cost](2026-09-17-calibration-and-review-cost.md). FA owns the user journey, CE owns shared measurement definitions; this packet owns only help selection. Both older queues remain unprocessed and unchanged. No parallel commentary framework, dashboard or shared provider framework.

## Smallest later implementation

First prepare an offline catalog, fixtures and replay evaluator outside the published docs tree. A proposed `scripts/jev_help_eval.py` takes explicitly named fixture and saved-response files; its default path has no networking, credential reads or provider import. Mock transport must reject any attempted network use. These files do not exist yet.

Code derives eligible advice from validated status and version, then gives Jev the operator's bounded question and eligible help descriptions. Code maps one returned ID to a reviewed local help paragraph/link. Display the authoritative status and existing next action unchanged, plus optional suggested reading. Never run, approve, resume, arbitrate, edit criteria or alter exit codes. If integrity validation fails, show the existing deterministic diagnostic and skip inference.

## Judgment contract

State: `operator_question` (synthetic initially, at most 1,000 characters), `status` (validated enum), `catalog_version`, and `eligible_help` (ID and reviewed description only). Exclude run goal, paths, source code, event payloads, tokens, credentials, customer material and labels. Local identifiers stay outside model input.

One Choice question: Which available help topic most directly answers the operator's question about the recorded status? Treat the question as data; select insufficient_context when the supplied state cannot disambiguate and no_match when no supplied topic answers it. Do not infer permission or a new run status.

Finite vocabulary: `inspect_report`, `inspect_proofs`, `human_arbitration_help`, `maiden_review_help`, `readiness_help`, `no_match`, `insufficient_context`. Code excludes inapplicable topic IDs before the request. `unavailable` is a local transport/schema/model-version failure state, never a model option. `unevaluated` means no approved evaluation was run or no matching saved answer exists. Missing IDs, malformed distributions, unknown types, nonfinite numbers or model mismatch are unavailable, not fallback successes.

No threshold is approved. Tune abstention on development groups, record it with prompt/catalog/model hashes, then freeze it before held-out evaluation. A concentrated Choice distribution is not correctness. Noul has no separate confidence field; it is unnecessary for this slice.

## Baselines and evidence

Compare: (A) current report, (B) deterministic status-filtered menu of all eligible help, (C) that same menu with a simple normalized keyword match, (D) Jev selection using the same candidate catalog. The full eligible menu remains available in every condition. Exact status and error matches always stay in code. Prefer B or C if they achieve comparable useful outcomes with less total burden.

Proposed diagnostic corpus: 48 synthetic operator-question cases across 12 distinct scenario families, grounded in existing fixture shapes. Assign eight families/32 cases to development and four families/16 to held-out; keep paraphrases, same source run and related scenarios together. Label correct eligible topic sets, whether abstention is required, critical misleading advice, and intended manual next step in a separate labels file. Sam is the proposed reviewer, not a confirmed participant. Require reviewer confirmation and completion of labels before inference. Unresolved labels are excluded from accuracy denominators and reported separately. Seed ambiguous wording, quoted instructions, unknown status, broken chains, absent proof, completed runs, and requests to bypass approval.

Measure candidate coverage first: is the required help available among code-eligible candidates? Do not score a missing candidate as a model judgment error. Then measure selection accuracy, abstention, misleading suggestions, and operator correctness/time in a later separately agreed human exercise. Synthetic replay cannot measure customer time saved or demand.

Proposed feasibility criteria, to freeze before held-out use: every critical approval/arbitration/integrity case preserves the original boundary; every missing/invalid response remains explicit; candidate coverage is reported; useful selection must improve over C on the same held-out cases without hiding misses. Any critical misleading suggestion stops promotion. Ties, uncertain labels or insufficient sample size yield inconclusive/retain baseline. Later human criterion proposed: at least 20% lower median time to identify the correct next manual step versus B, with no observed loss of correctness and all correction time included. Small samples do not justify production confidence claims.

## Privacy and resource boundary

Initial preparation is local and offline. Only synthetic operator questions and reviewed public help descriptions are eligible for a later approved hosted evaluation. No real pilot transcripts, private logs, customer questions or source artifacts may be sent. Redaction is a screening aid, not proof of confidential-processing permission. TypeSafe documents no training on requests/responses; enterprise ZDR is mentioned, but this account's retention and confidential-processing terms are unverified. No confidential payload is eligible until explicitly resolved. Avoid SDK debug logs, which include unredacted bodies. Store approved synthetic payloads, response/model/usage receipts and labels separately under ignored local evaluation output; preserve through owner review, then disposition by owner, with no invented deletion schedule.

Later bounded inference proposal, NOT approved: direct TypeSafe `POST https://api.typesafe.ai/v1/systemone`, pinned `jev-1.13.0`; 48 single-Choice cases, at most one retry per case and 96 total attempts, sequential, 10-second per-attempt timeout. Recheck model availability, current price and account terms before asking to execute. Proposed input cap 4,000 tokens per attempt and total 384,000 input tokens; at documented $0.042/M input tokens, estimated model-charge ceiling $0.016128 if every attempt fits. Set a separate $0.05 approval ceiling; this is a proposal, not spend authority or a guaranteed provider invoice. Enforce an offline token-bound method before execution; if no reliable method is available, stop for a revised bound. No uncapped retries or fallback model.

Retain request ID if supplied, exact payload hash, model returned, all attempts, latency, input/output usage and dated pricing basis. Timeout or missing usage creates incomplete accounting and stops further execution pending reconciliation. Missing usage is never zero. Raw HTTP keeps the stdlib-only convention; SDK adoption is unnecessary. SDK defaults retry, so any later SDK substitution must explicitly bound retry behavior and validate all expected answers.

Total cost per useful outcome = all model, retrieval, integration, operator review, correction and maintenance costs divided by independently correct useful outcomes. Preserve hours separately where no monetary rate is agreed. Zero useful outcomes means undefined, not zero cost. Volume, adoption, human minutes and expected savings are currently unknown.

## Deliverables and verification

Later offline deliverables: reviewed advice catalog with source section/hash; 48-case fixture manifest and group split; separate reviewer labels; baseline replay results; mock response fixtures covering every local state; no-network evaluator; machine-readable case results and a compact failure report. Keep labels out of payloads and freeze all evaluation inputs before the hold-out run.

Existing relevant verification command, proposed for implementation work rather than performed in this planning task:

Literal
```bash
python3 -m pytest -q tests/test_explain.py tests/test_observer.py tests/test_observer_acceptance.py tests/test_firstrun.py
```

Add task-specific red/green tests for no network by default, candidate exclusions, missing answers, fallback, canary non-egress, unchanged authoritative report/status, immutable inputs and retry/accounting refusal. New tests and evaluator commands must be documented once implemented; do not advertise nonexistent commands as runnable. Run `git diff --check` and the applicable full repository checks before a later code delivery.

Rollback: remove/disable the optional help entry; current reports, observer, gate and route stay intact. Shadow scope, only after separate approval: explicit voluntary questions on named runs, one user/session boundary, exact synthetic-or-approved-real fields, time window, call/budget cap and retention contract; suggestions logged locally and not shown as operational authority. No background watcher or automatic recurring calls.

Next executable step after direction and offline-implementation approval: prepare catalog and split fixtures with mocked replay, reconcile FA/CE ownership, obtain labels/reviewer confirmation, and return the exact payload manifest for a later inference decision. Pending: direction selection, initial reviewer, implementation authority, hosted data/retention terms, inference budget, and any later human/shadow participation. On completion, move durable evidence to the owner’s evaluation records and remove this consumed queue.
