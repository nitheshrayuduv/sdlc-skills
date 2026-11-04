# sdlc-skills

Generic SDLC skills, and one Spec Kit extension that makes them run at the right phase of a feature. Install Spec Kit in your repository, then run `installer/install.py` to add the extension, its preset and its skills.

## What is in this repository

```text
sdlc-skills/
├── skills/                                  every skill, one folder each, flat
│   ├── engineering-build/                   design → plan → build; calls the companion skills below
│   ├── engineering-review/                  whole-repository review (standalone)
│   ├── onboarding/                          explain a repository (standalone)
│   ├── engineering-vulnerability-upgrade/   Agility ticket → Gradle version fixes (companion)
│   ├── grill-me/                            clarify interview (companion, vendored, MIT)
│   ├── database-schema-designer/            data model design (companion, vendored, MIT)
│   ├── api-designer/                        OpenAPI design (companion, vendored, MIT)
│   └── playwright-expert/                   E2E tests (companion, vendored, MIT)
├── speckit-extensions/
│   └── engineering-build/                   the Spec Kit extension
│       ├── extension.yml, hooks.md, commands/, config/, adapters/, detectors/, scripts/
│       ├── skills.lock.yml                  which skills it ships, pinned by SHA-256
│       └── preset/                          the preset that wraps clarify, plan, tasks, implement
├── installer/install.py                     installs extension + preset + skills into a repo
├── docs/specs/                              design specs
└── catalog/                                 template entry for an internal Spec Kit catalog
```

Skills are stored once, in `skills/`. The extension does not keep its own copies; the installer copies the skills its lock names into the target repository at install time.

| I want to... | Use |
| --- | --- |
| Plan and build every feature with architecture, security, standards and the vetted companion skills | Engineering Build extension (sections 1 to 3) |
| Fix vulnerable Gradle versions from an Agility ticket | Engineering Build, vulnerability bindings (section 4) |
| Review a whole repository, or explain one to new engineers | `engineering-review` or `onboarding` skill (section 5) |
| Add my own stage-to-skill pairing (unit tests, security review) | The binding registry (section 6) |

## 1. Prerequisites: install Spec Kit in your repository

- Python 3.10 or later and Git.
- Spec Kit CLI 1.2.0 or later. Check with `specify --version`. Install: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.2.0`
- The target repository initialized once for your agent:

```bash
cd /path/to/your-repo
git switch -c my-feature-branch
specify init --here --integration claude        # or copilot, codex
```

If `specify init` stops with "claude not found" because you use the desktop app and not the CLI, add `--ignore-agent-tools`. On Windows add `--script ps`.

## 2. Install Engineering Build

From a clone of this repository:

```bash
python /path/to/sdlc-skills/installer/install.py install --repo /path/to/your-repo --dry-run   # preview
python /path/to/sdlc-skills/installer/install.py install --repo /path/to/your-repo
python /path/to/sdlc-skills/installer/install.py verify  --repo /path/to/your-repo
```

The installer stages the extension with its skills, adds it, then adds the preset (priority 5). It keeps existing project config, backs up the Spec Kit registries and rolls back if a step fails. Add `--agent-skills .claude/skills` to also copy every skill into your agent's skills folder, for direct use outside Spec Kit. More options (`--profile strict`, `--set key=value`, `--repos-file`, `--source url|bundle`, `package`) are in [installer/README.md](installer/README.md).

Restart your agent so the new commands load, then apply the principle to the project constitution once:

```text
/speckit-engineering-build-configure
```

In Claude, Spec Kit commands are written with hyphens, for example `/speckit-plan`. Other agents may use dots, such as `/speckit.plan`.

Moving from the older packages? Remove them first: `specify preset remove org-sdlc`, `specify extension remove sdlc-skills --keep-config`, `specify extension remove engineering-plan`. The installer warns if any are still present.

## 3. Use it

Run the normal Spec Kit commands. Nothing else to remember:

```text
/speckit-specify <what you want to build>
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-implement
```

Engineering Build hooks run before and after each stage (architecture, diagrams, security controls, standards, traceable tasks, implementation evidence). Inside the stages it calls its companion skills:

| Stage | Companion skill | Runs when |
| --- | --- | --- |
| `clarify` | grill-me | Always. An interview in rounds, with edge-case lenses; answers go under `## Clarifications` in `spec.md` |
| `plan` | database-schema-designer | The feature changes the data model. Output goes to `data-model.md` and `db/` |
| `plan` | api-designer | The feature adds or changes an API. Output goes to `contracts/openapi.yaml` |
| `tasks`, `implement` | playwright-expert | A `[E2E]` task or a Playwright test file. Rules are checked after writing |
| `plan`, `tasks`, `implement` | engineering-vulnerability-upgrade | A vulnerability ticket drives the feature (section 4) |

