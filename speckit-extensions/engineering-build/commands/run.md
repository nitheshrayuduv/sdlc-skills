---
description: Apply the skill bindings for a stage
---

# Run skill bindings for a stage

Argument: `$ARGUMENTS` is the stage name, one of `clarify`, `plan`, `tasks`, `implement`, `analyze`, `checklist`, or a sub-stage such as `implement.e2e-test`. If it is empty, stop and say which stages exist.

The extension lives in `.specify/extensions/engineering-build/`. Call that folder `EXT`. Skills are instructions you follow, read as plain files, so this works on any agent. Never fetch a skill from the network.

## 1. Load the registry

Merge these layers, later ones winning, matching bindings by `id`:

1. `EXT/config/engineering-build-config.template.yml` (shipped defaults)
2. `EXT/engineering-build-config.yml` (project)
3. `EXT/engineering-build-config.local.yml` (local, if present)
4. Environment variables `SPECKIT_ENGINEERING_BUILD_*`, for example `SPECKIT_ENGINEERING_BUILD_PLAN_DB_ENABLED=false`

Select bindings whose `stage` equals the argument. When the argument is a core stage (no dot), also select sub-stages that start with it plus a dot, for example `implement.e2e-test`. Drop bindings with `enabled: false`; record each as `skipped: disabled`. Order by `order` (default 100), and make sure every binding runs after the ids in its `depends_on`.

## 2. Verify the pinned skills

Run `python EXT/scripts/verify_lock.py --ext EXT`. If it exits non-zero, a vendored skill has drifted from `skills.lock.yml`. Stop, report which skill, and do not apply any skill. This is never downgraded to a warning.

## 3. Apply each binding

For each binding in order:

1. **Trigger.** Evaluate it:
   - `always`: run.
   - `detect`: read `EXT/detectors/<detector>.md`, follow it, and get `yes`, `no` or `unknown` plus quoted evidence. On `unknown` with `ask_if_unknown: true`, ask the user exactly one question, then treat their answer as the result and record it. Without that flag, `unknown` means skip with a warning.
   - `task_tag`: run only for tasks that carry the tag, for example `[E2E]`.
   - `path_glob`: run only for tasks that write to a matching path.
   - `any` / `all`: combine the nested `of` triggers.
2. **Apply.** If the trigger fired, read `EXT/adapters/<skill>.md` and `EXT/skills/<skill>/SKILL.md` (for `grill-me`, `EXT/skills/grill-me/grilling.md`), then follow the adapter. The adapter says how Spec Kit artifacts map to the skill's inputs and where results go. The skill itself is never edited.
3. **Failure handling.** If the skill's tooling is missing (no `npx`, no network, no database) record a warning and continue. If the binding or `defaults` sets `required: true`, stop the stage instead.
4. **Record.** Append a row to the run ledger and, for `plan`, to the Skill Applicability table (below).

## 4. Record every run and skip

Auditability is a requirement: every run or skip must be traceable to a decision and a pinned skill version.

- Ledger: `<feature_dir>/skill-runs.md`, a table with the columns `Date | Stage | Binding | Skill | Skill version | Decision | Evidence | Outputs | Warnings`. Take the skill version as the `commit` from `EXT/skills.lock.yml`. The decision is `ran`, `skipped: <reason>` or `failed`.
- Plan table: under `## Skill Applicability` in `plan.md`, keep one row per binding with the same decision and evidence, including skips.
- Re-running updates the existing row for that binding and stage instead of adding a duplicate. Re-running must never duplicate a section either.

`<feature_dir>` is the active feature directory, usually `specs/<feature>/`.

## Rules

- Do not silently skip a binding: a skip needs a recorded reason.
- Do not change core Spec Kit files or the vendored skills.
- Keep going after a skill's warning; stop only on `required: true`, a failed lock check, or an explicit user stop.
