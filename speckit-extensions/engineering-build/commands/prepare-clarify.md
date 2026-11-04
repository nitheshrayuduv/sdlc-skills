---
description: Prepare Engineering Build guidance before clarify
---

# Prepare clarify

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature using the installed Spec Kit prerequisite script in paths-only mode. Read spec.md and focus clarification on missing behavior, boundaries, compatibility, sensitive data and acceptance criteria. Feed unresolved questions to the core clarification step; do not answer them by assumption.

Companion skill: the `clarify-grill` binding runs the grill-me interview before the core clarify steps. The preset normally runs it just before this hook. If `<feature_dir>/skill-runs.md` has no `clarify` row from this run, follow `.specify/extensions/engineering-build/commands/run.md` with the stage `clarify` now, so the core gap scan sees the answers.

Apply the **Clarify** guidance in the stage map. Return a concise context/check result to the calling stage. Do not invoke another Spec Kit command.
