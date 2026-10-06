# Verification report: CANNOT VERIFY

- generated: 2026-10-06T03:21:29Z
- workspace: /app
- criteria: /tests/claims.md
- criteria_sha256: 671f118634980a96e8bdaa3395c98aeae3df5cd146dc8bf4d726a383914afcd7
- verifier model: (none — deterministic checks only)
- checks network: denied
- exit code: 2 (0 verified / 1 failed / 2 cannot verify, fail closed)

## Deterministic checks

### [FAIL] check-1

```
sandbox unavailable, check blocked (fail-closed): no OS sandbox backend on Linux; child-process execution is blocked (fail-closed policy). Wire a backend (bubblewrap / firejail / docker) to enable shell on this platform.
```

### [FAIL] check-2

```
sandbox unavailable, check blocked (fail-closed): no OS sandbox backend on Linux; child-process execution is blocked (fail-closed policy). Wire a backend (bubblewrap / firejail / docker) to enable shell on this platform.
```

## Verifier judgment

(not consulted: sandbox unavailable for checks: check-1, check-2; nothing was observed, so no verdict is earned)
