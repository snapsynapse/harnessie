# Claude subscription-route authentication contract

Date: 2026-10-01
Scope: read-only local route check and offline fail-closed contract repair
Status: implemented and verified offline; no model call or live execution authorized

## Operator direction

Sam directed the pilot to prefer the existing Claude subscription allowance over evidence reduction or API billing, then authorized a quick route test and the recommended authentication-contract repair. This authority covered read-only CLI metadata checks and offline implementation only. It did not authorize inference, an account change, a token-policy increase, panel-v4, Git delivery or release.

## Observed local state

Claude Code `2.1.261` reports `loggedIn: true`, `authMethod: oauth_token` and `apiProvider: firstParty`. It no longer emits the earlier `subscriptionType: max` field. The same result was returned with the ordinary process environment and with Harnessie's credential-denying environment whitelist.

None of the checked API-key or alternate-provider variables was present: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `AWS_ACCESS_KEY_ID`, `AWS_PROFILE` or `GOOGLE_APPLICATION_CREDENTIALS`. A sentinel test confirmed that the Harnessie child environment removes all of them when present.

This proves that the inspected CLI route is stored first-party OAuth and that the Harnessie adapter does not provide an environment or settings-source path for API-key, Bedrock or Vertex fallback. It does not prove the account's Max tier, included-allowance state or usage-credits setting. Those remain separate, fresh execution-authority evidence.

## Contract repair

Contract `claude-code-first-party-oauth-plus-billing/v2` separates route identity from billing authority:

- current `oauth_token` plus `firstParty` metadata maps to `claude.ai:oauth:firstParty` without claiming Max;
- the historical `claude.ai` plus `max` plus `firstParty` shape remains recognizable as `claude.ai:max:firstParty` for retained evidence;
- API-key, third-party-provider and logged-out shapes remain ineligible;
- preflight metadata explicitly reports `billing_route: requires_separate_account_evidence`;
- execution authority requires the exact v2 contract, an eligible auth class, fresh included-Fable-allowance evidence and usage credits off;
- the live adapter is bound to the preflight auth class and refuses `auth_identity_drift` before inference if the route changes;
- inference continues to use the environment allowlist and `--setting-sources ""`.

The historical additional-model policy is unchanged. This repair does not raise the 4,096 per-call or 32,768 run-wide Haiku input thresholds.

## Verification

- Actual installed CLI metadata passed through the repaired preflight path and produced the v2 contract with `claude.ai:oauth:firstParty`.
- Focused current-OAuth, API-key refusal, route-drift, environment isolation, preflight and execution-authority tests passed.
- The complete pilot suite passed: 193 tests.
- No inference-capable command, model request, account mutation, browser action or explicit API credential was used. Network and credential-store access internal to the Claude CLI metadata commands was not instrumented.

The next bounded decision is the separately versioned context-sized Haiku policy and full-evidence offline rehearsal. Its numerical token ceilings and all live allowance remain unapproved until presented in a new execution proposal.
