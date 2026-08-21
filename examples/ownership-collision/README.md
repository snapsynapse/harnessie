# Ownership-collision proof

This zero-model, zero-network example attempts the failure Harnessie's Golden Rule is designed to prevent. Alice creates `report.txt`; Bob then tries to replace it through the same built-in `write_file` tool an agent uses during a run. The example passes only if Bob receives the structured `ownership_denied` refusal and Alice's exact bytes survive.

This example targets Harnessie 1.1.0 or a current source checkout. The `harnessie ownership` inspection command ships in 1.1.0.

## Run the collision proof

From the repository root after installing the development dependencies:

Literal
```bash
python3 examples/ownership-collision/demo.py
```
Expected result:

```text
alice first write: ALLOWED
bob overwrite: DENIED (ownership_denied)
surviving artifact: alice-v1
recorded owner: alice
Golden Rule proof: PASS
```
The example uses a temporary directory and removes it on exit. It does not modify the checkout.

## Inspect a real project policy

Harnessie 1.1.0 adds a read-only explanation command. It evaluates the same ledger decision used by `write_file` and does not claim or modify a path.

Replace: PROJECT_ROOT -> the Harnessie project directory containing `OWNERSHIP.yaml`

Replace: WORKSPACE_PATH -> the path to inspect, relative to that project's `workspace/`

Replace: AGENT_NAME -> the agent identity to evaluate

Customize
```bash
python3 -m harness.cli --root PROJECT_ROOT ownership WORKSPACE_PATH --agent AGENT_NAME
```
Add `--json` for a schema-versioned machine decision. Schema version 1 fixes the fields and source vocabulary. A valid allowed or denied explanation exits 0; an invalid path or ownership document exits 2.
