# Spec Kit extensions

| Path | What it is |
| --- | --- |
| [`engineering-build/`](engineering-build/README.md) | The `engineering-build` extension, with its `engineering-build-preset` preset in `engineering-build/preset/` |
| `install.py` | Installs the extension, its locked skills and the preset into a Spec Kit project |
| `catalog.json` | Template entry for an internal Spec Kit catalog. Fill `download_url` and `sha256` at release time. Only an internal catalog should set `install_allowed: true` |

## install.py

Python 3.8+, standard library only. It drives the `specify` CLI, so the target needs `specify` 1.2.0 or later on the PATH and a project created with `specify init`. Run it from the root of the repository you are installing into; it changes the current folder unless you pass `--repo`. The examples assume this repository is cloned next to yours, at `../sdlc-skills`:

```bash
python ../sdlc-skills/speckit-extensions/install.py install                                  # into the current folder
python ../sdlc-skills/speckit-extensions/install.py install --dry-run                        # print everything, change nothing
python ../sdlc-skills/speckit-extensions/install.py install --agent-skills .claude/skills    # also copy skills for direct use
python ../sdlc-skills/speckit-extensions/install.py install --flows-config /path/outside/the/clone/vuln-flows.json
python ../sdlc-skills/speckit-extensions/install.py install --repo /path/to/other-repo        # a different folder
python ../sdlc-skills/speckit-extensions/install.py install --repos-file repos.txt            # many repos, one result row each
python ../sdlc-skills/speckit-extensions/install.py install --profile strict --set max_rounds=4
python ../sdlc-skills/speckit-extensions/install.py verify --json                           # CI gate
python ../sdlc-skills/speckit-extensions/install.py status|update|uninstall
python speckit-extensions/install.py package --output dist          # release zip + .sha256 (run in this repository)
```

What `install` does, in order:

1. Preflight: `.specify/` exists, `specify` version, Python version, git tree state. Warns if the older `engineering-plan`, `sdlc-skills` or `org-sdlc` packages are still installed.
2. Stage: copies `engineering-build/` (without `preset/`, `tests/`, `docs/`) to a temporary folder and adds every skill named in its `skills.lock.yml` from the top-level `skills/` folder. The lock is verified on the source and on the staged copy.
3. Back up `.specify/` registries to `.specify/.backup/<timestamp>/`.
4. `specify extension add <staged> --dev`, then `specify preset add --dev speckit-extensions/engineering-build/preset --priority 5`.
5. Create `engineering-build-config.yml` from the template only if absent (`--profile`, `--set` apply).
6. Verify the installed lock, check the extension and preset are listed, and check the four wrapped commands resolve to the preset. Any failure removes what was added and restores the registries.
7. With `--agent-skills DIR`, copy every folder under `skills/` into `DIR` inside the repo (existing ones are kept, except on `update`).

Sources: `--source local` (default, this checkout or `--local-path`), `catalog` (with `--version`), `url` (`--url` and `--sha256`) or `bundle` (`--bundle file.zip`, offline). Archives must come from `install.py package`, so the extension already carries its skills.

The shipped `vuln-flows.json` is a neutral example. Pass `--flows-config FILE` to overlay your team's own file (real repo chains, kept outside git) on install or update. `update` keeps project config and this project's `vuln-flows.json` settings (`workspace_root`, `branch_prefix`, `build`, `repo_overrides`, `base_branch`, `platform_repo`, `reference_paths`, `handoff`, `flows`) and takes only new default keys from the release.

Exit codes: 0 success, 1 failure, 2 preflight failure, 3 integrity failure. The log is `.specify/engineering-build-install.log`. Restart your agent if the new commands do not appear.
