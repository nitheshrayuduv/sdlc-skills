# sdlc-skills

Generic SDLC skills and the Spec Kit extensions that make them run at the right phase of a feature. Use a skill on its own, or install an extension into a repository so the skill is applied automatically while you run `specify`, `clarify`, `plan`, `tasks` and `implement`.

## What is in this repository

| Folder | What it is |
| --- | --- |
| `skills/` | Standalone skills: `engineering-plan`, `engineering-review`, `onboarding`, `engineering-vulnerability-upgrade` |
| `speckit-extensions/engineering-plan` | Spec Kit extension that applies the engineering-plan skill through hooks |
| `speckit-extensions/sdlc-skills` | Spec Kit extension with a **binding registry**: it runs pinned skills at chosen stages (grill-me, database design, API design, Playwright, vulnerability upgrade) |
| `speckit-extensions/org-sdlc` | Spec Kit preset that wraps `clarify`, `plan`, `tasks` and `implement` so they call the `sdlc-skills` extension |
| `installer/` | `install.py`, which installs the extension and preset into any Spec Kit repository |
| `docs/specs/` | Design specs: `spec-kit-extension-spec.md`, `engineering-vulnerability-upgrade-spec.md` |
| `catalog/` | Template entries for an internal Spec Kit catalog |

Which one do I need?

| I want to... | Use |
| --- | --- |
| Plan a feature with architecture, security and standards, every time | `engineering-plan` extension (section 3) |
| Have clarify, plan and test steps use vetted skills automatically | `org-sdlc` preset + `sdlc-skills` extension (section 2) |
| Fix vulnerable dependency versions from a scanner report | `sdlc-skills` extension, vulnerability bindings (section 4) |
| Review a whole repository, or explain one to new engineers | `engineering-review` or `onboarding` skill (section 5) |
| Add my own stage-to-skill pairing (unit tests, security review) | `sdlc-skills` registry (section 6) |

## 1. Prerequisites (all use cases that use Spec Kit)

- Python 3.10 or later and Git.
- Spec Kit CLI 1.2.0 or later. Check with `specify --version`. Install: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.2.0`
- The target repository initialized once for your agent:

```bash
cd /path/to/your-repo
git switch -c my-feature-branch
specify init --here --integration claude        # or copilot, codex
```

If `specify init` stops because the agent's CLI is not found (for example you use a desktop app), add `--ignore-agent-tools`. On Windows add `--script ps`.

Where the commands land depends on the integration: `claude` writes them to `.claude/skills/`, `copilot` to `.github/skills/`. Commands are invoked with hyphens, for example `/speckit-plan`; some agents use dots, such as `/speckit.plan`.

**Restart your agent after installing anything.** Agents load skills when a session starts, so a session that was already running when you installed reports the new commands as unknown. In GitHub Copilot CLI: `/exit`, open a new terminal in the repo, run `copilot`, and check `/skills`.

## 2. General use: skills at every stage (org-sdlc + sdlc-skills)

This is the main path. The preset wraps four core commands, and each wrap makes one call to the extension's runner, which reads a registry and applies the skills that match.

| Stage | Skill | Runs when |
| --- | --- | --- |
| `clarify` | grill-me | Always. An interview in rounds, with edge-case lenses; answers go under `## Clarifications` in `spec.md` |
| `plan` | database-schema-designer | The feature changes the data model. Output goes to `data-model.md` and `db/` |
| `plan` | api-designer | The feature adds or changes an API. Output goes to `contracts/openapi.yaml` |
| `tasks`, `implement` | playwright-expert | A `[E2E]` task or a Playwright test file. Rules are checked after writing |
| `plan`, `tasks`, `implement` | engineering-vulnerability-upgrade | A scanner report drives a dependency upgrade (section 4) |

### Install

```bash
python /path/to/sdlc-skills/installer/install.py install --repo /path/to/your-repo --dry-run   # preview
python /path/to/sdlc-skills/installer/install.py install --repo /path/to/your-repo
python /path/to/sdlc-skills/installer/install.py verify  --repo /path/to/your-repo
```

The installer adds the extension, then the preset (priority 5), keeps your existing project config, backs up the Spec Kit registries, and rolls back if a step fails. More options (`--profile strict`, `--set key=value`, `--repos-file` for many repos, `--source url|bundle`) are in [installer/README.md](installer/README.md). The manual equivalent:

