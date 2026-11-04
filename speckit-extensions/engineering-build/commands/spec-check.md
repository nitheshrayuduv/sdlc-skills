---
description: Check feature scope and acceptance criteria
---

# Check feature scope and acceptance criteria

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Use the feature directory returned by the core specify/clarify command. If invoked manually, resolve it through the installed Spec Kit prerequisite script in paths-only mode. Never choose the newest folder.

Read spec.md. Check user needs, scope, compatibility, sensitive data and measurable acceptance criteria against the request and source evidence. Preserve IDs and accepted decisions. Improve wording and simple links in spec.md where meaning is unchanged. Record unresolved product questions in its existing clarification area. Do not invent answers, impose architecture, or create plan.md/tasks.md during specification. Link to plan.md only if it already exists. Do not create a separate engineering specification.

After clarify only: also follow `.specify/extensions/engineering-build/commands/edge-case-audit.md`, which checks every edge-case lens from the grill-me binding is answered or marked N/A. It is advisory and never blocks.

Report remaining decisions and the next valid stage in plain English. Do not label the specification ready while a material product decision is unresolved.
