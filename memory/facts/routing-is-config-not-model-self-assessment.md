---
name: routing-is-config-not-model-self-assessment
type: decision
source: initial architecture session 2026-07-06
date: 2026-07-06
---

# Routing is config, not model self-assessment

Workflow phases declare a task_class; config/models.yaml maps task_class to (tier, effort). We do not ask a model how hard its own task is, weak models underestimate difficulty, and orchestrators drift toward whatever tier they run on. Escalation is earned by gate failures (evidence), not predicted.
