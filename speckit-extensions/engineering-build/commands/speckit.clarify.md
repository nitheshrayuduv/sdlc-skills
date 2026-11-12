---
description: Clarify with the grill-me interview first, then audit edge cases
strategy: wrap
---

## Engineering Build: before

Read `.specify/presets/engineering-build/guide/rules.md` and follow it. When the core steps below are done, do the **Engineering Build: after** section at the end of this command before your final report.

Resolve the current feature and read spec.md. Focus clarification on missing behavior, boundaries, compatibility, sensitive data and acceptance criteria. Apply the **Clarify** guidance in the stage map.

Companion skills: follow `.specify/presets/engineering-build/guide/bindings.md` for the stage `clarify` now. The `clarify-grill` binding runs the grill-me interview and writes the answers into spec.md, so the core gap scan below sees them. Do not answer questions by assumption.

{CORE_TEMPLATE}

## Engineering Build: after

Check spec.md for scope, compatibility, sensitive data and measurable acceptance criteria. Preserve IDs and accepted decisions. Do not invent answers or create plan.md or tasks.md.

Then follow `.specify/presets/engineering-build/guide/edge-case-audit.md`, which checks every edge-case lens from the grill-me binding is answered or marked N/A. It is advisory and never blocks.

Report remaining decisions and the next valid stage in plain English.
