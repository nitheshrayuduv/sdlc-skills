# engineering-build (Spec Kit extension + preset)

Engineering Build across the whole Spec Kit workflow: architecture, design and diagrams, security controls, standards, traceable tasks and implementation evidence. It calls pinned companion skills at the stage where each applies, as set out in [docs/specs/spec-kit-extension-spec.md](docs/specs/spec-kit-extension-spec.md).

| Stage | Engineering Build hook | Companion skill (binding) | Runs when |
| --- | --- | --- | --- |
| constitution | `prepare-constitution`, `configure` | | |
| specify | `prepare-specify`, `spec-check` | | |
| clarify | `prepare-clarify`, `spec-check` + edge-case audit | grill-me (`clarify-grill`) | Always |
| plan | `prepare-plan`, `design` | database-schema-designer (`plan-db`) | Detector `db_change` says yes |
| plan | | api-designer (`plan-api`) | Detector `api_change` says yes |
| tasks | `prepare-tasks`, `task-check` | playwright-expert (`tasks-e2e`) | Detector `ui_flows` says yes |
| implement | `prepare-implement`, `verify` | ponytail (`impl-minimal`) | Always, for every task (level in `settings.level`) |
| implement | | playwright-expert (`impl-e2e`) | `[E2E]` task, or a matching test path |
| plan, tasks, implement | | engineering-vulnerability-upgrade (`*-vuln-upgrade`) | Detector `vuln_report` says yes, or a `[VULN]` task |

## How the pieces fit

- **Extension** (this folder): twelve mandatory before/after hooks, the binding runner `speckit.engineering-build.run <stage>`, adapters, detectors and the binding registry.
- **Preset** (`preset/`, id `engineering-build-preset`): wraps clarify, plan, tasks and implement so the runner is called at the exact point inside each stage. Hooks can only run before or after a command, so the preset is what puts the database and API review after the core design draft.
- **Skills**: not stored here. They live once in the repository's top-level [`skills/`](../../skills) folder. `skills.lock.yml` names the ones this extension ships and pins each by commit and SHA-256. The installer copies exactly those into `.specify/extensions/engineering-build/skills/` at install time.

If the preset is missing or an agent skips a wrapped step, the after hooks (`design`, `task-check`, `verify`) and `prepare-clarify` notice the missing rows in `skill-runs.md` and run the bindings themselves, so the companion skills still run.

## Layout

| Path | What it holds |
| --- | --- |
| `extension.yml` | Commands and hooks |
| `hooks.md` | Rules every hook follows, and the companion-skill table |
| `commands/` | `prepare-*` and the after hooks; `run`, `edge-case-audit`, `vuln-intake`, `vuln-pr` |
| `config/engineering-build-config.template.yml` | The binding registry. Project overrides go in `.specify/extensions/engineering-build/engineering-build-config.yml` or `.local.yml` |
| `config/vuln-flows.json` | Repo chains and build settings for the vulnerability upgrade |
| `adapters/`, `detectors/` | Glue between Spec Kit artifacts and each skill, and the yes/no/unknown applicability checks |
| `skills.lock.yml` | Pinned skills: source, commit, license, SHA-256 |
| `scripts/` | `verify_lock.py`, `check_playwright_rules.py`, `vuln/` |
| `preset/` | The preset (installed separately by the installer) |
| `docs/`, `tests/` | Source-only; excluded from the install by `.extensionignore` |

## Install

Install Spec Kit in the target repository first (`specify init`). Then, from the target repository's root, with sdlc-skills cloned next to it:

```bash
python ../sdlc-skills/speckit-extensions/install.py install --dry-run
python ../sdlc-skills/speckit-extensions/install.py install
```

Then run `/speckit-engineering-build-configure` once in your agent. Details: [docs/install.md](docs/install.md). Day-to-day use: [docs/usage.md](docs/usage.md). Changing skills or releasing: [docs/maintaining.md](docs/maintaining.md).

## Audit trail

Every companion-skill run or skip is written to `specs/<feature>/skill-runs.md`, and `plan.md` gets a `## Skill Applicability` table with the evidence for each decision.

## Tests

From the sdlc-skills repository root:

```bash
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```
