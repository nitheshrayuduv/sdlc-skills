# Spec Kit stages

## One feature, one set of documents

Use the feature directory identified by the installed Spec Kit scripts. Never guess the feature from the most recent folder. Read the existing constitution and artifacts before changing them. Preserve the local Spec Kit command, scripts, IDs and document format.

| File | Owns this information |
| --- | --- |
| spec.md | User needs, behavior, acceptance criteria, scope and product questions |
| plan.md | Technical approach, affected code, standards/patterns, constitution check, rollout and links |
| tasks.md | The only implementation checklist, task IDs, dependencies, requirement links and test/done conditions |
| research.md | Important options, decisions and unresolved technical questions, if needed |
| data-model.md | Proposed data model/schema changes, if applicable |
| contracts/ | API/event contracts, if applicable |
| engineering/design.md | Detailed component and flow diagrams and explanations too large for plan.md |
| engineering/security.md | Feature risks, controls and their verification |
| engineering/validation.md | Checks actually run during implementation, results and remaining gaps |

Create supporting files only when useful. Keep small designs/security sections in plan.md instead. Retain Spec Kit's other useful files such as quickstart.md; link them. Do not repeat schema or contract definitions in design.md. Do not repeat requirements in a separate README or tasks in implementation.md. Use relative links from spec.md to plan.md, from plan.md to tasks.md and its supporting files, and from tasks to the section they implement. Only add links once the target exists.

## Apply the skill at every stage

**Constitution:** Incorporate a mandatory Engineering Build principle in .specify/memory/constitution.md. When the extension is installed, reference .specify/extensions/engineering-build/skills/engineering-build/SKILL.md and its references/speckit.md stage map. Otherwise reference .agents/skills/engineering-build/SKILL.md and this stage map. Use relative Markdown links when adding hyperlinks. Preserve other principles. Follow Spec Kit's constitution version/date and sync-report rules. Ensure the downstream command/template instructions retain the principle.

**Specify and clarify:** At clarify, the grill-me companion skill interviews the user first, in rounds, with edge-case lenses; record its answers under `## Clarifications`. Then use this skill to ask about boundaries, affected users, compatibility, sensitive data and observable success. Keep spec.md focused on what and why; do not force design choices into a product specification. Record requirements once using the existing IDs. Technical options belong to plan/research later. State unresolved product decisions rather than fabricating agreement.

**Plan:** Inspect affected code, callers, tests and standards. Make the architecture, design, diagrams, migration/API/UI changes, patterns, security and rollout concrete. Use plan.md as the technical entry point. Reuse Spec Kit research.md, data-model.md and contracts/ when applicable. After the core design draft exists, let the database-schema-designer and api-designer companion skills review it when the feature changes the data model or an API, and record each decision (including skips) in `## Skill Applicability`. State the constitution check and blocking decisions honestly. Link spec.md to the plan after it exists. Do not write a duplicate full plan in docs/plans.

**Tasks:** Convert the approved design into the existing tasks.md syntax, retaining T001-style IDs and story/parallel markers. Each task needs relevant file paths, prerequisites, a link to its requirement/design/control, and an observable completion check. Put the requirement-to-task-to-check table here once. Link plan.md to tasks.md. Make security, migration, compatibility, negative-path and regression checks explicit where needed. Tag browser end-to-end work `[E2E]` with its scenario ID (playwright-expert) and vulnerability fixes `[VULN]` per repo.

**Implement:** Read spec.md, plan.md, tasks.md and linked design/security/contracts before coding. Follow the approved tasks, patterns and standards. Apply the ponytail companion skill to every task: the smallest change that fully solves it. For `[E2E]` and `[VULN]` tasks, load the matching companion skill before writing the code and run its post-write checks. Record actual verification in engineering/validation.md only when implementation starts. Mark tasks done only with evidence. If implementation changes a requirement, public contract, permission model or data-loss risk, update the owning artifact and resolve the decision before proceeding with the affected work. Fix safe details and keep unaffected work moving. Do not invent test results. Link tasks.md to verification evidence rather than duplicating the results in every document.

## Keep automatic use explicit

Prefer the native extension and preset in [Extension integration](extension.md). The preset calls the companion-skill runner inside clarify, plan, tasks and implement. The extension's before hooks prepare stage context; its after hooks reconcile the owning artifacts and run any companion-skill bindings the preset did not. The manifest uses optional: false with no conditional expressions for all twelve hooks. Installation registers them with Spec Kit; it does not by itself update an existing constitution. Run the extension’s configure command after installation. Later constitution updates run that same action automatically.

Verify both hook registration and the installed agent’s core command files after installation or upgrades. Those files must dispatch before and after hooks for all six stages. An old generated command or a project override can omit them even when an extension is installed. Never claim automatic use from manifest presence alone.

Do not keep the older engineering-plan extension or org-sdlc preset active next to this one. Preserve a separately installed standalone skill for non-Spec-Kit planning if useful.
