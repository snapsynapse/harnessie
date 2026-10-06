# Harbor verifier acceptance, 2026-10-05

First real Harbor trials of `examples/harbor-verifier/`: Harnessie as the verifier of a Harbor task, on Harbor's Docker backend, in both shapes Harbor supports. Four trials, all against the `calc-add-mean` task. Evidence per trial is in `harbor-verifier-acceptance-2026-10-05/` (reward files, Harnessie's own report, Harbor's result excerpt), with home-directory and temp paths scrubbed.

## Setup

- Harbor 0.24.0 in the scratch `oe` virtualenv (Python 3.12.15). Harnessie 1.4.1 from the working tree at `42b0dd7` for the host-side form; the pinned PyPI release `harnessie==1.4.1` installed by `uv` inside the container for the in-sandbox form.
- Backend: Harbor `docker` against a Colima 0.10.3 VM (macOS Virtualization.framework, Ubuntu 24.04.4 aarch64, 2 CPUs), Docker Engine 29.5.2, Docker CLI 29.8.2, Docker Compose 5.5.1. Colima and the Docker CLI were already installed on the machine; the one change was a symlink in `~/.docker/cli-plugins/` so the CLI could find the installed compose plugin.
- Agents: Harbor's `oracle` (runs the task's `solution/solve.sh`) and `nop` (does nothing). No model was called by any trial.

## Trials

| Trial | Form | Agent | Harnessie exit | Reward file | Harbor records |
|---|---|---|---|---|---|
| formA | host-side `HarnessieVerifier` | oracle | 0 verified, checks 2/2 PASS | `reward.txt` = 1 | `rewards: {reward: 1.0}`, 1 completed trial, mean 1.0 |
| formA-nop | host-side | nop | 1 failed (no `calc.py`) | `reward.txt` = 0 | `rewards: {reward: 0.0}`, 1 completed trial, mean 0.0 |
| formA-nochecks | host-side, `checks=` empty | oracle | 2 cannot verify (nothing to check) | none | `rewards: None`, 1 completed trial, 0 scored trials, 0 exceptions |
| formB | in-sandbox `tests/test.sh` | oracle | 2 cannot verify (no OS sandbox inside the container) | none | `RewardFileNotFoundError`, 1 errored trial |

Each host-side trial took about 12 seconds; the in-sandbox trial 16 seconds including the `uv` install of Harnessie.

## What the trials establish

- The exit-code mapping holds under a real Harbor job for all three Harnessie outcomes: verified scores 1, failed scores 0, and cannot-verify produces no number.
- The two ways Harbor can carry "no number" differ, and the README now says so. A custom `BaseVerifier` returning `rewards=None` yields a completed trial with no score and no exception, which is the cleanest expression of unscorable. A `tests/test.sh` that writes no reward file makes Harbor's default verifier raise `RewardFileNotFoundError`, so the trial is recorded as errored. Neither is a zero, which is the invariant that matters for training; the host-side form is the one to prefer.
- The in-sandbox form's failure is the predicted one, in Harnessie's own words from inside the container: "no OS sandbox backend on Linux; child-process execution is blocked (fail-closed policy)". Bubblewrap is installed in the image; the container runtime does not let it create the namespaces it needs under default confinement. Harnessie refused to run the checks unconfined and reported exit 2. That is the harness working as specified, and it is why the host-side form exists.
- Harnessie's report inside the trial directory carries the harness identity header (version, inward manifest digest, tool set digest) next to the verdict, so a Harbor result produced this way names the harness that scored it.

## Limits

- One task, one backend, no model agent. This proves the contract between `harnessie verify` and Harbor's verifier interface, not the quality of any brain.
- Colima shares only `$HOME` into its VM. A Harbor jobs directory outside that path leaves the container's `/logs/verifier` mount unreachable from the host, which presented as an empty verifier directory and a `RewardFileNotFoundError` with no diagnostic. The first attempt hit this; the recorded trials use a jobs directory under the repository's ignored `runs/`. Harbor users on Docker Desktop will not see this.
- The in-sandbox form could score if the task image were run with the capabilities bubblewrap needs, or if Harnessie gained a backend that confines without namespaces. Neither was attempted; the fail-closed result is the one worth recording.

## Reproduce

Literal
```bash
PYTHONPATH=examples/harbor-verifier harbor run -p examples/harbor-verifier/tasks -a oracle -e docker --verifier harnessie_verifier:HarnessieVerifier --verifier-kwarg python=.venv/bin/python -o runs/harbor-jobs
```

Literal
```bash
harbor run -p examples/harbor-verifier/tasks -a oracle -e docker -o runs/harbor-jobs
```

Dated observations under the versions above; a different Harbor, backend or Harnessie version requires a new run.
