# Schema compatibility

Harnessie 1.0 freezes six operator-authored contracts at schema version 1: model configuration, cascade policy, boundary policy, approval and rehydration policy, ownership policy, and workflows. YAML is the authoring syntax. JSON Schema Draft 2020-12 files under `harness/schemas/v1/` are the executable structural authority and are served byte-identically from `https://harnessie.com/schemas/v1/`.

## Version selection

- New documents declare `schema_version: 1`.
- A document without `schema_version` is implicit v1. This preserves every valid 0.8 document and remains supported for the entire 1.x line.
- A boolean, string, or unsupported integer version fails before other validation. Harnessie never guesses a version.
- The inward and outward manifests retain their existing `kind` plus `version` contracts. They are machine artifacts, not part of this authoring-schema family.

## Validation contract

- Unknown keys fail at every core schema level. Provider-specific request fields belong only under a model's explicit `extra` mapping.
- Types are exact. Strings are not coerced to booleans or numbers, and falsey invalid containers are not converted to defaults.
- Structural validation runs before cross-document validation. Cross-document checks cover configured tiers, cascade names, role and verifier names, unique phase names, prior-phase placeholders, and consecutive parallel groups.
- Ownership lane and claim paths must be relative POSIX paths or globs without traversal, backslashes, control characters, or surrounding whitespace. Broad globs are accepted but sandbox enforcement protects their conservative literal prefix.
- Diagnostics are deterministic and contain source, instance path, code, message, and schema version. Invalid authoring input exits 2 and never reaches a model.
- `harnessie validate` validates the project without model calls, network, sandbox admission, run-state creation, or workspace writes. `harnessie validate PATH --kind KIND` validates one explicitly typed document.

## Standalone verification evidence

The separately versioned `verify-evidence.schema.json` contract governs optional evidence bundles accepted by `harnessie verify`. It is not a seventh project-authoring document and is not loaded by `harnessie validate`. A bundle is an immutable intake envelope: stable claims, an exact workspace revision and dirty state, and content-addressed diffs, proof files, and recorded checks. Bundle schema version 1 remains additive to raw Markdown criteria; callers choose exactly one input form. Changing an existing v1 field incompatibly requires a new evidence-bundle schema version.

## Defaults

Defaults are part of the behavioral contract even when omitted from YAML. Current v1 defaults are the runtime defaults already shipped in 0.8: model token and cost fields use `ModelSpec` defaults; the run budget uses `Budget` defaults when absent; cascade policies default to gate-failure escalation, full ladder-bounded climb, and defer on exhaustion; the boundary defaults off; approval and rehydration policies default deny-all; ownership lane groups and claims default empty; workflow phases default to 40 steps, network denied, no tool pre-approval, and the existing role-specific consent behavior.

Changing a behavioral default is a major-version change. JSON Schema's `default` annotations document defaults but do not mutate input; Harnessie's runtime applies the named defaults after validation.

## Compatible and breaking changes

- Adding an optional field without changing existing behavior is minor-version compatible.
- Adding a required field, removing a field, narrowing a valid value, or changing field semantics is major-version work.
- Inputs outside the published schema were never supported. Rejecting such an input more precisely is not a breaking change.
- A deprecation begins in a minor release with a machine-readable diagnostic and documentation, remains accepted for the rest of that major line, and may be removed only in the next major.
- Security repairs may reject an input in the current major only when it was already invalid under the published schema or it bypassed a stated fail-closed invariant.

## Extension boundary

Version 1 defines no plugin configuration namespace. The active plugin contract is command-line admission of installed `harnessie.tools.v1` entry points, documented separately in `PLUGIN_CONTRACT.md`; it does not widen any of the six authoring schemas. Nonempty unknown extension data in a v1 authoring document remains invalid. Any future plugin-owned configuration requires its own namespaced schema identity and compatibility policy rather than an unvalidated escape hatch.

## Outside this guarantee

Eval suites, ecosystem metadata, run journals, event records, maiden proposal records, trace metrics, and generated decision records are versioned or maintained separately. They do not silently become stable 1.0 authoring APIs through this document.
