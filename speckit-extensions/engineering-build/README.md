# engineering-build (Spec Kit preset)

Engineering Build across the whole Spec Kit workflow: architecture, design and diagrams, security controls, standards, traceable tasks and implementation evidence. It calls pinned companion skills at the stage where each applies, as set out in [docs/specs/spec-kit-extension-spec.md](docs/specs/spec-kit-extension-spec.md).

It is one preset. It wraps the six core commands with `strategy: wrap`: an **Engineering Build: before** section runs before the core steps and an **Engineering Build: after** section runs once they are done. No extension or hooks are needed.

| Command | Before the core steps | After the core steps | Companion skill (binding) | Runs when |
| --- | --- | --- | --- | --- |
| constitution | Prepare the principle | Merge the Engineering Build principle | | |
| specify | Carry goals and constraints | Check scope and acceptance criteria | | |
| clarify | Run the clarify bindings | Spec check and edge-case audit | grill-me (`clarify-grill`) | Always |
| plan | Note data and API impact | Run the plan bindings, then complete the design | database-schema-designer (`plan-db`) | Detector `db_change` says yes |
| plan | | | api-designer (`plan-api`) | Detector `api_change` says yes |
| tasks | Check coverage inputs | Run the tasks bindings, then check tasks | playwright-expert (`tasks-e2e`) | Detector `ui_flows` says yes |
| implement | Standing instruction: bindings per task | Record evidence in `validation.md` | ponytail (`impl-minimal`) | Always, for every task (level in `settings.level`) |
| implement | | | playwright-expert (`impl-e2e`) | `[E2E]` task, or a matching test path |

## Layout

| Path | What it holds |
| --- | --- |
| `preset.yml` | The six wrapped commands |
| `commands/` | The wraps; `{CORE_TEMPLATE}` marks where the core steps go |
| `guide/rules.md` | Rules every wrapped command follows, and the companion-skill table |
| `guide/bindings.md` | How to apply a stage's bindings: merge the registry, check the lock, run triggers, adapters, record |
| `guide/edge-case-audit.md` | The advisory audit after clarify |
| `bindings.yml` | The binding registry (shipped defaults). Projects override it in `.specify/engineering-build.yml` or `.specify/engineering-build.local.yml` |
| `adapters/`, `detectors/` | Glue between Spec Kit artifacts and each skill, and the yes/no/unknown applicability checks |
| `skills.lock.yml` | Pinned skills: source, commit, license, SHA-256 |
| `scripts/` | `verify_lock.py`, `check_playwright_rules.py` |
| `docs/`, `tests/` | Source-only; left out of the install by `.presetignore` |

**Skills** are not stored here. They live once in the repository's top-level [`skills/`](../../skills) folder. `skills.lock.yml` names the ones this preset ships and pins each by commit and SHA-256. The installer copies exactly those into the staged preset, so they end up in `.specify/presets/engineering-build/skills/`.

## Install

Install Spec Kit in the target repository first (`specify init`). Then, from the target repository's root, with sdlc-skills cloned next to it:

```bash
python ../sdlc-skills/speckit-extensions/install.py install --dry-run
python ../sdlc-skills/speckit-extensions/install.py install
```

Then run `/speckit-constitution` once in your agent if the repository already has a constitution. Details: [docs/install.md](docs/install.md). Day-to-day use: [docs/usage.md](docs/usage.md). Changing skills or releasing: [docs/maintaining.md](docs/maintaining.md).

## Audit trail

Every companion-skill run or skip is written to `specs/<feature>/skill-runs.md`, and `plan.md` gets a `## Skill Applicability` table with the evidence for each decision.

## Tests

From the sdlc-skills repository root:

```bash
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```
