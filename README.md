# sdlc-skills

SDLC skills for coding agents, plus one Spec Kit extension that runs them at the right stage of a feature.

Install Spec Kit in your repository, then run this repository's `speckit-extensions/install.py` from your repository's root. It adds the **engineering-build** extension, its preset, and the skills it uses. See [Install the Spec Kit extension and preset](#install-the-spec-kit-extension-and-preset).

## Repository layout

```text
sdlc-skills/
├── skills/                                  every skill, one folder each
│   ├── engineering-build/                   design, plan and build a feature; calls the companion skills
│   ├── engineering-review/                  review a whole repository (standalone)
│   ├── onboarding/                          explain a repository to new engineers (standalone)
│   ├── grill-me/                            clarify interview (companion, vendored, MIT)
│   ├── database-schema-designer/            data model design (companion, vendored, MIT)
│   ├── api-designer/                        OpenAPI contract design (companion, vendored, MIT)
│   ├── playwright-expert/                   end-to-end tests (companion, vendored, MIT)
│   └── ponytail/                            smallest complete change at implement (companion, vendored, MIT)
└── speckit-extensions/
    ├── install.py                           installs extension + preset + skills into a Spec Kit repo
    ├── catalog.json                         template entry for an internal Spec Kit catalog
    └── engineering-build/                   the Spec Kit extension
        ├── extension.yml                    commands and the 12 stage hooks
        ├── hooks.md                         rules every hook follows
        ├── commands/                        prepare-*, after-stage checks, run, edge-case-audit
        ├── config/                          binding registry
        ├── adapters/, detectors/            how each skill reads Spec Kit files; when it applies
        ├── scripts/                         lock check, Playwright rule check
        ├── skills.lock.yml                  the skills it ships, pinned by SHA-256
        ├── preset/                          the preset: wraps clarify, plan, tasks, implement
        └── docs/, tests/                    usage docs, design specs and tests (source only, not installed)
```

Each skill is stored once, in `skills/`. The extension holds no copies: at install time the installer copies the skills listed in `skills.lock.yml` into the target repository and checks their hashes.

## Which part do I need?

| I want to... | Use |
| --- | --- |
| Plan and build features with architecture, security, standards and vetted companion skills | [Install the Spec Kit extension and preset](#install-the-spec-kit-extension-and-preset), then [Use it](#use-it) |
| Add a skill to a stage (unit tests, security review) | [Add a skill to a stage](#add-a-skill-to-a-stage) |

## Install the Spec Kit extension and preset

The extension and its preset are installed together: the preset requires the extension, and the extension needs its skills staged in. `install.py` does all three in the right order.

### 1. Install Spec Kit in your repository

You need Python 3.10+, Git and the Spec Kit CLI 1.2.0 or later (`specify --version`):

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.2.0
```

Initialize your repository once for your agent:

```bash
cd /path/to/your-repo
specify init --here --integration claude
```

Use `copilot` or `codex` instead of `claude` if needed. Add `--ignore-agent-tools` if the agent's CLI is not installed (for example, you use the desktop app), and `--script ps` on Windows.

### 2. Run the installer from your repository's root

Stay in your repository's root. Clone this repository next to it (not inside it):

```bash
git clone https://github.com/nitheshrayuduv/sdlc-skills.git ../sdlc-skills
```

Preview the install. The installer changes the folder you run it from:

```bash
python ../sdlc-skills/speckit-extensions/install.py install --dry-run
```

Then install:

```bash
python ../sdlc-skills/speckit-extensions/install.py install
```

The installer:

1. Checks that the target has `.specify/` and a supported `specify` version.
2. Stages the extension with its locked skills and verifies every hash.
3. Adds the extension (`specify extension add`), then the preset (`specify preset add`, priority 5).
4. Creates `engineering-build-config.yml` only if it is missing.
5. Checks that `clarify`, `plan`, `tasks` and `implement` resolve to the preset.

Any failure restores the Spec Kit registries.

Useful options:

| Option | What it does |
| --- | --- |
| `--agent-skills .claude/skills` | Also copies every skill into your agent's skills folder, for use outside Spec Kit |
| `--profile strict` | Makes skill quality gates block a stage instead of warning |
| `--repo PATH` | Installs into another folder instead of the current one |
| `--repos-file repos.txt` | Installs into many repos, one result row each |
| `--source bundle --bundle file.zip` | Installs a release zip built with `install.py package`, offline |

### 3. Configure and verify

Restart your agent, then add the Engineering Build principle to the constitution once:

```text
/speckit-engineering-build-configure
```

Check the install:

```bash
python ../sdlc-skills/speckit-extensions/install.py verify
```

```bash
specify preset resolve speckit.plan
```

`speckit.plan` should resolve to `engineering-build-preset`.

Claude spells Spec Kit commands with hyphens (`/speckit-plan`); some agents use dots (`/speckit.plan`).

### Update or remove

```bash
python ../sdlc-skills/speckit-extensions/install.py update
```

```bash
python ../sdlc-skills/speckit-extensions/install.py uninstall
```

`update` keeps your project config and flow settings. `uninstall` leaves feature documents and constitution text in place. If you cloned this repository somewhere else, replace `../sdlc-skills` with that path. All commands and options: [speckit-extensions/README.md](speckit-extensions/README.md).

If you used the older packages, remove them before installing. The installer warns if they are still present:

```bash
specify preset remove org-sdlc
```

```bash
specify extension remove sdlc-skills --keep-config
```

```bash
specify extension remove engineering-plan
```

## Use it

Run the normal Spec Kit commands:

```text
/speckit-specify <what you want to build>
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-implement
```

Engineering Build hooks run before and after each stage. They add the architecture, diagrams, security controls, standards, traceable tasks and implementation evidence. Inside the stages, Engineering Build calls its companion skills:

| Stage | Companion skill | Runs when | Output |
| --- | --- | --- | --- |
| `clarify` | grill-me | Always | Interview answers under `## Clarifications` in `spec.md` |
| `plan` | database-schema-designer | The feature changes the data model | `data-model.md`, `db/` drafts |
| `plan` | api-designer | The feature adds or changes an API | `contracts/openapi.yaml` |
| `tasks`, `implement` | playwright-expert | A UI flow needs an `[E2E]` test | `[E2E]` tasks, Page Objects and specs, rule checks |
| `implement` | ponytail | Always, for every task | The smallest change that fully solves the task, and a note on what was skipped |

The preset calls each skill at the right point inside its stage. If the preset is missing or a call is skipped, the after-stage hooks run the skills themselves.

### See which skills ran

Every run or skip is recorded with the pinned skill version:

- `specs/<feature>/skill-runs.md` has one row per skill: ran or skipped, why, evidence and warnings.
- `plan.md` has the same decisions in a `## Skill Applicability` table.

For example, a feature that only changes UI text skips the database and API skills, and the table says why.

### Configure per repository

Override the defaults in `.specify/extensions/engineering-build/engineering-build-config.yml`, or locally in `engineering-build-config.local.yml`:

```yaml
bindings:
  - id: plan-api
    enabled: false
  - id: clarify-grill
    settings: { max_rounds: 3, interaction: one-at-a-time }
  - id: impl-minimal
    settings: { level: ultra }
```

Here `enabled: false` turns the api-designer skill off for this repository. `impl-minimal` is ponytail at implement: `lite` builds what was asked and names a smaller option, `full` (default) writes the smallest complete change, `ultra` also questions the request before coding.

When a skill's tooling is missing (for example, no network for the API lint), the stage records a warning and continues. Set `required: true` on a binding, or install with `--profile strict`, to stop the stage instead.

More detail: [extension README](speckit-extensions/engineering-build/README.md), [install](speckit-extensions/engineering-build/docs/install.md), [usage](speckit-extensions/engineering-build/docs/usage.md), [maintenance](speckit-extensions/engineering-build/docs/maintaining.md), [design spec](speckit-extensions/engineering-build/docs/specs/spec-kit-extension-spec.md).

## Add a skill to a stage

The binding registry is the extension point. Adding a skill needs no change to the wrapped commands:

1. Put the skill in `skills/<id>/` with its license. Add an entry to `speckit-extensions/engineering-build/skills.lock.yml`.
2. Write `adapters/<id>.md`: which Spec Kit files it reads, where its output goes, and its quality gate.
3. If deciding when it applies needs judgment, add `detectors/<name>.md`. It answers `yes`, `no` or `unknown`, with evidence.
4. Add a binding to `config/engineering-build-config.template.yml`. Triggers are `always`, `detect`, `task_tag`, `path_glob`, `any` and `all`.
5. Refresh the hashes and run the tests, then reinstall from your repository's root with `python ../sdlc-skills/speckit-extensions/install.py update`.

To refresh the hashes:

```bash
python speckit-extensions/engineering-build/scripts/verify_lock.py --ext speckit-extensions/engineering-build --skills skills --update
```

Any edit to a shipped skill, including `skills/engineering-build/`, needs this refresh.

## Develop and test

```bash
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```

The suite checks manifests, hooks, bindings, lock integrity, packaging, and the Playwright rule checker. It uses temporary folders and needs no network. When `specify` is on the PATH, it also runs real installs, rollback, dry-run, bulk mode and `--agent-skills`. It takes a few minutes.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `claude not found` during `specify init` | Add `--ignore-agent-tools` |
| New Spec Kit commands do not appear | Restart the agent; check `specify extension list` and `specify preset list` |
| `skill-runs.md` is missing after a stage | Check that `specify preset resolve speckit.plan` points at `engineering-build-preset`, then restart the agent |
| `hash drift` from `verify_lock.py` | A skill was edited. Restore it, or review it and refresh the hashes ([Add a skill to a stage](#add-a-skill-to-a-stage)) |
| Old `speckit-sdlc-skills-*` or `speckit-engineering-plan-*` commands still appear | Remove the older packages ([Update or remove](#update-or-remove)) |