The preset places each call at the right point inside the stage. If it is missing or skipped, the Engineering Build after hooks run the bindings themselves.

### Check which skills ran

Every run or skip is recorded, with the pinned skill version:

- `specs/<feature>/skill-runs.md`: one row per binding (ran, skipped and why, evidence, warnings)
- `plan.md`, `## Skill Applicability`: the same decisions inside the plan

A feature that only changes UI copy will skip the database and API skills. That is correct, and the table says why.

### Configure

Defaults live in `.specify/extensions/engineering-build/config/engineering-build-config.template.yml`. Override per repo in `.specify/extensions/engineering-build/engineering-build-config.yml`, or locally in `engineering-build-config.local.yml`:

```yaml
bindings:
  - id: plan-api
    enabled: false              # turn a skill off for this repo
  - id: clarify-grill
    settings: { max_rounds: 3, interaction: one-at-a-time }
```

A skill whose tooling is missing (no network for the API lint, say) records a warning and the stage continues. Set `required: true` on a binding, or install with `--profile strict`, to block instead. Installed skills are checked against `skills.lock.yml` on every run: `python .specify/extensions/engineering-build/scripts/verify_lock.py --ext .specify/extensions/engineering-build`.

More: [extension README](speckit-extensions/engineering-build/README.md), [install](speckit-extensions/engineering-build/docs/install.md), [usage](speckit-extensions/engineering-build/docs/usage.md), [maintenance](speckit-extensions/engineering-build/docs/maintaining.md).

## 4. Vulnerability upgrade from an Agility ticket

Fixes vulnerable Gradle dependency versions listed in an Agility ticket across the repos of the **deploy** or **release** build flow. Scripts do the exact work; the agent asks questions and reads results. Design: [engineering-vulnerability-upgrade-spec.md](docs/specs/engineering-vulnerability-upgrade-spec.md).

### One-time setup

1. Install Engineering Build into the repo you will run from (section 2). It is usually `xl-platform`.
2. Check out every repo of the flow under one folder. The tool never clones.
3. Set in your shell, never in a file:

```powershell
$env:AGILITY_TOKEN = "<your Agility token>"
$env:AGILITY_URL   = "https://www7.v1host.com/Instance"
```

4. Edit `.specify/extensions/engineering-build/config/vuln-flows.json`: `workspace_root`, the repo order per flow, build commands, and check `handoff`: it already maps each repo's published version into the later repos' `gradle/dependencies.conf` keys (`xlPlatformVersion`, `centralConfigurationVersion`, `deployTaskEngineVersion`, `xlDeployVersion`). Repos build strictly one at a time in flow order.

### Run it

| Step | Command | What happens |
| --- | --- | --- |
| 1 | `/speckit-engineering-build-vuln-intake` | Asks flow, ticket number, branch and base branch (suggested from the branch name, for example `26.3.x-maintenance`). Reads the report, shows the findings table, asks you to confirm, seeds `spec.md` |
| 2 | `/speckit-specify`, `/speckit-clarify` | Normal stages on the seeded spec |
| 3 | `/speckit-plan` | Finds where each vulnerable version is declared (`dependencies.conf`, `build.gradle`, property files, `xl-reference`), decides which repo changes, writes **Vulnerability Upgrade** in `plan.md` |
| 4 | `/speckit-tasks` | One `[VULN]` task per changed repo, in build order |
| 5 | `/speckit-implement` | Creates or checks out branches, edits only the identified lines, builds and publishes each repo to Maven Local in order |
| 6 | automatic `after_implement` hook (`verify`) | Shows the PR plan and asks before pushing. One PR per changed repo, only if every build passed |

