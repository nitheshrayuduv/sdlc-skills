---
description: Implement with the smallest complete change per task, E2E rules, and recorded evidence
strategy: wrap
---

## Engineering Build: before

Read `.specify/presets/engineering-build/guide/rules.md` and follow it. When the core steps below are done, do the **Engineering Build: after** section at the end of this command before your final report.

Resolve the current feature. Require spec.md, plan.md and tasks.md, and read their linked design, security, schema and contracts. Identify the approved tasks, required checks and repository standards before coding. If a material requirement, permission, public contract or data-loss decision is unresolved, do not implement the affected tasks; report the blocked scope. Apply the **Implement** guidance in the stage map.

Companion skills (standing instruction for every task below): before writing code for a task, follow `.specify/presets/engineering-build/guide/bindings.md` for the stage `implement` for that task. Every task gets ponytail (binding `impl-minimal`: the smallest complete change). An `[E2E]` task, or a task writing to `e2e/**/*.spec.ts`, also gets playwright-expert, whose post-write checks must pass before the task is marked done.

{CORE_TEMPLATE}

## Engineering Build: after

Write or update engineering/validation.md with the checks actually run, their commands, observed results, requirement and task links, and remaining gaps. A plan to run a test is not a test result. Do not install dependencies, access production, run migrations against live data, deploy or publish anything here.

Compare implemented behavior with requirements, contracts, diagrams, patterns and security controls. Leave incomplete tasks unchecked; never mark a task done merely because code exists. Confirm every `[E2E]` task has an `implement` row in `<feature_dir>/skill-runs.md` with its post-write checks. Link tasks.md to the validation evidence.

Report completed scope, blocked work and validation gaps honestly.