```bash
specify extension add /path/to/sdlc-skills/speckit-extensions/sdlc-skills --dev
specify preset add --dev /path/to/sdlc-skills/speckit-extensions/org-sdlc --priority 5
```

### Use

Run the normal Spec Kit commands. Nothing else to remember:

```text
/speckit-specify <what you want to build>
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-implement
```

### Check which skills ran

Every run or skip is recorded, with the pinned skill version:

- `specs/<feature>/skill-runs.md`: one row per binding (ran, skipped and why, evidence, warnings)
- `plan.md`, `## Skill Applicability`: the same decisions inside the plan

A feature that only changes UI copy will skip the database and API skills. That is correct, and the table says why.

### Configure

Defaults live in `.specify/extensions/sdlc-skills/config/sdlc-skills-config.template.yml`. Override per repo in `.specify/extensions/sdlc-skills/sdlc-skills-config.yml`, or locally in `sdlc-skills-config.local.yml`:

```yaml
bindings:
  - id: plan-api
    enabled: false              # turn a skill off for this repo
  - id: clarify-grill
    settings: { max_rounds: 3, interaction: one-at-a-time }
```

A skill whose tooling is missing (no network for the API lint, say) records a warning and the stage continues. Set `required: true` on a binding, or install with `--profile strict`, to block instead. Vendored skills are checked against `skills.lock.yml` on every run: `python .specify/extensions/sdlc-skills/scripts/verify_lock.py --ext .specify/extensions/sdlc-skills`.

## 3. Engineering plan (engineering-plan extension)

Use this when you want every feature planned with architecture, design diagrams, security controls, code standards, suitable patterns, traceable tasks and a rollout plan, in plain English.

```bash
cd /path/to/sdlc-skills/speckit-extensions/engineering-plan
python scripts/install.py --repo /path/to/your-repo --dry-run
python scripts/install.py --repo /path/to/your-repo
```

Then, in your agent, apply the principle to the project constitution once:

```text
/speckit-engineering-plan-configure
```

After that, use Spec Kit as normal. Hooks prepare each stage before it runs and check the output after it: `spec-check` after specify and clarify, `design` after plan, `task-check` after tasks, `verify` after implement. Outputs land in the usual files (`spec.md`, `plan.md`, `tasks.md`, plus `engineering/` pages when a plan grows large). Details: [install](speckit-extensions/engineering-plan/docs/install.md), [usage](speckit-extensions/engineering-plan/docs/usage.md), [maintenance](speckit-extensions/engineering-plan/docs/maintaining.md).

`engineering-plan` and `org-sdlc` can be installed together. They use different hooks and commands.

## 4. Vulnerability upgrade from a scanner report

Fixes vulnerable dependency versions reported by a scanner (Trivy JSON, or a table saved to a file) across a chain of repositories that depend on each other. Works with Gradle, Maven or any build tool you configure. Scripts do the exact work; the agent asks questions and reads results. Design: [engineering-vulnerability-upgrade-spec.md](docs/specs/engineering-vulnerability-upgrade-spec.md).

### One-time setup

1. Install `org-sdlc` and `sdlc-skills` into the repo you will run from (section 2), usually the first repo of the chain.
2. Check out every repo of the chain side by side under one folder. The tool never clones.
3. Describe the chain in `.specify/extensions/sdlc-skills/config/vuln-flows.json`:
   - `flows`: the repos in build order, for example `"main": {"publish": true, "repos": ["platform", "service-a", "service-b"]}`.
   - `handoff`: which file and key in a later repo pins an earlier repo's version (`gradle.properties`, a version catalog, HOCON, or a Maven `<x.version>` property).
   - `build`: `"tool": "gradle"` or `"maven"`, or explicit `command`, `publish_command`, `version_command`; per repo under `repo_overrides`, with optional `env` such as `JAVA_HOME`.
   - `workspace_root` only if the repos are not next to the repo you run from.

   The shipped file is a generic example; `installer/install.py update` keeps your project's values.

4. Produce a scanner report and save it in the repo or next to it, for example `trivy image --format json -o trivy.json <image>`. A table copied from a ticket or a scanner summary into a text file also works.

Example `vuln-flows.json` for a chain where a Gradle platform library is used by a Gradle service and a Maven service:

