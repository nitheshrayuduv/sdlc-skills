---
description: Prepare Engineering Build guidance before tasks
---

# Prepare tasks

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature. Read spec.md, plan.md and linked design, security, data-model and contracts. Identify requirement/control-to-task coverage and dependencies. State blocking design decisions before task generation. Preserve the repository’s task syntax and IDs. Do not implement anything.

Companion skills: after task generation, the `tasks` bindings add `[E2E]` tasks per UI flow (playwright-expert) and `[VULN]` tasks per repo (engineering-vulnerability-upgrade). Keep room for those tags in the task syntax.

Apply the **Tasks** guidance in the stage map. Return a concise context/check result to the calling stage. Do not invoke another Spec Kit command.
