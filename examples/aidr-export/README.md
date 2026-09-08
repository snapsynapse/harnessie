# Mock review to open AIDR export

This walkthrough runs two scripted `MockModel` actors through the actual `WorkflowRunner`, exports their open record through the installed `harnessie export-aidr` command, and checks the result with the pinned AIDR 0.1.0 reference linter. It makes no live provider calls and incurs no model cost. Both actors use the `mock` provider; this is an integration example, not evidence of independent review.

Use a source checkout or extracted source distribution with Harnessie installed in its Python environment. Python 3.11+, a supported POSIX environment, and Node on `PATH` are required. Node is used only for this demo's reference-linter check; the exporter itself has no Node dependency. The command below uses the repository's `.venv`, including its installed `harnessie` executable. Run it from the repository root.

Literal
```sh
.venv/bin/python examples/aidr-export/demo.py
```
The script creates a temporary project with mock model configuration, a human-arbitration workflow, and synthetic decision IDs. It removes that project before exiting and prints a JSON receipt. It does not edit the checkout or retain exported records. The reported temporary path therefore no longer exists after success. `--cli` can select another installed executable, and `--reference` can select another copy of the same pinned fixture; its provenance and file hashes must match.

The supported case demonstrates:

- Two instances of the `implementer` role become distinct participants, `implementer` and `implementer-2`, with original roles retained.
- One position recommends SQLite; the other opposes migration and records a concrete risk of losing history.
- Explicit `arbitration: human` leaves the run at `needs_arbitration`.
- Export produces synthetic `AIDR-9999` with an empty Arbitration section and the declared fixture arbiter `synthetic-human-tester`. This designation does not represent or authenticate a real person.
- The pinned reference linter passes; source record, event journal and other run files remain byte-for-byte unchanged through export and lint.
- Resuming the original run still returns `needs_arbitration` and makes no further model calls. Resume appends normal runtime events to its journal; the original decision record remains unchanged.

A second mock run includes an unclosed Markdown fence in its rendered task. Export intentionally refuses it with `invalid_record`, preserving its inputs and leaving no output or staging file. Unsupported formatting is refused, not silently rewritten.

A successful receipt reports `status: passed`, eight scripted mock calls across the two runs, zero live model calls, zero resume model calls, `export_preserved_inputs: true`, and `format_refusal_preserved_inputs: true`. Run IDs, fixture roles, assertions and reference bytes are reproducible; runtime timestamps and generated source reference values vary between invocations.

The reference fixture is under `tests/fixtures/aidr-0.1.0/`, copied from revision `a67c41d339d3e70bc3baaf07e652f9cf9d13a5bb`. Its structural lint result does not establish human authorship or semantic adequacy. The complete exporter contract is in [AIDR_EXPORT.md](../../AIDR_EXPORT.md).

The release smoke script runs this same example with a newly installed wheel, a working directory outside the repository, and no `PYTHONPATH`. It also verifies that the example imported Harnessie from the new virtual environment.