```json
{
  "workspace_root": "~/work",
  "branch_prefix": "vuln/",
  "build": { "tool": "gradle" },
  "repo_overrides": {
    "service-b": { "tool": "maven", "env": { "JAVA_HOME": "/opt/jdk-21" } }
  },
  "handoff": [
    { "from": "platform", "version_source": "build",
      "to": [ { "repo": "service-a", "file": "gradle.properties", "key": "platformVersion" },
              { "repo": "service-b", "file": "pom.xml", "key": "platform.version" } ] }
  ],
  "flows": { "main": { "publish": true, "repos": ["platform", "service-a", "service-b"] } }
}
```

| Setting | Meaning |
| --- | --- |
| `build.tool` | `gradle`: `./gradlew clean build -x test`, then `publishToMavenLocal`. `maven`: `./mvnw clean install -DskipTests`. The repo's wrapper is used when present, else `gradle` or `mvn` from the PATH |
| `build.command`, `publish_command`, `version_command`, `version_pattern` | Explicit commands for any other build tool, or to override a preset. `publish_command: null` skips publishing |
| `repo_overrides.<repo>` | Any of the above for one repo, plus `env` (for example a different `JAVA_HOME`) and extra exclusions such as `-x itest` |
| `handoff` | After `from` is published, its version is written into `key` of `file` in each `to` repo before that repo builds, then restored |

### Run it

| Step | Command | What happens |
| --- | --- | --- |
| 1 | `/speckit-sdlc-skills-vuln-intake` | Asks flow, ticket reference, branch, base branch and report file. Reads the report, shows the findings table, asks you to confirm, seeds `spec.md` |
| 2 | `/speckit-specify`, `/speckit-clarify` | Normal stages on the seeded spec |
| 3 | `/speckit-plan` | Finds where each vulnerable version is declared (Maven `pom.xml`, Gradle files and catalogs, properties), decides which repo changes, writes **Vulnerability Upgrade** in `plan.md` |
| 4 | `/speckit-tasks` | One `[VULN]` task per changed repo, plus one `build_chain.py` task |
| 5 | `/speckit-implement` | Creates or checks out branches, edits only the identified lines, builds (clean, no tests) and publishes each affected repo in order, handing each published version to the next repos |
| 6 | automatic `after_implement` hook | Shows the PR plan and asks before pushing. One PR per changed repo, only if every build passed |

At intake, the base branch is the branch the working branch is created from in repos that do not have it yet, and the branch the PRs target, for example `2.4.x-maintenance`. A repo that lacks it can get its own base branch.

**Let the tool build.** Do not run `./gradlew`, `mvn install` or publish tasks by hand, and do not edit version pins yourself: only `build_chain.py` hands each published version to the next repos and puts the files back afterwards. If it finds a pin already changed by hand it refuses to start and names the file; revert it with `git checkout -- <file>`.

### Without an agent

The scripts are plain Python and can run on their own, from the repo where the extension is installed:

```bash
S=.specify/extensions/sdlc-skills/scripts/vuln
F=specs/001-vuln-upgrade-proj-123
python $S/intake.py --flow main --ticket PROJ-123 --branch vuln/PROJ-123 --base main --feature-dir $F
python $S/read_report.py --report trivy.json --ticket PROJ-123 --out $F/vuln/findings.json
python $S/find_versions.py --flow main --findings $F/vuln/findings.json --out $F/vuln/hits.json
python $S/resolve_owner.py --hits $F/vuln/hits.json --findings $F/vuln/findings.json --out $F/vuln/changes.json
python $S/prepare_branches.py --feature-dir $F
python $S/apply_upgrade.py --changes $F/vuln/changes.json --out $F/vuln/apply-results.json
python $S/build_chain.py --flow main --feature-dir $F --changed-only
python $S/raise_prs.py --feature-dir $F          # shows the plan; add --yes to push and open PRs
```

Each script accepts `--help`. To look before changing anything: `apply_upgrade.py` and `build_chain.py` take `--dry-run`, `prepare_branches.py` takes `--check-only`, and `raise_prs.py` only shows the plan until you add `--yes`.

### Safety rules

- Fixed versions come only from the report. Nothing is invented.
- The first failed build stops the chain and blocks all PRs, whatever `required` says.
- Pushing a branch or opening a PR needs your confirmation. PRs are never merged by the tool.
- Operating-system packages in the report are listed as out of scope.
- A line that no longer holds the expected old version is refused, not edited.

