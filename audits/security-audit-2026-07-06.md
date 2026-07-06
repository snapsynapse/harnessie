# Security Audit — harnessie — 2026-07-06

Standards: OWASP Top 10:2021. Tools: Bandit 1.9.4, pip-audit 2.10.0. First audit (no prior baseline).

## Executive Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 1 |

Posture: strong. SAST, dependency, secret, and configuration analysis are clean; all four Bandit hits are false positives or benign (explained below). A deeper OWASP A01/A04 pattern pass surfaced one genuine defense-in-depth finding (SEC-001): inter-phase reports — which are untrusted model output — are substituted into the next phase's task prompt without passing through the quarantine filter that tool results get. It is low severity because existing mitigations (role boundary text appended after the task, independent verifiers kept blind to prior reports) substantially reduce exploitability, but the asymmetry is real and worth closing. Overall risk level: low.

## Findings

### SEC-001 (LOW) — A04 Insecure Design: inter-phase reports bypass the quarantine filter

[runner.py:168-170](harness/runner.py:168). Prior-phase reports are substituted into a later phase's task template with a plain `str.replace`:

```python
task = phase["task"]
for key, value in reports.items():
    task = task.replace("{" + key + "}", str(value))
```

`reports[name]` is a prior phase's `outcome.report` — the output of a model that may have been prompt-injected. It flows into the next phase's task, which is part of that phase's prompt. `read_file` results get `quarantine=True` (scanned, invisibles-stripped, fenced as data-not-instructions) precisely because workspace content is untrusted ingress; inter-phase report text is equally model-adjacent but is not run through the same filter.

Why it is only LOW: the harness appends role-boundary text after the task (the harness gets the last word), and independent verifiers do not receive prior reports (runner.py phase wiring). A prompt-injected report can attempt to steer the next worker, but the boundary and the verifier gate stand between it and a bad outcome.

Remediation: run substituted report values through `guard_result` (harness/quarantine.py) before interpolation, fencing flagged content as data — the same treatment `read_file` already gets. Adds no dependency; reuses the existing filter. Suggested as a 0.4/0.5 hardening item, not a release blocker.

Note on method: a parallel OWASP A01/A04 agent proposed 13 findings; on verification 12 were self-refuted-as-defended, out-of-threat-model (operator-authored workflows are trusted), or refuted by test (the claimed `fnmatch` `**` glob gap does not exist — Python `fnmatch` `*` spans `/`, so ownership lanes are over-broad, which is fail-safe for deny lanes). SEC-001 is the one that survived verification.

## Automated Scan Results

### Bandit (SAST)

3,368 lines analyzed, 0 nosec comments. Raw severity counts: 1 HIGH, 3 MEDIUM, 13 LOW. Every MEDIUM+ result is a false positive or benign:

| Test | Location | Bandit says | Assessment |
|---|---|---|---|
| B613 (HIGH) | [quarantine.py:39](harness/quarantine.py:39) | source contains bidirectional control characters | False positive, ironic. The bidi chars are literals inside `INVISIBLE_CHARS`, the regex that detects and strips bidi/zero-width characters from tool output. The flagged code is the defense against the trojan-source class Bandit is warning about. Keep as-is. |
| B310 (MEDIUM) | [models/anthropic.py:57](harness/models/anthropic.py:57) | `urlopen` permits file:/custom schemes | Benign. URL is the hardcoded constant `https://api.anthropic.com/v1/messages`; no request-controlled input reaches it. Not SSRF. |
| B310 (MEDIUM) | [models/openai_compat.py:53](harness/models/openai_compat.py:53) | `urlopen` permits file:/custom schemes | Benign. URL derives from operator-configured `base_url` in `config/models.yaml`, not from untrusted request input. This is deployment configuration, outside the untrusted-content trust boundary. |
| B108 (MEDIUM) | [sandbox.py:111](harness/sandbox.py:111) | probable insecure temp file/directory | False positive. The line is `"--tmpfs", "/tmp"`, a bubblewrap argument mapping a private in-sandbox tmpfs. It is a confinement control, not a host temp-file operation. |

The 13 LOW findings are dominated by the expected `subprocess` import/call warnings (B404/B603); the targeted B105/B108/B110 pass surfaced only the B108 above. No hardcoded-password (B105) or swallowed-exception (B110) findings.

### Dependencies (pip-audit)

Runtime dependency surface is a single package: `pyyaml>=6.0` (resolved 6.0.3). Zero known vulnerabilities. `pytest` is dev-only. Minimal dependency surface is itself a security property here.

### Secret Scan

