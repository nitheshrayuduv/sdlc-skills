---
description: Plan, then apply the database and API design skills and complete the engineering design
strategy: wrap
---

## Engineering Build: before

Read `.specify/presets/engineering-build/guide/rules.md` and follow it. When the core steps below are done, do the **Engineering Build: after** section at the end of this command before your final report.

Resolve the current feature and read spec.md, the constitution, affected code, callers, tests and repository standards. Prepare the design concerns, security controls, compatibility and rollout needs for the core planning steps below. Note the likely data-model and API impact, so the core plan drafts `data-model.md` and `contracts/` for the companion skills to review. Do not create a second plan. Apply the **Plan** guidance in the stage map.

{CORE_TEMPLATE}

## Engineering Build: after

Companion skills: once the core design artifacts exist, follow `.specify/presets/engineering-build/guide/bindings.md` for the stage `plan`. It decides whether database-schema-designer and api-designer apply, revises `data-model.md` and `contracts/`, and writes the `## Skill Applicability` table in plan.md. Build the design on their output; do not redo their work.

Then complete plan.md as the technical entry point, applying the engineering-build skill's `references/design.md` and `references/implementation.md`. Cover affected components and interfaces; end-to-end success and failure flows; relevant API/event, database/migration and frontend details; security and reliability controls; applicable repository standards and patterns; compatibility, rollout and recovery. Include a component diagram and an end-to-end sequence when they explain the change; add an ER or state diagram only when relevant. Keep Mermaid source with its explanation.

Use engineering/design.md only for detail too large for plan.md and engineering/security.md only when security needs a separate page. Keep canonical data definitions in data-model.md and API/event definitions in contracts/. Reuse research.md for technical decisions. Do not duplicate the design or repeat the requirements. Mark non-applicable areas once. Put unresolved decisions in one owning artifact with links from affected work.

Link spec.md to plan.md and plan.md to existing supporting files. Do not create tasks.md or another index here. Preserve approved choices; propose material changes rather than silently changing scope. State whether the design is ready for task generation and why.