Results are under `specs/<feature>/vuln/` (`findings.json`, `changes.json`, `build-results.json`, logs, `pr-results.json`). The scripts (`scripts/vuln/`, Python standard library only) can also be run on their own; see below.

## 5. Skills used on their own

`engineering-review` and `onboarding` are not Spec Kit stages. Use them directly.

| Skill | Use it to | Example request |
| --- | --- | --- |
| `engineering-review` | Review a whole repository for technical debt, defects and gaps, with source-backed findings and prioritized fixes | "Review this repository with the engineering-review skill" |
| `onboarding` | Explain an existing repository to new engineers: architecture, flows, database schema, APIs, modules, standards | "Use the onboarding skill to document how this repo works" |
| `engineering-plan` | Plan one feature or change without Spec Kit | "Use engineering-plan to plan adding rate limiting" |
| `engineering-vulnerability-upgrade` | Run the vulnerability workflow without Spec Kit | "Use engineering-vulnerability-upgrade for PROJ-123 with report trivy.json" |

To make a skill available to your agent, copy its folder (it contains `SKILL.md`) into the agent's skills folder. For Claude Code that is `~/.claude/skills/` for all projects, or `<repo>/.claude/skills/` for one project:

```bash
cp -r /path/to/sdlc-skills/skills/onboarding ~/.claude/skills/
```

Restart the agent, then ask for the skill by name.

## 6. Add your own stage-to-skill pairing

The registry in `sdlc-skills` is the extension point. Adding unit testing, security review or another skill needs no change to the wrapped commands:

1. Vendor the skill into `speckit-extensions/sdlc-skills/skills/<id>/`, keeping its license, and add an entry to `skills.lock.yml`.
2. Write `adapters/<id>.md`: inputs from Spec Kit artifacts, where results go, the quality gate.
3. If the trigger needs judgment, add `detectors/<name>.md` (output `yes`, `no` or `unknown` with evidence).
4. Add a binding to `config/sdlc-skills-config.template.yml`. Triggers: `always`, `detect`, `task_tag`, `path_glob`, `any`, `all`.
5. Refresh hashes with `python scripts/verify_lock.py --ext . --update`, run the tests, then reinstall with `installer/install.py update`.

To upgrade a vendored skill, copy the new version in, update `commit` and `version` in the lock, rerun `--update`, review the diff and run the tests.

## 7. Develop and test

```bash
python -m unittest discover -s speckit-extensions/sdlc-skills/tests -v
```

The suite checks manifests, bindings, lock integrity, the Playwright rule checker, the vulnerability scripts (temporary git repos, sample Trivy and table reports, Gradle and Maven layouts, stub build commands; no network or real build tools), and real installs, rollback, dry-run and bulk mode when `specify` is on the PATH. It takes a couple of minutes.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `claude not found` during `specify init` | Add `--ignore-agent-tools` |
| New commands do not appear | Restart the agent; check `specify extension list` and `specify preset list` |
| `skill-runs.md` is missing after a stage | The wrapped command did not call the runner. Check `specify preset resolve speckit.plan` points at `org-sdlc`, and restart the agent |
| `hash drift` from `verify_lock.py` | A vendored skill was edited. Restore it, or review and run `--update` |
| `Unknown command: /speckit-...` in Copilot CLI or another agent | The session started before the install. Start a new session in the repo; in Copilot CLI check `/skills` |
| Repo folder not found | Check the repos out side by side next to the repo you run from, or set `workspace_root` in `vuln-flows.json` |
| "These version pins were changed by hand" | Revert the named files with `git checkout -- <file>` and rerun `build_chain.py` |
| Build fails with "requires at least JVM runtime version ..." | Point that repo at the right JDK with `repo_overrides.<repo>.env.JAVA_HOME`, or start the agent with the right `JAVA_HOME` |
| A vulnerable version is `not-found` | It probably arrives transitively. Find the parent with `gradle dependencyInsight --dependency NAME` or `mvn dependency:tree -Dincludes=GROUP:ARTIFACT`, then upgrade the parent or add a constraint |
| A build fails on a Docker, integration or format task | It is the environment, not the version change. Exclude that task for the repo in `repo_overrides.<repo>.command`; CI still runs it |
| `Unable to delete directory ... build` on Windows | Another process (an IDE, a running server, an Explorer window) holds files in the build folder. Close it and resume with `--from-repo <repo>` |
