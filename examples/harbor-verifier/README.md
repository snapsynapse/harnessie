# Harnessie as a Harbor verifier

Harbor (https://harborframework.com/) runs an agent against a containerised task and then runs a verifier that writes a reward. This example makes `harnessie verify` that verifier, in the two shapes Harbor supports, and keeps one rule either way: a result Harnessie cannot verify is unscorable, never a zero.

| `harnessie verify` exit | Meaning | Harbor reward |
|---|---|---|
| 0 | verified: every check passed | `reward.txt` = `1` |
| 1 | failed: a check failed | `reward.txt` = `0` |
| 2 | cannot verify: no sandbox, no checks, verifier crashed | no reward file; `harnessie-verify.json` records why |

Writing `0` for exit 2 would teach a policy that an unverifiable result is a failure to avoid, which is not what the task meant to teach. Harbor carries "no number" in two different ways, and the first real trials (see `audits/harbor-verifier-acceptance-2026-10-05.md`) showed both: a custom verifier returning `rewards=None` gives a completed trial with no score and no exception, while a `tests/test.sh` that writes no reward file makes Harbor's default verifier raise `RewardFileNotFoundError` and record an errored trial. Neither is a zero. OpenEnv's training path carries a verifier that never scored through as `reward=None`.

Only deterministic checks map to reward. The verifier model (`harnessie verify` without `--no-verifier`) is a judgment and is never used as a training signal here.

## Layout

```
examples/harbor-verifier/
  harnessie_reward.py      exit-code mapping, reward files, verify command; no Harbor import
  harnessie_verifier.py    HarnessieVerifier(BaseVerifier): host-side form
  tasks/calc-add-mean/     a Harbor task whose tests/test.sh is the in-sandbox form
    instruction.md
    task.toml
    environment/Dockerfile python:3.12-slim with bubblewrap
    solution/solve.sh      oracle answer
    tests/claims.md        the acceptance claims harnessie verifies against
    tests/test.sh          runs harnessie verify inside the sandbox, maps the exit code
```

## Form A: host-side verifier (recommended)

Harbor's custom verifier interface runs `verify()` in the Harbor process. `HarnessieVerifier` downloads the agent's workspace from the environment, runs `harnessie verify --no-verifier` on the host under Harnessie's own OS sandbox (Seatbelt on macOS, bubblewrap or firejail on Linux), writes the reward files into the trial's verifier directory, and returns the mapped `VerifierResult`.

Literal
```bash
PYTHONPATH=examples/harbor-verifier harbor run -p examples/harbor-verifier/tasks -a oracle -e docker --verifier harnessie_verifier:HarnessieVerifier
```

`-a oracle` runs the task's own solution so the verifier is exercised against a known-good workspace. Replace `-e docker` with any Harbor environment type you have (`apple-container`, `podman`, `e2b`, `modal`). Kwargs: `--verifier-kwarg checks="cmd one ;; cmd two"`, `workspace=/app`, `claims=tests/claims.md`, `python=/path/to/python-with-harnessie`.

This is the form that fits Harnessie's security model: the OS sandbox is the host's, nothing extra is needed inside the task image, and the verifier never shares a process with the agent.

## Form B: in-sandbox `tests/test.sh`

The portable Harbor shape: `tests/test.sh` runs inside the task container after the agent, installs the pinned `harnessie` release with `uv`, runs `harnessie verify --no-verifier` with the task's checks, and maps the exit code as above.

Literal
```bash
harbor run -p examples/harbor-verifier/tasks -a oracle -e docker
```

Caveat, stated up front and now observed: `harnessie verify` runs every `--check` inside an OS sandbox and fails closed without one. The image ships bubblewrap, but under Harbor's Docker backend with default confinement bubblewrap cannot create the namespaces it needs, and Harnessie reports "no OS sandbox backend on Linux; child-process execution is blocked (fail-closed policy)", exit 2, no reward file. Harbor then records the trial as errored (`RewardFileNotFoundError`). That is the harness working as specified, the diagnostic file names it, and it is why Form A exists.

If you run Harbor's Docker backend through Colima, put the jobs directory (`-o`) under your home directory. Colima shares only `$HOME` into its VM, and a jobs directory elsewhere leaves the container's `/logs/verifier` mount unreachable from the host, which presents as an empty verifier directory with no diagnostic at all.

## Testing without Harbor

`tests/test_harbor_verifier_example.py` in the repository covers the mapping, the reward files, `test.sh` with a stub verifier for all three exit codes, and a real `harnessie verify` on a sample workspace where a sandbox backend is available. `HarnessieVerifier` itself imports Harbor and is only loaded where Harbor is installed.

To exercise `test.sh` by hand with a stub that exits 2:

Literal
```bash
HARBOR_VERIFIER_DIR=/tmp/hv HARNESSIE_VERIFY_CMD="sh -c 'exit 2'" bash examples/harbor-verifier/tasks/calc-add-mean/tests/test.sh && ls /tmp/hv && cat /tmp/hv/harnessie-verify.json
```

## What this does and does not establish

It establishes that Harnessie's verdict contract maps cleanly onto Harbor's reward contract, including the cannot-verify case, and that a Harbor job can use Harnessie as its verifier without changes to either project. Four trials on Harbor's Docker backend are recorded in `audits/harbor-verifier-acceptance-2026-10-05.md`: the host-side form scored 1 with the oracle agent, 0 with the no-op agent, and stayed unscored with an empty check list; the in-sandbox form failed closed as described above. One task and one backend; nothing here is evidence about any brain.
