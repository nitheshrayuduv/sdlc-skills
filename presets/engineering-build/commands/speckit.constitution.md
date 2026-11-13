---
description: Update the constitution with the Engineering Build principle
strategy: wrap
---

## Engineering Build: before

Read `.specify/presets/engineering-build/guide/rules.md` and follow it. When the core steps below are done, do the **Engineering Build: after** section at the end of this command before your final report.

Read the existing constitution and repository guidance. Prepare the Engineering Build principle for the core constitution update below. Do not require a feature folder. Apply the **Constitution** guidance in the stage map.

{CORE_TEMPLATE}

## Engineering Build: after

If the constitution is still an unfilled template, finish the core steps above first; do not fabricate project principles.

Merge one Engineering Build principle into the constitution as part of the same update (do not increment the version a second time). Require Engineering Build at constitution, specify, clarify, plan, tasks and implement, with its companion skills applied through the binding registry; architecture and design with useful Mermaid diagrams; concrete security controls; repository standards and suitable patterns; task and check traceability; plain English and one home per topic. From the constitution file, link `../presets/engineering-build/skills/engineering-build/SKILL.md` and `../presets/engineering-build/skills/engineering-build/references/speckit.md`.

Preserve other principles and the ratification date. Re-running must not add a duplicate principle.

For a migration from an older Engineering Build install, replace only its clearly delimited `<!-- engineering-plan:start -->` to `<!-- engineering-plan:end -->` (or `engineering-build`) blocks in the constitution, AGENTS.md, CLAUDE.md and .github/copilot-instructions.md. Preserve all other text, and do not follow symlinks outside the repository. Stop if markers are duplicated, unpaired or unclear. In agent instruction files, the replacement block should only direct Spec Kit work to this preset's guide, keeping the same marker pair. Replace links to `../extensions/engineering-build/` with `../presets/engineering-build/`.

This changes guidance only. It does not install anything or execute application code.
