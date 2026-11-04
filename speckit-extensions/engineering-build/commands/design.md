---
description: Complete the feature architecture and engineering design
---

# Complete the feature architecture and engineering design

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature and read spec.md, plan.md, the constitution and the affected source. Apply the Plan stage in the stage map, plus skills/engineering-build/references/design.md and skills/engineering-build/references/implementation.md.

Companion skills first: check `<feature_dir>/skill-runs.md` for `plan` rows from this run. If they are missing, follow `.specify/extensions/engineering-build/commands/run.md` with the stage `plan` now. It decides whether database-schema-designer and api-designer apply, revises `data-model.md` and `contracts/openapi.yaml`, and writes the `## Skill Applicability` table. Build the design on their output; do not redo their work.

Complete the existing plan.md as the technical entry point. Cover affected components and interfaces; end-to-end success and failure flows; relevant API/event, database/migration and frontend details; security/reliability controls; applicable repository standards and patterns; compatibility, rollout and recovery. Include a component diagram and an end-to-end sequence when they explain the change; add an ER/state diagram only when relevant. Keep Mermaid source with its explanation.

Use engineering/design.md only for detail too large for plan.md and engineering/security.md only when security needs a separate page. Keep canonical data definitions in data-model.md and API/event definitions in contracts/ when those exist. Reuse research.md for technical decisions. Do not duplicate the same design in several places or repeat the requirements. Mark non-applicable areas once. Put unresolved decisions in one owning artifact with links from affected work.

Add simple relative links from spec.md to plan.md and from plan.md to existing supporting files. Do not create tasks.md, implementation.md, docs/plans or another index in this stage. Preserve existing approved choices; propose material changes and obtain their resolution rather than silently changing scope. State whether the design is ready for task generation and why.
