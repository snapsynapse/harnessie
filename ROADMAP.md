# Harnessie roadmap

This is the forward view: versioned milestones, their themes, and platform support. It answers "what comes next and in what order". For the numbered build steps and their pass/fail done-tests, see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md); for the security properties every sandbox backend must satisfy, see [SECURITY.md](SECURITY.md).

Roadmap items are intent, not commitments. Dates are omitted deliberately; milestones ship when their acceptance criteria are green, not on a calendar.

## Released so far

Versions 0.1.0 through 1.1.0 are shipped; the current core release is 1.1.0. It retains the stable 1.x authoring and plugin contracts while making Harnessie's ownership invariant inspectable through a read-only CLI decision surface and executable collision proof. This file is the forward view only: what each release's theme and acceptance bar were, and what comes next. The authoritative record of what actually landed in each version lives in [CHANGELOG.md](CHANGELOG.md), not here.

## Guiding priorities

- Correctness and safety land before features; no milestone opens while a prior acceptance criterion is red.
- Brain-agnosticism must be a testable claim, not a slogan: configuration proves swappability, while a public “proven” label requires a scorecard bundle or runtime decision record.
- Portability never weakens a guarantee: an unsupported platform fails closed rather than running a control unenforced.
- Lean and solo-operable: complexity is added only when a real threshold is crossed.

## Milestones

### 0.3.x: Aggregated-intelligence tenets, agent triage, refusal hardening - SHIPPED

Acceptance met: triage runs headless as propose-only and applies only under recorded approval; a stale fact is surfaced by date, archived never deleted; the audit timeline shows agent and operator actions interleaved; refusals carry `{error, boundary, detail, why}` and are audit-rendered.

### 0.4.0: Portability and proof - SHIPPED

Theme: make the harness runnable and measurable beyond a single Mac.

- Linux sandbox backend, so shell-using workflows run confined on Linux instead of failing closed (detail in Platform support below). Implementation step 15 follow-up. GREEN: bwrap/firejail/docker backends with startup smoke tests and a CI matrix (Linux bubblewrap parity, macOS, no-backend fail-closed).
- Live-endpoint smoke tests: implemented as opt-in code and pytest infrastructure (`tests/live/`, `harness/live_scorecard.py`). A keyless/no-endpoint environment emits visible skips; real calls require `HARNESSIE_LIVE=1` plus provider configuration. Implementation step 11.
- Golden-task evaluation scorecard beyond the mock-brain baseline: implemented as `python3 -m harness.cli eval --live`, with direct, verifier, tool-loop, consent-loop, and consent-lock rows per configured provider, including token and cost display where usage is reported. Implementation steps 11 and 12.
- Trust-bundle manifest integrity: `docs/MANIFEST.yaml` pins the hash of public machine-readable trust/discovery files; `python3 -m harness.cli verify-manifest` and `tests/test_trust_manifest.py` verify it.
- Live contested-phase run: ready for an operator-attended run through `workflows/contested-decision.yaml` across two real providers. This remains a live-provider operation and is not part of the default no-network suite.

Acceptance: the full suite is green on Linux with a backend present and fails closed on a runner with none; a brain swap (config edit) produces a comparable scorecard.

### 0.5.0: Operability - SHIPPED

Theme: put a human comfortably in the loop for long autonomous runs.

- Interactive approval handler wired to a TTY prompt and a headless allow/deny policy file; per-phase cost display. Implementation step 13. GREEN.
- Parallel workers: independent phases fan out with per-phase workspaces to prevent write conflicts. Implementation step 14. GREEN.

Acceptance: a requires_approval tool blocks headless by default and proceeds only under policy; two independent phases run concurrently, gate independently, and beat sequential wall-clock.

### 0.6.0: First-harness readiness (public launch gate) - SHIPPED

