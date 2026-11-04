# sdlc-skills

SDLC skills for coding agents, plus one Spec Kit extension that runs them at the right stage of a feature.

You install Spec Kit in your own repository, then run `installer/install.py` from this repository. That adds the **engineering-build** extension, its preset, and the skills it uses.

## Repository layout

```text
sdlc-skills/
├── skills/                                  every skill, one folder each
│   ├── engineering-build/                   design, plan and build a feature; calls the companion skills
│   ├── engineering-review/                  review a whole repository (standalone)
│   ├── onboarding/                          explain a repository to new engineers (standalone)
│   ├── engineering-vulnerability-upgrade/   fix vulnerable Gradle versions from an Agility ticket (companion)
│   ├── grill-me/                            clarify interview (companion, vendored, MIT)
│   ├── database-schema-designer/            data model design (companion, vendored, MIT)
│   ├── api-designer/                        OpenAPI contract design (companion, vendored, MIT)
│   ├── playwright-expert/                   end-to-end tests (companion, vendored, MIT)
│   └── ponytail/                            smallest complete change at implement (companion, vendored, MIT)
├── speckit-extensions/
│   └── engineering-build/                   the Spec Kit extension
│       ├── extension.yml                    commands and the 12 stage hooks
│       ├── hooks.md                         rules every hook follows
│       ├── commands/                        prepare-*, after-stage checks, run, vuln-intake, vuln-pr
│       ├── config/                          binding registry, example vuln-flows.json
│       ├── adapters/, detectors/            how each skill reads Spec Kit files; when it applies
│       ├── scripts/                         lock check, Playwright rule check, vulnerability scripts
│       ├── skills.lock.yml                  the skills it ships, pinned by SHA-256
│       ├── preset/                          wraps clarify, plan, tasks, implement
│       └── docs/, tests/                    source only, not installed
├── installer/install.py                     installs extension + preset + skills into a repo
├── docs/specs/                              design specs
└── catalog/                                 template entry for an internal Spec Kit catalog
```

Each skill is stored once, in `skills/`. The extension holds no copies. At install time the installer copies the skills listed in `skills.lock.yml` into the target repository and checks their hashes.

## Which part do I need?

| I want to... | Use |
| --- | --- |
| Plan and build features with architecture, security, standards and vetted companion skills | Engineering Build in Spec Kit (sections 1 to 3) |
| Fix vulnerable Gradle versions listed in an Agility ticket | The vulnerability workflow (section 4) |
| Review a repository, or explain one to new engineers | `engineering-review` or `onboarding` on their own (section 5) |
| Add a skill to a stage (unit tests, security review) | The binding registry (section 6) |

## 1. Install Spec Kit in your repository

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

## 2. Install Engineering Build

From a clone of this repository, kept outside your repository:

```bash
python installer/install.py install --repo /path/to/your-repo --dry-run
```

```bash
python installer/install.py install --repo /path/to/your-repo
```

The installer:

1. Checks that the target has `.specify/` and a supported `specify` version.
2. Stages the extension with its locked skills and verifies every hash.
3. Adds the extension, then the preset (priority 5).
4. Creates `engineering-build-config.yml` only if it is missing.
5. Checks that `clarify`, `plan`, `tasks` and `implement` resolve to the preset.

Any failure restores the Spec Kit registries.

Useful options:

| Option | What it does |
| --- | --- |
| `--agent-skills .claude/skills` | Also copies every skill into your agent's skills folder, for use outside Spec Kit |
| `--flows-config FILE` | Installs your team's vulnerability flow file (section 4) |
| `--profile strict` | Makes skill quality gates block a stage instead of warning |
| `--repos-file repos.txt` | Installs into many repos, one result row each |

Other commands are `update`, `verify`, `status`, `uninstall` and `package`. Details are in [installer/README.md](installer/README.md).

Restart your agent, then add the Engineering Build principle to the constitution once:

```text
/speckit-engineering-build-configure
```

Claude spells Spec Kit commands with hyphens (`/speckit-plan`); some agents use dots (`/speckit.plan`).

If you used the older packages, remove them first. The installer warns if they are still present:

```bash
specify preset remove org-sdlc
```

```bash
specify extension remove sdlc-skills --keep-config
```

```bash
specify extension remove engineering-plan
```

## 3. Use it

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
| `plan`, `tasks`, `implement` | engineering-vulnerability-upgrade | A vulnerability ticket drives the feature | Section 4 |

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

More detail: [extension README](speckit-extensions/engineering-build/README.md), [install](speckit-extensions/engineering-build/docs/install.md), [usage](speckit-extensions/engineering-build/docs/usage.md), [maintenance](speckit-extensions/engineering-build/docs/maintaining.md).

## 4. Vulnerability upgrade from an Agility ticket

This workflow fixes vulnerable Gradle dependency versions listed in an Agility ticket, across a chain of repositories. Scripts do the exact work; the agent asks questions and reads the results. Design: [engineering-vulnerability-upgrade-spec.md](docs/specs/engineering-vulnerability-upgrade-spec.md).

### Your flow file

All repository knowledge lives in `vuln-flows.json`:

- which **flows** exist, and the repos of each in build order;
- the **platform repo** that holds shared versions, and its reference paths;
- the **handoff** rules: which later repos pin a repo's version, in which file and key.

The copy in this repository (`speckit-extensions/engineering-build/config/vuln-flows.json`) is a neutral example with one flow: `shared-lib`, then `service-a` and `service-b`.

Keep your team's real file outside this public repository. A git-ignored `private/` folder in your clone works. Then pass it at install time. `update` keeps the project's flows afterwards.

