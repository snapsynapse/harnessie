# Pending eval suites

Scorecards written before their scenario kinds exist in `harness/evals.py`. The default runner globs only `evals/*.yaml`, so nothing here runs yet and the shipped count is unchanged.

When a suite's kind is implemented, move the file up one directory in the same change. It then joins the default suite and `tests/test_evals.py` counts it. A suite left here after its kind ships is unprocessed work.

- `bidding.yaml`: kind `bid` (AIDR-0009). Runs after `harness/bidding.py` and the `bid:` phase key land.
- `observer-commentary.yaml`: deferred commentary capability. Keep pending until that separately approved slice is implemented.

Activation is capability-specific: a scenario kind alone does not authorize promoting deferred scenarios. Every expectation must be asserted by the adapter, never silently ignored. CLI diagnostics, path confinement, and JSON payload omission are active pytest contracts in `tests/test_observer_acceptance.py`.

The offline observer suite is active at `evals/observer.yaml`. Bidding, commentary and runner-integration tests retain strict expected failures until separately approved and implemented.