Theme: make "the safest and easiest first AI harness for people" true for someone who has never identified as a developer, and make the safety claim falsifiable for the developers who will audit it. This milestone gated the public launch; it does not displace 0.4 portability or 0.5 operability, both of which it depends on. Released 2026-07-07; the repo and canonical page are public. The then-current guide earned GuideCheck Level 4 end to end, and the Siteline live-page bar was green. Each changed guide must independently re-earn that status.

Ease (the first-run path):
- PyPI packaging: `pip install harnessie` (or `pipx install harnessie`) replaces clone-and-editable-install as the documented entry; signed, tagged releases use `RELEASE_CHECKLIST.md` per the repo-standards promotion path. GREEN: Harnessie 0.6.0 shipped on PyPI and as a tagged GitHub release; subsequent 0.7.0, 0.7.1, and 0.8.0 releases use the same ceremony. A fresh install from the live index reaches the guided init's green zero-dollar run, with source installation kept for development.
- Guided first run: `harnessie init` grows an interactive setup that checks Python version, detects a sandbox backend, walks API-key setup via environment variable (never a file), and ends with a green mock-brain run so the first experience costs zero dollars. GREEN (`harness/firstrun.py`).
- Plain-language operator surface: `harnessie report` and every halt message readable by a non-developer; each stop condition explains itself in one sentence and names the single next action (the README halt table becomes the in-tool text, not just docs). GREEN (`harness/explain.py`).
- Pre-run cost preview: before a live run, show the configured ceilings and a worst-case dollar estimate; refuse to start when no ceiling is set. GREEN (`harness/preflight.py`).
- A non-developer quickstart in `docs/` (the served tree once public): one real, useful, low-risk workflow end to end, with a glossary that never assumes git or shell fluency. GREEN ([docs/quickstart.md](docs/quickstart.md)).
- Windows path documented honestly: WSL2 walkthrough, plus a clear statement of what fails closed on bare Windows and why that is protection, not breakage. GREEN (in the quickstart's "Running on Windows" section).

Standards adoption (the credited specs become checkable claims):
- GuideCheck: rewrite the shipped `assistant-guide.txt` from the current minimal unstructured guide to a conformable Level 3+ profile; add the byte-identical `.well-known/assistant-guide.txt` plus manifest sidecar (the trust-anchored pair) and verify the hash match; link it from the landing page footer and README so it is discoverable, not just present. The `.well-known/` half is only verifiable end-to-end once Pages is live; the content rewrite and manifest need not wait. GREEN: `assistant-guide.txt` is a conforming GuideCheck Level 3 profile (bounded review task; verified by the reference verifier at Level 3, zero findings), with a byte-identical `docs/.well-known/assistant-guide.txt`, a sidecar provenance manifest, `docs/.nojekyll` so Pages serves the dot-directory, discovery from the landing page, README, `llms.txt`, and `pyproject` `[project.urls]`, and all three files pinned in the trust manifest. Level 4 CONFIRMED end-to-end 2026-07-07 by the hosted fetching verifier (guidecheck-hosted 0.7.0: achieved level 4, zero blocking findings) against the live `.well-known/` pair, the sidecar manifest, and an independent DNS TXT anchor at `_assistant-guide.harnessie.com` (registrar control plane, resolved via DoH). The two remaining warnings are response headers GitHub Pages cannot set (nosniff, HSTS).
- Graceful Boundaries: check the shipped v0.3.2 refusal grammar against GB's conformance criteria across all 16 enumerated denial sites; cite the achieved level (or a named gap list) in `SECURITY.md` or `GOVERNANCE.md`; update `INTENT.md` §7 from lesson-import to the real adopted status. GREEN: adopted transport-adapted (Level 1 grammar met, Action Boundaries vocabulary aligned, SC-16 met; HTTP Levels 2-4 N/A). Cited in [GOVERNANCE.md](GOVERNANCE.md) §8; `INTENT.md` §7 moved to adopted.
- Siteline: GREEN. A fresh live rubric 2.3.0 scan on 2026-08-05 UTC scored the deployed canonical site A, 97/100, with Level 4 machine enablement at 16/18. The captured external response provenance and the result-store residual are recorded in [the release-gate audit](audits/siteline-live-result-2026-08-05.json).

Safety (the falsifiable claim):
- A published threat-model comparison artifact: SECURITY.md properties mapped against the failure modes of prevailing harness patterns (unsandboxed shell, prompt-level-only guardrails, self-verification, silent dissent-merging), each row citing the enforcing code and its test. This is the artifact the "safest" headline points at. GREEN ([docs/threat-model.md](docs/threat-model.md); every row cites a passing test).
- A standing "break it" invitation: a `SECURITY.md` disclosure path plus eval scenarios published as red-team targets, so the claim is contestable in public rather than asserted. GREEN (`SECURITY.md` disclosure path + `evals/redteam.yaml`).
- Default-deny posture audit before launch: one pass proving every tool grant, network allowance, and approval gate defaults closed in the shipped configs (extends `tests/test_repo_configs.py`). GREEN.

Acceptance: a non-developer given only the quickstart reaches a green first run without touching a config file; the comparison artifact exists with every row citing code and test; a fresh install on a ceiling-less config refuses a live run; the GuideCheck pair verifies, the Graceful Boundaries status (level or gap list) is cited in a tracked doc, and the live page passes the Siteline bar.

### 0.7.0: Sovereignty cascade routing and the containment boundary - SHIPPED

Theme: route every task to the least-exposed environment that can complete it, and make containment a mechanical property of the run rather than an operator habit. Extends the existing gate ladder (reformulate, then effort up, then tier up) into declared, containment-aware routing policy. Opens only after the 0.6 launch gate closes, and only after the design passes a contested-decision run recorded as an AIDR: the harness's own governance decides its routing layer. Redrafted 2026-07-07 after `decisions/AIDR-0003` arbitrated "do not adopt as first specified": the containment claim is now a per-data-class coverage table rather than a blanket statement, contained routing explicitly owns the unstructured residual the filter cannot catch, the strip-map lifecycle across resume is designed rather than deferred, and placeholder impact on gate pass rates becomes a published per-brain number.

Prerequisite (carried from 0.6 known limits): GREEN. `Budget.child()` gives parallel phases headroom-scoped budgets with live charge-through to the run budget, and escalation headroom builds on that enforcement.

Routing (policy over the existing ladder):

- Cascade policies as config (`config/cascade.yaml`): a workflow phase may reference a named policy instead of a fixed `task_class` tier. A policy declares a tier ladder, the escalation reasons that climb it (gate fail, schema fail, refusal, tool-contract break), a maximum climb, and an on-exhaust action (reduce scope or defer, never silent). Phases that do not opt in behave exactly as today.
- Containment-constrained ladders: a policy names the data classes it may carry, and a contained ladder never escalates past its allowed tier set. Redaction (below) can transform a task's data class and therefore its allowed ladder.
- Sideways fallback, distinct from upward escalation: availability failures (rate limit, overload, provider error) and guardrail refusals move across providers at the same tier; they never auto-escalate a contained task upward, because up-tiering on refusal is a containment leak. Both motions are recorded with their reasons.
- A `sovereign` tier slot between `local` and `frontier` in `config/models.yaml`: any OpenAI-compatible controlled endpoint, including TEE-hosted inference, with the same swap-by-config contract as every other tier.
- A reserved pre-gate: work classes named `reserved:` in policy never reach any model at any tier and halt with a named operator action (the existing human-only Arbitration rule, generalized and enforced as config).
- Escalation headroom: a climb is refused when the remaining run budget cannot cover it, extending the 0.6 budget-safety hardening; an escalation can never be the thing that busts the ceiling.
- `routing_trace` in decision records and events: per attempt, the tier, model, outcome, and reason. Aggregated across runs this becomes the capability evidence behind [docs/brains.md](docs/brains.md), and it makes frontier overuse a queryable number: escalations to frontier without a recorded lower-rung failure should be zero by construction.

Containment boundary (the mechanical half of the sovereignty claim, scoped to what a deterministic filter can honestly claim):

- A deterministic strip/rehydrate boundary at the provider adapter (`harness/boundary.py`), adapted with provenance from PAICE.work PBC's production PII service: structured PII (multilingual pattern set) is replaced with stable placeholders before any egress; models never see values; every run artifact (workspace, phase reports, events, decision records) carries placeholders only; rehydration happens solely at the operator boundary. The filter is regex over text, no model in the filter path, so it cannot be prompt-injected into leaking.
- A published coverage table, not a blanket claim: the boundary's guarantee is stated per data class with its enforcing mechanism and its test — structured PII (boundary, caught), secrets (boundary, caught, halt-not-warn), unstructured free-text PII (NOT caught by the boundary; covered by contained routing, next bullet). The claim the release makes is exactly the table, in the same falsifiable-row style as [docs/threat-model.md](docs/threat-model.md). A deterministic filter that claimed totality would be false assurance; a scoped one with a named residual and a named covering mechanism is a boundary.
- Contained routing covers the boundary's residual: a task carrying data the filter cannot classify (free-text sensitive content) declares that data class, and its containment-constrained ladder never leaves the local/sovereign tier set — unstructured PII is not filtered on egress, it never egresses to an exposed tier at all. The two halves cover each other's blind spot by construction: the boundary handles what patterns catch, routing handles what they cannot, and the coverage table names which mechanism owns which class.
- Placeholder-map lifecycle (designed, not deferred): the strip map (placeholder -> value) is an operator-boundary artifact stored outside every run artifact — never in the workspace, phase reports, events, or decision records, which carry placeholders only. Secrets never enter the map at all (their placeholders reference environment-variable names, resolved only at the tool-execution boundary, so there is no secret value to persist). On resume the map is reloaded before any rehydration; a missing or corrupt map fails closed — placeholders stay placeholders, the report names the degradation, and the harness never guess-rehydrates.
- A secrets class with stricter lifecycle than PII: known-prefix and entropy detection (gitleaks-style rulesets, adopted not invented), placeholders that reference environment-variable names and are resolved only at the tool-execution boundary (the boundary never stores secret values), and a hard rule that a secret is never rehydrated into any text, record, or report. A detected secret in an egress payload always halts; there is no warn mode.
- Tool-output scrubbing: tool results are scrubbed before they enter context, closing the loop where a worker reads an env var or config file and the value would otherwise ride the next model call out.
- Per-tool rehydration grants using the shipped approval-policy grammar (allow/deny by tool and phase, explicit deny wins, no match denies closed), starting deny-all.

Proof (the claim is eval-shaped, per the eval-first discipline):

- Canary leak evals: seeded fake PII and secrets in eval inputs, asserting zero appearance in egress payloads, records, and reports. Coverage-table honesty is part of the eval: structured canaries must be caught by the boundary; unstructured canaries must be shown routed under a contained ladder (never egressing an exposed tier), not claimed as filtered.
- Placeholder-impact scorecard: the gate pass-rate delta with the boundary on versus off, measured per proven brain and published alongside its scorecard in [docs/brains.md](docs/brains.md). Whether placeholder substitution depresses a small model's gate performance stops being an open question and becomes a queryable number per brain, the same way `routing_trace` makes frontier overuse queryable.
- Gate-integrity canaries: deterministic manipulation templates (phantom prior context, self-contradiction, autonomy grab) injected into phase inputs, asserting the gate or verifier catches them.
- Proven-brain claims tighten to bundle identity: a scorecard result pins model, provider, endpoint, prompt version, parser version, and sampling, and any component change requires a re-run — change control, not drift monitoring.

Acceptance: a phase under a contained policy completes a real task with zero canary PII or secret bytes in any egress payload or run artifact; the published coverage table names every data class with its owning mechanism, and unstructured-PII canaries are proven contained by routing rather than claimed filtered; a resumed run rehydrates identically to an uninterrupted one, and a missing or corrupt strip map halts rehydration closed rather than guessing; the placeholder-impact delta is a published number for every proven brain; `routing_trace` shows every escalation and fallback with its reason; an escalation without budget headroom is refused before dispatch; a workflow that does not opt into cascade routing produces byte-identical routing behavior to 0.6; the adopting AIDR is on record with human arbitration.

### 0.7.1: The verifier leaves the harness - SHIPPED

Theme: extract the VerificationGate as a standalone surface (`harnessie verify`) consumable by any orchestrator or CI as an exit-code check, first proving ground agent-produced pull requests. Adopted via `decisions/AIDR-0006`. GREEN: fail-closed exit contract (0/1/2) proven by `tests/test_verify_standalone.py`; field-proven same day against the Ringer PR queue including a refutation of its own author's PR.

### 0.8.0: Write-safety and self-integrity - SHIPPED

Theme: bound what a run may change, the way 0.7 bounds what a run may expose. 0.7's containment boundary limits data leaving the harness; this milestone limits damage inside it, and extends the same integrity discipline to the harness's own configuration. These mechanisms are independent of the routing engine and the containment boundary, which is why they ship as their own claim rather than riding the sovereignty milestone.

- Blast-radius ceilings, the artifact-volume sibling of the cost budget: GREEN. Phases and whole workflows may cap files touched, edits applied, and workspace bytes written. Registered writes, sandboxed shell calls, and deterministic checks execute as measured filesystem transactions; a cap hit restores the pre-operation workspace, emits the count and limit, and halts the phase without retry. Workflow-wide counters aggregate parallel phases under a lock and reconstruct from audit events on resume. Invalid declarations refuse before model dispatch, while workflows with no declaration retain their prior behavior.
- Declared-write-path conflict refusal for parallel groups: GREEN. Phases may declare exact files or directory subtrees up front; partial opt-in, ambiguous declarations, and portable case/Unicode aliases fail closed, while overlapping declarations refuse before workspace creation or model dispatch. Declared operator and agent ownership lanes remain enforced inside isolated phase workspaces. Static conflict detection is layered under the existing workspace isolation, and legacy groups that do not opt in retain their 0.7 behavior.
- Maiden-voyage rule: GREEN. A worker phase opts in with a stable `phase_type`; the exact normalized phase contract is fingerprinted, so any behavioral change creates another maiden voyage. An unapproved contract runs and gates in an ignored `.maiden/` staged clone, with network and non-workspace mutation disabled. The main workspace remains byte-identical until `harnessie approve-maiden <run_id> <phase>` verifies the audit chain, staged output, ownership ledger, and unchanged target before promotion. Approval is audited, resume skips the approved phase, and future runs of that exact contract write normally.
- Inward manifest: GREEN. `INWARD_MANIFEST.yaml` hash-pins every shipped role prompt, every YAML config, and the static policy portion of `OWNERSHIP.yaml`, with exact coverage so a newly added unpinned input also diverges. Auto-maintained first-writer claims are excluded from the ownership-policy hash so legitimate writes do not invalidate later runs. The default `refuse` policy halts before model dispatch; `record` emits the divergence and continues for intentional local development. Clean runs record the manifest identity and selected workflow hash. The outward manifest proves the public surface; this proves the declared inputs of the machine that produced the run.

Acceptance: a phase that exceeds a declared volume ceiling fails with the count and applies nothing further; a parallel group with overlapping declared write paths refuses before any phase starts; a first-run workflow stages artifacts without applying them until operator approval is recorded; a run under an edited role prompt is either recorded as divergent or refused, and the shipped-state run proves byte-identical prompts.

### 1.0.0: Extensibility, earned (shipped 2026-08-09)

Theme: stable surfaces and pluggability, only after the core is proven.

- Stable, versioned configuration and workflow schemas with a written compatibility and deprecation policy: SHIPPED. Six strict Draft 2020-12 schemas cover every user-authored models, cascade, boundary, approval-policy, ownership, and workflow surface. `harnessie validate` is side-effect-free, runtime startup uses the same validator, cross-document references fail closed, public schema bytes match the packaged contracts, and schema-less 0.8 documents remain implicit v1 throughout 1.x. `SCHEMA_COMPATIBILITY.md` defines compatibility and deprecation behavior.
- Per-lane sandbox profiles: SHIPPED. Operator lanes, other-agent lanes, and other agents' first-writer claims compile into conservative read-only roots for worker shell calls, deterministic checks, and verifier execution. Invalid patterns and backends that cannot prove nested enforcement fail closed; unowned paths retain first-writer semantics. Docker remains admitted for the base workspace sandbox only and refuses nonempty lane profiles until its configured image has a truthful nested-mount probe.
- Tool plugins: SHIPPED. Installed packages expose declarations through the single versioned `harnessie.tools.v1` entry-point group and never auto-load. Repeatable `--plugin NAME` admission validates and namespaces tools before model dispatch, applies registry roles, consent, approvals, effects metadata, and quarantine, records immutable provenance, and pins the exact receipt across resume. Imported implementation code is explicitly operator-trusted and not lane-confined; untrusted plugins remain unsupported pending a separate out-of-process protocol.

Gate result: GREEN. All earlier acceptance criteria, the three 1.0 slices, the composed release gate, exact package build, and fresh-install smoke passed before release.

### 1.1.0: The Golden Rule becomes inspectable (shipped 2026-08-20)

Theme: turn the ownership invariant into a memorable, falsifiable product surface without weakening the 1.x compatibility contract.

- Positioning: SHIPPED. "Harnessie's Golden Rule for agent work: Read together. Write only what you own" names the existing invariant while the technical term remains ownership lanes. The public explanation cites dispatch denial, child-process read-only overlays, pre-dispatch parallel conflict refusal, explicit collaborative and plugin boundaries, and the `request_change` remedy.
- Policy inspection: SHIPPED. `harnessie ownership PATH --agent AGENT [--json]` evaluates the exact decision used by enforcement without claiming or changing a path. Human output names the governing source, owner, matching pattern, reason, and remedy. Schema-versioned JSON provides a stable machine vocabulary. Valid allow and deny explanations exit 0; invalid input exits 2.
- Collision proof: SHIPPED. A zero-model, zero-network example writes an artifact as Alice, attempts to replace it as Bob through the built-in tool registry, and passes only when Bob receives `ownership_denied`, Alice's bytes survive, and the ledger still names Alice.
- Public and release surfaces: SHIPPED. README, website, Guide, agent declarations, CLI manifest, machine changelog, assistant guide, package metadata, release notes, generated pages, and fresh-install smoke describe and test the same 1.1.0 behavior.

Gate result: GREEN. The composed release gate, ownership adversarial corpus, exact package build, and fresh-install ownership inspection passed before release. The assistant guide's external DNS re-anchor and hosted re-verification follow publication because those checks require the final public bytes.

### Post-1.0 candidates

Deliberately after 1.0, not before:

- Official Docker image. The complication is that the sandbox story inverts inside a container: the docker sandbox backend needs a daemon the container does not have, so an image must either nest a backend (bwrap inside the container), document a reduced-confinement mode honestly, or treat the container boundary itself as the sandbox with the fail-closed rules re-derived for that topology. That is a security-docs problem as much as a packaging problem, which is why it waits for the stable 1.0 surfaces. Acceptance when it lands: the image's confinement posture is stated in SECURITY.md with the same fail-closed honesty as the bare-metal table, and the threat-model artifact gains a container row citing enforcing config and test.
- conda-forge feedstock, if data-science users ask; the review process is external and the PyPI package already serves `pip`/`pipx`/`uv`.
- Multi-orchestrator handoffs, only if a documented real job demonstrates that a single orchestrator cannot hold it. In the absence of that evidence this is not a 1.0 requirement.
- Truthful operating-mode controls. The current `--approve-interactive` handler covers only tools declared `requires_approval`; it is not an every-side-effect approval mode. A future such mode must mediate every write and execute tool structurally. Delegated external operators also remain outside Harnessie's human-vs-agent identity proof until the audit contract can authenticate those seats.

## Platform support

### Supported today

macOS is fully supported: the OS sandbox uses native `sandbox-exec` (Seatbelt), confining child-command writes to the workspace, overlaying denied ownership lanes read-only, and denying network by default. Linux backends (bubblewrap preferred, firejail alternate, docker fallback for the base workspace sandbox) are implemented as of the 0.4 line. Bubblewrap and firejail must pass a second nested read-only probe for nonempty lane profiles; Docker refuses those profiles until its configured image has an equivalent probe. CI proves the suite green under bubblewrap and proves fail-closed with every backend removed. On Windows, and on any host where no backend passes its required smoke test, shell-using workflows fail closed. This is the fail-closed-everywhere policy working as designed, not a bug: a control that cannot be enforced is refused rather than skipped.

### Linux backend design (shipped in 0.4.0)

This is the headline portability need. The same security policy the macOS backend enforces (writes confined to the workspace, network denied by default, per-phase `allow_network` opt-in) must be expressed with Linux primitives.

Backend:

- Add a Linux backend to `harness/sandbox.py` that maps the existing policy onto, in order of preference:
  - bubblewrap (`bwrap`) as primary: rootless, no daemon, lightweight. Confinement via read-only bind of the root filesystem, a read-write bind of the workspace, `--unshare-net` for network deny, a private `/tmp`, a minimal `/dev`, and `--die-with-parent`.
  - firejail as the alternative where bubblewrap is absent.
  - docker as a heavyweight fallback: the workspace bind-mounted, `--network none` for deny, non-root user.
- Extend `backend_name()` to detect the available backend on Linux and keep failing closed when none is present.

Parity tests:

- The existing escape tests (a worker `python3` writing outside the workspace is denied, network is denied, a workspace write succeeds, and shell/checks fail closed when no backend exists) must pass under the Linux backend with the same assertions as the macOS suite. Confinement equivalence is the acceptance bar, not merely "a sandbox runs".

CI:

- Run the full suite on both a Linux runner with bubblewrap installed and a macOS runner; assert both green. Add a job with no backend present and assert shell-using workflows fail closed.

Docs:

- Extend the backend section of [SECURITY.md](SECURITY.md) with a table: platform, backend, the confinement primitive used, and its known gaps.

Linux non-goals for now:

- seccomp-bpf syscall filtering beyond what bubblewrap already provides; revisit only if the threat model demands it.
- Rootless-container orchestration beyond a single bind-mounted workspace.

### Windows

The pure-Python harness logic runs on Windows, but shell and gate checks fail closed: there is no first-class rootless sandbox equivalent in scope. Windows sandboxing is out of scope for the current roadmap; workflows that need shell should run under WSL2 (which presents as Linux and uses the Linux backend) or on macOS.

## Non-goals (all platforms)

- Multi-agent coordination beyond orchestrator / worker / verifier until a single orchestrator is provably insufficient for a real job.
- Automatic, local-file, or untrusted plugin loading. Version 1 supports only explicit operator-trusted `harnessie.tools.v1` entry points; an untrusted mode requires a separately versioned out-of-process design.
- A hosted Harnessie API, MCP server, or autonomous remote agent. The public website and its discovery files document the local package and CLI; they do not turn Harnessie into a hosted service.

## How the planning docs relate

- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): numbered build steps, each with a pass/fail done-test. The how.
- [ROADMAP.md](ROADMAP.md): versioned milestones and platform support. The what-order and when-ready.
- [SECURITY.md](SECURITY.md): the security model each backend and control must satisfy. The invariants.
