# Install in an application repository

[Back to overview](../README.md)

## 1. Install Spec Kit in the target (once)

Use Python 3.10+ and Spec Kit 1.2.0 or a later 1.x version (`specify --version`). Install the CLI with:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.2.0
```

In the application repository, initialize Spec Kit once for your agent:

```bash
specify init --here --integration claude     # or copilot, codex
```

Add `--ignore-agent-tools` if the agent CLI is not on PATH, and `--script ps` on Windows. For an existing setup, do not run init again; refresh old generated commands with `specify integration upgrade <integration>`.

## 2. Install Engineering Build

From the application repository's root, with sdlc-skills cloned next to it (`git clone https://github.com/nitheshrayuduv/sdlc-skills.git ../sdlc-skills`). The installer changes the folder you run it from; `--repo PATH` picks another one:

```bash
python ../sdlc-skills/speckit-extensions/install.py install --dry-run
python ../sdlc-skills/speckit-extensions/install.py install
```

The installer:

1. checks the target has `.specify/`, the CLI version, and warns about older `engineering-plan`, `sdlc-skills` or `org-sdlc` installs;
2. stages `speckit-extensions/engineering-build/` with the skills named in `skills.lock.yml`, copied from the top-level `skills/` folder, and verifies every SHA-256;
3. backs up the Spec Kit registries, runs `specify extension add <staged> --dev`, then `specify preset add --dev speckit-extensions/engineering-build/preset --priority 5`;
4. creates `engineering-build-config.yml` only if absent, verifies the installed lock, and checks the four wrapped commands resolve to the preset. Any failure rolls back.

Add `--agent-skills .claude/skills` (or `.github/skills`, `.agents/skills`) to also copy the skills into the agent's skills folder, so you can call Engineering Build, Engineering Review or Onboarding directly outside Spec Kit.

## 3. Configure and verify

In the agent chat, run `/speckit-engineering-build-configure` once (Codex: `$speckit-engineering-build-configure`). It adds the Engineering Build principle to the constitution. Then:

```bash
python ../sdlc-skills/speckit-extensions/install.py verify
specify extension info engineering-build --json
specify preset resolve speckit.plan
```

Expect the extension enabled with fifteen commands and twelve hooks, and `speckit.plan` resolving to `engineering-build-preset`. Try a small feature and check `specs/<feature>/skill-runs.md`; a printed EXECUTE_COMMAND line alone is not proof a hook ran.

## Update, migrate, remove

- Update: `python ../sdlc-skills/speckit-extensions/install.py update`. Project config and vulnerability flow settings are kept.
- Migrate from `engineering-plan` or `sdlc-skills` + `org-sdlc`: `specify preset remove org-sdlc`, `specify extension remove sdlc-skills --keep-config`, `specify extension remove engineering-plan`, then install. Move any binding overrides from `sdlc-skills-config.yml` into `engineering-build-config.yml`.
- Remove: `python ../sdlc-skills/speckit-extensions/install.py uninstall`. Feature documents and constitution text remain.
