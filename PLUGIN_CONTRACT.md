# Plugin contract

Status: stable for the Harnessie 1.x line. The extension surface is versioned separately from the Harnessie package.

## One extension mechanism

Harnessie discovers installed Python package entry points in exactly one group: `harnessie.tools.v1`. It does not scan project directories, import `tools/*.py`, or auto-enable installed packages.

An operator admits a plugin explicitly for `run` and `resume` with repeatable `--plugin NAME` arguments. Resume requires the same recorded receipt, including names, versions, entry-point targets, public tools, and declarative contract hashes. Missing, duplicate, renamed, malformed, or drifted plugins fail before model dispatch.

## Trust boundary

An admitted v1 plugin executes in the Harnessie process and is operator-trusted code. Python import and tool-call code can access the process, environment, and filesystem with the operator's authority. Registry mediation does not sandbox the implementation or prove that its declared effects are complete.

Do not install or admit untrusted plugins. Harnessie v1 has no untrusted plugin mode. A future untrusted mechanism must use a separately versioned out-of-process protocol and must carry the active agent's read-only lane profile, scrubbed environment, network default, approval decision, and effects declaration into the confined child process.

## Entry point value

The selected entry point must load either a `PluginDeclaration` or a zero-argument callable returning one. A declaration contains:

- `name`: the entry point name, using lowercase letters, digits, hyphens, or underscores
- `version`: a nonempty immutable plugin contract version for resume identity; it must change whenever plugin behavior changes
- `tools`: one or more `ToolSpec` values with local names

Harnessie exposes each local tool as `PLUGIN__TOOL`. The combined name must be at most 64 characters and use only letters, digits, hyphens, and underscores. The loader supplies immutable provenance as `plugin:NAME@VERSION`; a plugin cannot self-assert different provenance. The run receipt includes the entry-point target, public tool names, and a SHA-256 digest of the complete declarative tool policy. Resume refuses receipt drift. The plugin publisher remains responsible for changing `version` whenever executable behavior changes because Python callable bytes are not a portable identity surface.

Each tool must declare a JSON object parameter schema, one effects class (`read`, `write`, or `execute`), at least one known role, whether approval is required, whether role context is passed, and whether returned text is quarantined. Duplicate public tool names and invalid declarations fail closed.

## Example package metadata

```toml
[project.entry-points."harnessie.tools.v1"]
acme = "acme_harnessie:plugin"
```

The callable may return:

```python
PluginDeclaration(
    name="acme",
    version="1.0.0",
    tools=(ToolSpec(
        name="lookup",
        description="Look up an approved local record.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        fn=lookup,
        effects="read",
        allowed_roles=frozenset({"worker", "verifier"}),
        requires_approval=False,
        quarantine=True,
    ),),
)
```

The model-visible tool name is `acme__lookup`.
