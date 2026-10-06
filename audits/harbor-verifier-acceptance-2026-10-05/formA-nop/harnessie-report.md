# Verification report: FAILED

- generated: 2026-10-06T03:22:37Z
- workspace: <tmp>
- criteria: <repo>/examples/harbor-verifier/tasks/calc-add-mean/tests/claims.md
- criteria_sha256: 671f118634980a96e8bdaa3395c98aeae3df5cd146dc8bf4d726a383914afcd7
- verifier model: (none — deterministic checks only)
- harness: harnessie 1.4.1
- inward manifest sha256: 91acd9976c66f40549db394ee25a0ea395fdfebdce24aa3bd3de03b59f2905d8
- tool set sha256: ff7a60ebaa0db482f4154ea9b2b52d3e8fbfa5139708f6908f76494528778e77
- checks network: denied
- exit code: 1 (0 verified / 1 failed / 2 cannot verify, fail closed)

## Deterministic checks

### [FAIL] check-1

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import calc; assert calc.add(2, 3) == 5
    ^^^^^^^^^^^
ModuleNotFoundError: No module named 'calc'
```

### [FAIL] check-2

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import calc
ModuleNotFoundError: No module named 'calc'
```

## Verifier judgment

(not consulted: deterministic checks already failed: check-1, check-2)
