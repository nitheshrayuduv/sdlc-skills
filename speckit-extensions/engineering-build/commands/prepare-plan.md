---
description: Prepare Engineering Build guidance before plan
---

# Prepare plan

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature and read spec.md, the constitution, affected code, callers, tests and repository standards. Prepare the design concerns, security controls, compatibility and rollout needs for the core planning step. Do not overwrite artifacts or create a second plan. The design post-hook will complete and check the resulting artifacts.

Companion skills: after the core design step, the `plan` bindings decide whether database-schema-designer and api-designer apply (and engineering-vulnerability-upgrade, when `vuln/intake.json` exists). Note the likely data-model and API impact now, so the core plan drafts `data-model.md` and `contracts/` the skills will review.

Apply the **Plan** guidance in the stage map. Return a concise context/check result to the calling stage. Do not invoke another Spec Kit command.
