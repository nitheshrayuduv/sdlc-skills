---
description: Prepare Engineering Build guidance before implement
---

# Prepare implement

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature. Require spec.md, plan.md and tasks.md, and read their linked design, security, schema and contracts. Identify the approved tasks, required checks and repository standards before coding. If a material requirement, permission, public contract or data-loss decision is unresolved, do not authorize affected implementation. Report the blocked scope. This hook reads and assesses only; the explicitly requested core implement stage performs code edits.

Companion skills (standing instruction): every task gets ponytail (binding `impl-minimal`: the smallest complete change). Before writing code for a task, and in particular one that matches an `implement` sub-stage binding (an `[E2E]` task or Playwright spec path, a `[VULN]` task or Gradle version file), follow `.specify/extensions/engineering-build/commands/run.md` with the stage `implement` for that task, then run the skill's post-write checks. Do not mark such a task done until they pass.

Apply the **Implement** guidance in the stage map. Return a concise context/check result to the calling stage. Do not invoke another Spec Kit command.
