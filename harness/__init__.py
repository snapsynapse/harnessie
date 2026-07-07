"""Harnessie, a brain-agnostic multi-agent harness.

Subsystem map (each module is one explicit boundary):

    models/       ModelInterface + provider adapters (Anthropic, OpenAI-compatible, mock)
    tools/        ToolRegistry: single source of truth for capabilities AND policy
    loop.py       AgentLoop: goal -> context -> model -> permission gate -> tool -> repeat
    verify.py     VerificationGate: deterministic checks + model verifier + retry ladder
    routing.py    Routing policy: task tier -> (model, effort), escalation ladder, budgets
    memory.py     Project memory (markdown facts w/ provenance) + proof artifacts
    state.py      Run journal (JSONL) for resumability and audit
    roles.py      Role definitions (orchestrator / worker / verifier) loaded from agents/
    quarantine.py Prompt-injection ingress filter + secret detection/redaction
    sandbox.py    OS confinement of child commands (workspace-only writes, network deny)
    ownership.py  Ownership lanes: agents own their files, never each other's
    adversarial.py Contested phases: positions, objections, decision records, lint
    audit.py      Hash-chain verification + governance timeline for any run
    runner.py     WorkflowRunner: executes workflows/*.yaml phase by phase through gates
    events.py     Structured, hash-chained event log shared by everything above

Security model: SECURITY.md. Architecture and source map: ARCHITECTURE.md.
Governance layer (consent, ownership, contest, audit): GOVERNANCE.md.
"""

__version__ = "0.5.0"
