---
description: Check tasks against requirements, design and security
---

# Check tasks against requirements, design and security

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature. Read spec.md, plan.md, tasks.md and their linked artifacts. Apply the Tasks stage and skills/engineering-build/references/implementation.md.

Companion skills first: check `<feature_dir>/skill-runs.md` for `tasks` rows from this run. If they are missing, follow `.specify/extensions/engineering-build/commands/run.md` with the stage `tasks` now, so UI flows get `[E2E]` tasks with scenario IDs and vulnerability features get `[VULN]` tasks.

Keep tasks.md as the only implementation checklist. Preserve task IDs, story labels, parallel markers, dependencies and completed statuses. Add or improve incomplete tasks for accepted requirements, relevant security controls, schema/API compatibility, frontend behavior, negative paths, regression checks and rollout. Each task needs concrete paths, prerequisites, its requirement/design/control link and an observable done check. Record requirement-to-task-to-check coverage once in tasks.md; reference existing requirements rather than rewriting them.

Link plan.md to tasks.md. Do not create another backlog or reset completed tasks. If a design decision blocks a task, record that dependency instead of inventing the answer. Check agreement with diagrams/contracts and report readiness for implementation. Do not implement code.
