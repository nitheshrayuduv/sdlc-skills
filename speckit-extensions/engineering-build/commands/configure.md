---
description: Apply the Engineering Build constitution principle
---

# Apply the Engineering Build constitution principle

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Read the existing .specify/memory/constitution.md. If it does not exist or is still an unfilled template, ask the core constitution workflow to finish it; do not fabricate project principles. Do not invoke that core command yourself from this hook.

Merge one Engineering Build principle into the existing constitution. Require Engineering Build at constitution, specify, clarify, plan, tasks and implement, with its companion skills applied through the binding registry; architecture/design with useful Mermaid diagrams; concrete security controls; repository standards and suitable patterns; task/check traceability; plain English and one home per topic. Reference `.specify/extensions/engineering-build/skills/engineering-build/SKILL.md` and `skills/engineering-build/references/speckit.md` under that extension. From the constitution file, the Markdown links are `../extensions/engineering-build/skills/engineering-build/SKILL.md` and `../extensions/engineering-build/skills/engineering-build/references/speckit.md`.

Preserve other principles. Reconcile the version/date and sync impact report following the repository’s constitution rules. When running as after_constitution, fold this into the same logical constitution update rather than blindly incrementing a second time. Retain the ratification date. Re-running must not add duplicate principles.

For a migration from the older skill installer, replace only its clearly delimited `<!-- engineering-plan:start -->` to `<!-- engineering-plan:end -->` (or `engineering-build`) blocks in the constitution, AGENTS.md, CLAUDE.md and .github/copilot-instructions.md. Preserve all other text, and do not follow symlinks outside the repository. Stop if markers are duplicated, unpaired or their boundaries are unclear. In agent instruction files, the replacement block should only direct Spec Kit work to the installed extension guide, keeping this same marker pair. In the constitution, the block can own the single principle. Do not delete the standalone skill or other extensions. Confirm the old engineering-plan extension and org-sdlc preset have been removed before describing the migration as complete.

This command changes guidance only. It does not install extensions, change integration settings or execute application code.
