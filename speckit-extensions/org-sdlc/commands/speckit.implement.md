---
description: Implement, applying stage skills to matching tasks
strategy: wrap
---

## Skill bindings (standing instruction)
Before starting any task, check whether it matches a binding for the `implement` stage (for example an `[E2E]` task, or a task writing to `e2e/**/*.spec.ts`). When it does, run the `speckit.sdlc-skills.run` command (agents that name commands with hyphens call it `speckit-sdlc-skills-run`) with the argument `implement.e2e-test` for that task, which loads the skill before you write the code, and run its post-write checks before marking the task done.

{CORE_TEMPLATE}
