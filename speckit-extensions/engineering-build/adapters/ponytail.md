# Adapter: ponytail (stage `implement`)

Skill: `skills/ponytail/SKILL.md`.

## When

Binding `impl-minimal`, trigger `always`: it applies to every task of `speckit.implement`, before any other implement binding (`order: 10`). The `[E2E]` and `[VULN]` bindings still run for their tasks; ponytail decides how much code is written, they decide what a test or a version change must contain.

## How to apply it

Before writing code for a task, follow the skill's **Before you write** and **The smallest complete change** sections at the level in the binding's `settings.level` (default `full`).

Map the skill to Spec Kit:

- **Scope** is the task text in `tasks.md` plus what `spec.md`, `plan.md`, `data-model.md` and `contracts/` require for it. Everything those files ask for counts as "asked for" and is never cut, including tests the task or a companion skill requires (Page Objects for `[E2E]`, the build chain for `[VULN]`).
- **Skipped extras** (an option, abstraction or feature nobody asked for) are named in one line in the task's completion note, not built.
- **Shortcuts** with a known limit get the skill's `shortcut: <the limit>, <when to upgrade>` comment in code.
- **`ultra`** pushes back on the request: raise the doubt with the user before coding the task, and do not change `spec.md` or `tasks.md` on your own.

Session-wide behaviour in the skill (staying on until "stop ponytail", `/ponytail` level switches) does not apply here: the binding is active only while implement runs, and its level comes from the config. To turn it off for a repository, set `enabled: false` on `impl-minimal`.

## Done when

The task is complete, the callers, tests and fixtures it breaks are updated, and the completion note ends with one or two lines on what was skipped or not checked and any risk.