Deploy chain: `xl-platform`, `central-configuration`, `deploy-central-configuration`, `deploy-permission-service`, `xld-stitch-core`, `deploy-task-engine`, `xl-deploy`, `xl-satellite`, `overthere`, `deploy-cli`. Release chain: `xl-platform`, `xl-release`.

### Safety rules

- Fixed versions come only from the ticket. Nothing is invented.
- The first failed build stops the chain and blocks all PRs, whatever `required` says.
- Pushing a branch or opening a PR needs your confirmation. PRs are never merged by the tool.
- Operating-system packages in the report are listed as out of scope.
- A line that no longer holds the expected old version is refused, not edited.

Results are under `specs/<feature>/vuln/` (`findings.json`, `changes.json`, `build-results.json`, logs, `pr-results.json`). The scripts (`speckit-extensions/engineering-build/scripts/vuln/`, Python standard library only) can also be run alone with `--dry-run`.

## 5. Skills used on their own

Every folder in `skills/` is a normal agent skill. Install them with `--agent-skills` (section 2), or copy a folder into your agent's skills folder (`~/.claude/skills/` for all projects, `<repo>/.claude/skills/` for one):

```bash
cp -r /path/to/sdlc-skills/skills/onboarding ~/.claude/skills/
```

| Skill | Use it to | Example request |
| --- | --- | --- |
| `engineering-build` | Plan and build one feature without Spec Kit; it applies the companion skills by hand when they are installed next to it | "Use engineering-build to plan adding rate limiting" |
| `engineering-review` | Review a whole repository for technical debt, defects and gaps, with source-backed findings and prioritized fixes | "Review this repository with the engineering-review skill" |
| `onboarding` | Explain an existing repository to new engineers: architecture, flows, database schema, APIs, modules, standards | "Use the onboarding skill to document how this repo works" |
| `engineering-vulnerability-upgrade` | Run the vulnerability workflow without Spec Kit | "Use engineering-vulnerability-upgrade for ticket D-12345, deploy flow" |

Restart the agent, then ask for the skill by name.

## 6. Add your own stage-to-skill pairing

The binding registry is the extension point. Adding unit testing, security review or another skill needs no change to the wrapped commands:

1. Put the skill in `skills/<id>/`, keeping its license, and add an entry to `speckit-extensions/engineering-build/skills.lock.yml`.
2. Write `adapters/<id>.md`: inputs from Spec Kit artifacts, where results go, the quality gate.
3. If the trigger needs judgment, add `detectors/<name>.md` (output `yes`, `no` or `unknown` with evidence).
4. Add a binding to `config/engineering-build-config.template.yml`. Triggers: `always`, `detect`, `task_tag`, `path_glob`, `any`, `all`.
5. Refresh hashes, run the tests, then reinstall with `installer/install.py update`:

```bash
python speckit-extensions/engineering-build/scripts/verify_lock.py --ext speckit-extensions/engineering-build --skills skills --update
```

Any edit to a shipped skill, including `skills/engineering-build/`, needs that hash refresh.

## 7. Develop and test

```bash
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```

The suite checks manifests, hooks, bindings, lock integrity, packaging, the Playwright rule checker, the vulnerability scripts (temporary git repos and sample scanner reports, no network or Gradle), and real installs, rollback, dry-run, bulk mode and `--agent-skills` when `specify` is on the PATH. It takes a few minutes.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `claude not found` during `specify init` | Add `--ignore-agent-tools` |
| New commands do not appear | Restart the agent; check `specify extension list` and `specify preset list` |
| `skill-runs.md` is missing after a stage | Check `specify preset resolve speckit.plan` points at `engineering-build-preset`, and restart the agent. The after hooks should also run the bindings; check the transcript |
| `hash drift` from `verify_lock.py` | A skill was edited. Restore it, or review and refresh the hashes (section 6) |
| Old commands (`speckit-sdlc-skills-*`, `speckit-engineering-plan-*`) still appear | Remove the older packages (section 2) |
| Agility step stops asking for variables | Set `AGILITY_TOKEN` and `AGILITY_URL` in the shell, then rerun the intake command |
| Repo folder not found | Fix `workspace_root` in `vuln-flows.json`, or check the repo out there |