Clean. No hardcoded API keys, AWS credentials, private keys, JWT secrets, or connection strings in any tracked file. `git log --diff-filter=A` shows no `.env`, `.pem`, or `.key` file ever committed. `git ls-files '*.env*'` returns nothing. `.gitignore` covers `.env` and `.env.*`.

### Configuration Review

Server-surface checks (CORS, CSP, security headers, rate limiting) are not applicable: harnessie is a CLI and library with no HTTP server and no inbound authentication. Applicable checks:

| Check | Result | Evidence |
|---|---|---|
| E1 `.env` in `.gitignore` | PASS | `.gitignore:3-4` covers `.env` and `.env.*` |
| E3 no hardcoded key fallback | PASS | Keys read from env only; `ModelSpec.api_key_env` stores the env var name, never the key ([models/base.py:32](harness/models/base.py:32), [anthropic.py:46](harness/models/anthropic.py:46), [openai_compat.py:47](harness/models/openai_compat.py:47)) |

## Code Pattern Analysis (OWASP Top 10:2021)

| Category | Findings | Notes |
|---|---|---|
| A01 Broken Access Control | 0 | Role/permission is enforced at registry dispatch, not in prompts: a role not in `allowed_roles` is refused before the tool function runs ([registry.py:131](harness/tools/registry.py:131)). The model only ever sees schemas for tools its role may call. Ownership lanes gate `write_file` by first-writer and operator-locked lanes. |
| A02 Cryptographic Failures | 0 | No custom crypto. Identifiers use `secrets.token_bytes` with rejection sampling ([ids.py:25](harness/ids.py:25)). No MD5/SHA1 used for security. |
| A03 Injection | 0 | No `eval`, `exec`, `os.system`, `pickle`, or `shell=True`. All `subprocess.run` calls use array form through the sandbox wrapper. All YAML parsing uses `yaml.safe_load`. The only `.format()` calls target trusted fence-header constants. |
| A04 Insecure Design | 0 | Consent lock, ownership lanes, and fail-closed sandbox are the design. Client/agent-supplied identifiers are not used for trust decisions; agent identity is passed by the harness, not the model. |
| A05 Security Misconfiguration | 0 | Fail-closed everywhere: no usable sandbox backend blocks shell rather than running unconfined. Child processes run under a scrubbed environment. |
| A06 Vulnerable Components | 0 | Single runtime dependency, lock-free by design, zero known vulns. |
| A07 Auth Failures | 0 | No inbound authentication surface (no server). Provider API keys are never inherited by child processes (`scrubbed_env`), so an injected `print(os.environ)` finds nothing. |
| A08 Data Integrity Failures | 0 | No untrusted deserialization. Events are hash-chained; `harnessie audit` detects tampering. |
| A09 Logging Failures | 0 | `run_shell` output passes through `redact_secrets` before returning; `write_file` blocks credential-shaped content via `find_secrets` (which, as of v0.3.3, returns kind labels, not value fragments). |
| A10 SSRF | 0 | The two `urlopen` sites use a hardcoded constant and operator-configured `base_url` respectively; neither takes a URL from untrusted request/agent input. |

## Remediation Priority

None. No P0–P3 items. Optional hygiene (not findings):

- The two B310 and one B108 Bandit hits could be annotated with `# nosec` and a one-line justification to keep future automated runs at zero noise. This is cosmetic; the current code is correct.

## Positive Security Controls

- Policy enforced in code at registry dispatch, not in prompts — no role prompt can opt out (registry.py).
- Fail-closed-everywhere sandbox policy: shell blocked when no backend passes its startup smoke test (sandbox.py).
- Scrubbed child-process environment: provider keys not inherited, nothing to exfiltrate even with network opted in (builtin.py `scrubbed_env`).
- Layered quarantine: bidi/zero-width stripping, injection-pattern scanning, data-not-instructions fencing, and secret redaction on tool output (quarantine.py).
- Structured refusal grammar with hash-chained, tamper-evident audit events (registry.py, audit.py).
- `find_secrets` returns kind labels, never credential fragments (v0.3.3 hardening) — secrets never reach model observations or the audit timeline.
- Minimal dependency surface: one runtime dependency.

## Methodology

Bandit 1.9.4 (`-r harness -ll`, plus targeted B105,B108,B110 pass), pip-audit 2.10.0 against the resolved runtime dependency, Grep-based secret patterns across all tracked source, `git log --diff-filter=A` history check, and manual OWASP pattern analysis over the harness package (3,368 LOC, 20 modules). Static analysis only; no runtime probing. First audit — no delta section.
