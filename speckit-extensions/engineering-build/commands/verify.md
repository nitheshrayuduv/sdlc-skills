---
description: Record implementation evidence and remaining gaps
---

# Record implementation evidence and remaining gaps

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Resolve the current feature. Read spec.md, plan.md, tasks.md, linked design/security/contracts and the implementation changes. Apply the Implement stage and skills/engineering-build/references/implementation.md.

Write or update engineering/validation.md with checks actually run, commands or methods, observed results, requirement/task links and remaining gaps. A plan to run a test is not a test result. Run only relevant local checks already authorized by the implementation request, after inspecting the commands. Do not install dependencies, access production, run migrations against live data, deploy or publish anything through this hook.

Compare implemented behavior with requirements, contracts, diagrams, patterns and security controls. Update owning documentation for agreed implementation details without silently approving requirement or security changes. Leave incomplete tasks unchecked; never mark a task done merely because code exists. Link tasks.md to validation evidence. Do not copy results into several files, start unrelated fixes or convert this into a whole-codebase review. Companion skills: confirm every `[E2E]` and `[VULN]` task has an `implement` row in `<feature_dir>/skill-runs.md` with its post-write checks. If `<feature_dir>/vuln/intake.json` exists, finish by following `.specify/extensions/engineering-build/commands/vuln-pr.md`, which asks before pushing anything.

Report completed scope, blocked work and validation gaps honestly.
