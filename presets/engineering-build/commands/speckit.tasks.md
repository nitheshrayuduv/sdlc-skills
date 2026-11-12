---
description: Generate tasks, tag Playwright work as E2E, and check coverage
strategy: wrap
---

## Engineering Build: before

Read `.specify/presets/engineering-build/guide/rules.md` and follow it. When the core steps below are done, do the **Engineering Build: after** section at the end of this command before your final report.

Resolve the current feature. Read spec.md, plan.md and linked design, security, data-model and contracts. Identify requirement and control-to-task coverage and dependencies. State blocking design decisions before task generation. Preserve the repository's task syntax and IDs, and keep room for the `[E2E]` tag. Do not implement anything. Apply the **Tasks** guidance in the stage map.

{CORE_TEMPLATE}

## Engineering Build: after

Companion skills: follow `.specify/presets/engineering-build/guide/bindings.md` for the stage `tasks`, which adds or retags `[E2E]` tasks with their scenario IDs (playwright-expert).

Then check tasks.md, applying the engineering-build skill's `references/implementation.md`. Keep it as the only implementation checklist. Preserve task IDs, story labels, parallel markers, dependencies and completed statuses. Add or improve tasks for accepted requirements, security controls, schema and API compatibility, frontend behavior, negative paths, regression checks and rollout. Each task needs concrete paths, prerequisites, its requirement, design or control link and an observable done check. Record requirement-to-task-to-check coverage once in tasks.md.

Link plan.md to tasks.md. If a design decision blocks a task, record that dependency instead of inventing the answer. Report readiness for implementation.
