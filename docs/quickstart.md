# Quickstart for people, not just developers

This is the gentlest path into Harnessie. It assumes you have never cloned a repository, never written YAML, and are not sure what a terminal is for. That is fine. Every command here is safe, nothing reaches the internet or spends money until you decide it should, and the tool checks your machine for you before anything runs.

If you are already comfortable in a terminal, the faster five-minute path is [Getting started](getting-started.md), and the full reference is [the user guide](GUIDE.md).

## What Harnessie is, in one breath

A harness is the structure you put around an AI model so it can do real work while you stay in control. It decides what the AI is allowed to do, checks the work before moving on, and writes down everything that happened so you can read it back. Harnessie is built to be a safe first one: it runs on your own machine, and its first run costs nothing because it uses a pretend "mock" model instead of a paid one.

New words (harness, agent, workflow, gate, brain, and so on) are collected in the [Glossary](#glossary) at the end. You do not need to memorize them; glance down when one shows up.

## What you need

- A computer running macOS, Linux, or Windows with WSL2 (see [Running on Windows](#running-on-windows) below).
- Python 3.11 or newer. To check, open a terminal and run `python3 --version`. If it prints 3.11 or higher, you are set. If not, install Python from python.org first.
- A terminal. On macOS it is the Terminal app; on Linux it is your shell; on Windows it is the WSL2 (Ubuntu) window.

You do not need an API key, a credit card, or a cloud account to finish this quickstart.

## Step 1: Get Harnessie

One line installs the `harnessie` command from the Python package index:

```bash
pip install harnessie
```

If `pip` is not found, try `python3 -m pip install harnessie`. If you use pipx, uv, or Homebrew, `pipx install harnessie`, `uv tool install harnessie`, and `brew install snapsynapse/tap/harnessie` work the same way. You do not need to download or clone anything.

## Step 2: Let the tool check your machine

Create your own project and let Harnessie tell you whether everything is ready:

```bash
harnessie init my-first-project
```

This scaffolds a small project (a config file, an example workflow, the agent instructions) and then runs a guided first check. You will see something like:

```
Guided first run — is this machine ready?

  [ok  ] Python: Python 3.12 meets the 3.11+ requirement.
  [ok  ] Sandbox: OS sandbox backend detected: seatbelt. Shell work will be confined.
  [ok  ] API keys: No API key needed: this scaffold uses the mock brain, so your first run costs zero dollars.
  [ok  ] First run: Zero-dollar mock run: 2/2 eval baseline checks passed. Your harness works end to end and billed nothing.

You are ready. Run your first workflow:
  harnessie run workflows/build-and-verify.yaml --goal "your goal here"
```

Read each line. If Python is too old, it says so. If your computer has no sandbox (the safety cage around any command the AI runs), it says so plainly and explains that shell work will simply be blocked until you add one, which is protection, not breakage. The last line proves the harness works, using the mock model, for zero dollars.

## Step 3: Run your first real workflow

Move into your project and run the built-in workflow, which plans a small change, makes it, and checks it:

```bash
cd my-first-project
harnessie run workflows/build-and-verify.yaml --goal "a to-do list saved to a text file"
```

Before it starts, Harnessie prints a cost preview. Because the scaffold uses the mock model, it will say `MOCK (zero-dollar, nothing is billed)`. The run then prints a plain summary at the end. Every run gets an id; note it down, or copy it from the summary.

To use a real, paid AI model later, you edit one file (`config/models.yaml`) and set the model's key as an environment variable in your terminal. You never paste a key into a file. Harnessie refuses to start a paid run that has no spending ceiling, so you cannot accidentally run up a bill.

## Step 4: Read what happened

A run never just says "done". Ask for a plain-language report:

```bash
harnessie report <run_id>
```

Put your run's id in place of `<run_id>`. The report tells you, in ordinary sentences, which steps completed, whether the run stopped and is waiting for you, and the single next thing to do. For the complete, hash-verified trail of every action, run `harnessie audit <run_id>`.

## Step 5: When a run stops and waits for you

Silence is never treated as success. A run ends in a named condition, and each one names one action:

- Completed: the goal was met and every check passed. Nothing to do.
- Stopped and waiting for you (`needs_human`): a check did not pass. Read the report, fix what it points at, and run the `harnessie resume ...` command it gives you.
- A contested decision needs your call (`needs_arbitration`): the agents disagreed and did not paper over it. The report names the exact decision file to edit; record your decision there, then resume.

Re-running is safe: a resume only re-does the steps that did not already pass.

## Running on Windows

Harnessie's safety depends on an operating-system sandbox that confines any command the AI runs. macOS and Linux provide one. Bare Windows (the Command Prompt or PowerShell) does not provide one that Harnessie can use, so on bare Windows the harness fails closed: any workflow step that runs a shell command is blocked rather than run without a cage. That is deliberate. An unconfined command is exactly the risk the sandbox exists to remove, so running without one would quietly break the core safety promise.

The supported path on Windows is WSL2 (Windows Subsystem for Linux), which gives you a real Linux environment inside Windows:

1. Open PowerShell as Administrator and run `wsl --install`. Restart when asked.
2. Launch the installed Ubuntu app and finish its first-time setup.
3. Inside that Ubuntu window, follow this quickstart from [Step 1](#step-1-get-harnessie). It is now a Linux machine, and the Linux sandbox (bubblewrap) applies.

Everything mock and offline works on bare Windows too (the checks, the eval baseline, reading reports), because none of it runs a sandboxed shell command. It is only shell-using workflow steps that require WSL2. If you are only exploring, you can start on bare Windows and move to WSL2 when you want to run a real workflow.

## Glossary

Terms in the order a newcomer meets them, each in one plain sentence.

- Harness: the structure around an AI model that decides what it may do, checks its work, and records what happened.
- Brain / model: the AI itself. Harnessie can use different ones without code changes; you pick in a config file.
- Mock brain: a pretend model that follows a fixed script, used so your first runs are free and predictable.
- Tier: a named slot for a model (for example `cheap`, `mid`, `frontier`), so a workflow can ask for "a capable model" without naming a specific vendor.
- Agent: one AI doing one job within a run. The three kinds below are all agents.
- Orchestrator: the agent that breaks your goal into small tasks and hands them out. It cannot change files itself.
- Worker: an agent that does one scoped task inside a walled-off folder and reports what it did.
- Verifier: an independent agent that checks a worker's result against the rules before the run moves on. It is deliberately not shown the worker's reasoning.
- Workflow: the ordered list of steps for a job, written in a small YAML file.
- Phase / step: one entry in a workflow, handled by one agent.
- Gate: the check at the end of a phase. If it fails, the run stops instead of building on unverified work.
- Workspace: the walled-off folder agents may write in. They cannot reach outside it.
- Sandbox: the operating-system cage around any command an agent runs, so it cannot touch your files or the network unless you allow it.
- Ceiling / budget: the maximum tokens and dollars a run may spend. A paid run refuses to start without one.
- Consent: a worker must accept a task before it is allowed to change anything; a task is an offer, not an order.
- Ownership lane: a rule about which agent (or you) owns which files, so agents cannot overwrite each other's work or yours.
- Arbitration: when agents disagree, a human (you) makes the call. The tool never averages a disagreement into a fake consensus.
- Refusal: a structured "no" from the harness that always says what was refused, which boundary applied, and why.
- Audit: the tamper-evident log of every action in a run, which `harnessie audit` re-verifies end to end.

## Where to next

- [Getting started](getting-started.md): the same path, faster, for a terminal-comfortable reader.
- [User guide](GUIDE.md): the complete guide, from concepts to extending the harness.
- [GOVERNANCE.md](../GOVERNANCE.md): how consent, ownership, contested decisions, and the audit trail work.
- [SECURITY.md](../SECURITY.md): the prompt-injection and secret-handling model, and the sandbox backends.
