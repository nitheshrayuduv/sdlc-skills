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
python ../sdlc-skills/presets/install.py install --dry-run
python ../sdlc-skills/presets/install.py install
```

The installer:

1. checks the target has `.specify/` and the CLI version, and warns about older `engineering-plan`, `sdlc-skills` or `org-sdlc` installs;
2. stages `presets/engineering-build/` with the skills named in `skills.lock.yml`, copied from the top-level `skills/` folder, and verifies every SHA-256;
3. backs up the Spec Kit registries and removes an earlier Engineering Build install (the `engineering-build` extension and `engineering-build-preset`), moving its binding config to `.specify/engineering-build.yml`;
4. runs `specify preset add --dev <staged> --priority 5`;
5. creates `.specify/engineering-build.yml` only if absent, verifies the installed lock, and checks the six wrapped commands resolve to the preset. Any failure rolls back.

Add `--agent-skills .claude/skills` (or `.github/skills`, `.agents/skills`) to also copy the skills into the agent's skills folder, so you can call Engineering Build, Engineering Review or Onboarding directly outside Spec Kit.

## 3. Add the principle and verify

If the repository already has a constitution, run `/speckit-constitution` once in the agent chat (Codex: `$speckit-constitution`). Its wrapped after step adds the Engineering Build principle. Then:

```bash
python ../sdlc-skills/presets/install.py verify
specify preset resolve speckit.plan
```

Expect the composition chain to end with a `[wrap]` from `engineering-build`, for all six core commands. Try a small feature and check `specs/<feature>/skill-runs.md`.

## Update, migrate, remove

- Update: `python ../sdlc-skills/presets/install.py update`. `.specify/engineering-build.yml` is kept.
- Migrate from an earlier Engineering Build release (extension + `engineering-build-preset`): run `install` or `update`; the installer removes the old packages and keeps their config. Then run `/speckit-constitution` so the principle links to `.specify/presets/engineering-build/`.
- Migrate from `engineering-plan` or `sdlc-skills` + `org-sdlc`: `specify preset remove org-sdlc`, `specify extension remove sdlc-skills --keep-config`, `specify extension remove engineering-plan`, then install. Move any binding overrides from `sdlc-skills-config.yml` into `.specify/engineering-build.yml`.
- Remove: `python ../sdlc-skills/presets/install.py uninstall`. Project settings, feature documents and constitution text remain.
