---
description: Implement, applying stage skills to matching tasks
strategy: wrap
---

## Skill bindings (standing instruction)
Before starting any task, check whether it matches a binding for the `implement` stage or one of its sub-stages: an `[E2E]` task or a task writing to `e2e/**/*.spec.ts`, a `[VULN]` task or a task editing a build or version file such as `pom.xml`, a Gradle build file, `gradle.properties` or a version catalog. When it does, run the `speckit.sdlc-skills.run` command (agents that name commands with hyphens call it `speckit-sdlc-skills-run`) with the argument `implement` for that task, which loads the matching skill before you write the code and runs its post-write checks. Do not mark the task done until those checks pass.

{CORE_TEMPLATE}