```bash
python installer/install.py install --repo /path/to/your-repo --flows-config /path/to/vuln-flows.json
```

The format is in [flows.md](skills/engineering-vulnerability-upgrade/references/flows.md).

### One-time setup

1. Install Engineering Build into the repo you will run from, usually the first repo of the chain, with `--flows-config`.
2. Check out every repo of the flow under one folder, set as `workspace_root`. The tool never clones.
3. Set the Agility connection in your shell, never in a file:

```powershell
$env:AGILITY_TOKEN = "<your Agility token>"
$env:AGILITY_URL   = "https://<your-agility-host>/<instance>"
```

### Run it

| Step | Command | What happens |
| --- | --- | --- |
| 1 | `/speckit-engineering-build-vuln-intake` | Asks for the flow, ticket number, working branch and base branch. Reads the report, shows the findings table for you to confirm, and seeds `spec.md` |
| 2 | `/speckit-specify`, `/speckit-clarify` | Normal stages on the seeded spec |
| 3 | `/speckit-plan` | Finds where each vulnerable version is declared (`dependencies.conf`, `build.gradle`, property files, the platform repo's reference paths), decides which repo changes, and writes **Vulnerability Upgrade** in `plan.md` |
| 4 | `/speckit-tasks` | One `[VULN]` task per changed repo, in build order |
| 5 | `/speckit-implement` | Creates or checks out branches, edits only the identified lines, then builds and publishes the affected repos to Maven Local in order |
| 6 | `after_implement` hook (`verify`) | Shows the PR plan and asks before pushing. One PR per changed repo, only if every build passed |

### Safety rules

- Fixed versions come only from the ticket. Nothing is invented.
- The first failed build stops the chain and blocks all PRs.
- Pushing a branch or opening a PR needs your confirmation. The tool never merges.
- Operating-system packages in the report are listed as out of scope.
- A line that no longer holds the expected old version is refused, not edited.

Results go to `specs/<feature>/vuln/`: `findings.json`, `changes.json`, `build-results.json`, the logs and `pr-results.json`. The scripts are in `speckit-extensions/engineering-build/scripts/vuln/` (Python standard library only), and each can run alone with `--dry-run`.

## 5. Skills on their own

Every folder in `skills/` is a normal agent skill. Install them with `--agent-skills` (section 2), or copy a folder into your agent's skills folder. For Claude Code that is `~/.claude/skills/` (all projects) or `<repo>/.claude/skills/` (one project):

```bash
cp -r /path/to/sdlc-skills/skills/onboarding ~/.claude/skills/
```

| Skill | Use it to | Example request |
| --- | --- | --- |
| `engineering-build` | Plan and build one feature without Spec Kit. It applies the companion skills by hand when they are installed next to it | "Use engineering-build to plan adding rate limiting" |
| `engineering-review` | Review a whole repository for technical debt, defects and gaps, with source-backed findings and prioritized fixes | "Review this repository with the engineering-review skill" |
| `onboarding` | Explain an existing repository: architecture, flows, database schema, APIs, modules, standards | "Use the onboarding skill to document how this repo works" |
| `engineering-vulnerability-upgrade` | Run the vulnerability workflow without Spec Kit | "Use engineering-vulnerability-upgrade for ticket D-12345" |
| `ponytail` | Write the smallest change that fully solves a coding task, and say what was skipped | "ponytail: fix the date parsing bug" |

Restart the agent, then ask for the skill by name.

## 6. Add a skill to a stage

The binding registry is the extension point. Adding a skill needs no change to the wrapped commands:

1. Put the skill in `skills/<id>/` with its license. Add an entry to `speckit-extensions/engineering-build/skills.lock.yml`.
2. Write `adapters/<id>.md`: which Spec Kit files it reads, where its output goes, and its quality gate.
3. If deciding when it applies needs judgment, add `detectors/<name>.md`. It answers `yes`, `no` or `unknown`, with evidence.
4. Add a binding to `config/engineering-build-config.template.yml`. Triggers are `always`, `detect`, `task_tag`, `path_glob`, `any` and `all`.
5. Refresh the hashes and run the tests, then reinstall with `installer/install.py update`.

To refresh the hashes:

```bash
python speckit-extensions/engineering-build/scripts/verify_lock.py --ext speckit-extensions/engineering-build --skills skills --update
```

Any edit to a shipped skill, including `skills/engineering-build/`, needs this refresh.

## 7. Develop and test

```bash
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```

The suite checks manifests, hooks, bindings, lock integrity, packaging, the Playwright rule checker and the vulnerability scripts. It uses temporary git repos and sample reports, with no network or Gradle. When `specify` is on the PATH, it also runs real installs, rollback, dry-run, bulk mode, `--agent-skills` and `--flows-config`. It takes a few minutes.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `claude not found` during `specify init` | Add `--ignore-agent-tools` |
| New commands do not appear | Restart the agent; check `specify extension list` and `specify preset list` |
| `skill-runs.md` is missing after a stage | Check that `specify preset resolve speckit.plan` points at `engineering-build-preset`, then restart the agent |
| `hash drift` from `verify_lock.py` | A skill was edited. Restore it, or review it and refresh the hashes (section 6) |
| Old `speckit-sdlc-skills-*` or `speckit-engineering-plan-*` commands still appear | Remove the older packages (section 2) |
| The vulnerability intake lists only `main` | Your flow file was not installed; rerun with `--flows-config` |
| The Agility step stops and asks for variables | Set `AGILITY_TOKEN` and `AGILITY_URL` in the shell, then rerun the intake |
| A repo folder is not found | Fix `workspace_root` in `vuln-flows.json`, or check the repo out there |
