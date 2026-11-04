# Adapter: playwright-expert (stages `tasks` and `implement.e2e-test`)

Skill: `skills/playwright-expert/SKILL.md` and its `references/`.

## In `tasks` (binding `tasks-e2e`, detector `ui_flows`)

Run the skill's first step, identify user flows to test, against the acceptance scenarios in `spec.md`. Emit one task per flow, tagged `[E2E]`, with the scenario ID in the task text, for example `- [ ] T012 [E2E] Cover US1-AS2: checkout with expired card`. Update existing `[E2E]` tasks instead of duplicating them. If the repo has no Playwright config, emit a setup task first.

## In `implement` (binding `impl-e2e`)

For every `[E2E]` task, and any task whose target path matches the binding's globs, load the skill before writing code and follow its workflow: configure, write with Page Objects, debug, wire into CI. Deliverables: Page Object classes, test files with assertions, fixtures when needed, configuration recommendations. If `contracts/openapi.yaml` exists, its examples may serve as route-mock payloads, following `references/api-mocking.md`.

Every test title includes its scenario ID, for example `US1-AS2 rejects an expired card`, so coverage of `spec.md` can be audited.

## Rules enforced after writing

Run `python .specify/extensions/engineering-build/scripts/check_playwright_rules.py <files...> --config playwright.config.ts`. It exits non-zero when a failing rule is hit.

| Rule from the skill | Check | Severity |
| --- | --- | --- |
| No `waitForTimeout()` | Pattern search | Fails the task |
| No CSS-class selectors | Pattern search for class-based locators | Fails the task |
| `first()` and `nth()` only with a reason | Needs an adjacent comment | Fails the task |
| Role-based selectors preferred | Reported as a ratio | Warning |
| Independent tests, no shared state | Run with `--repeat-each=2` (and random order when supported) | Warning |
| Traces and screenshots on failure | Verified in `playwright.config.ts` | Warning |
| Parallel execution | `fullyParallel` verified in `playwright.config.ts` | Warning |

## Done when

The new tests run green once locally, or the failure is recorded as a warning with the reason (FR-9). Do not mark an `[E2E]` task complete while a failing rule remains.
