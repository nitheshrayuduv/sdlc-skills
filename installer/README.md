# Installer

Installs Engineering Build into any Spec Kit project: the `engineering-build` extension with its skills, then the `engineering-build-preset` preset. It drives the `specify` CLI. Python 3.8+, standard library only. Spec Kit is installed separately: the target needs `specify` 1.2.0 or later on the PATH and a project created with `specify init`.

```bash
python installer/install.py install --repo /path/to/app                 # from this checkout
python installer/install.py install --repo /path/to/app --dry-run       # print everything, change nothing
python installer/install.py install --repo /path/to/app --agent-skills .claude/skills   # also copy skills for direct use
python installer/install.py install --repos-file repos.txt              # many repos, one result row each
python installer/install.py install --repo . --profile strict --set max_rounds=4
python installer/install.py verify  --repo . --json                     # CI gate
python installer/install.py status|update|uninstall --repo .
python installer/install.py package --output dist                       # release zip + .sha256
```

What `install` does, in order:

1. Preflight: `.specify/` exists, `specify` version, Python version, git tree state. Warns if the older `engineering-plan`, `sdlc-skills` or `org-sdlc` packages are still installed.
2. Stage: copies `speckit-extensions/engineering-build/` (without `preset/`, `tests/`, `docs/`) to a temporary folder and adds every skill named in its `skills.lock.yml` from the top-level `skills/` folder. The lock is verified on the source and on the staged copy.
3. Back up `.specify/` registries to `.specify/.backup/<timestamp>/`.
4. `specify extension add <staged> --dev`, then `specify preset add --dev speckit-extensions/engineering-build/preset --priority 5`.
5. Create `engineering-build-config.yml` from the template only if absent (`--profile`, `--set` apply).
6. Verify the installed lock, check the extension and preset are listed, and check the four wrapped commands resolve to the preset. Any failure removes what was added and restores the registries.
7. With `--agent-skills DIR`, copy every folder under `skills/` into `DIR` inside the repo (existing ones are kept, except on `update`).

Sources: `--source local` (default, this checkout or `--local-path`), `catalog` (with `--version`), `url` (`--url` and `--sha256`) or `bundle` (`--bundle file.zip`, offline). Archives must come from `install.py package`, so the extension already carries its skills. The shipped `vuln-flows.json` is a neutral example. Pass `--flows-config FILE` to overlay your team's own file (real repo chains, kept outside git) on install or update. `update` keeps project config and this project's `vuln-flows.json` settings (`workspace_root`, `branch_prefix`, `build`, `repo_overrides`, `base_branch`, `platform_repo`, `reference_paths`, `handoff`, `flows`) and takes only new default keys from the release. Exit codes: 0 success, 1 failure, 2 preflight failure, 3 integrity failure. The log is `.specify/engineering-build-install.log`. Restart your agent if the new commands do not appear.
