# Installer

Adds the `sdlc-skills` extension and the `org-sdlc` preset to any Spec Kit project by driving the `specify` CLI. Python 3.8+, standard library only. Needs `specify` 1.2.0 or later on the PATH and a project created with `specify init`.

```bash
python installer/install.py install --repo /path/to/app                 # from this checkout
python installer/install.py install --repo /path/to/app --dry-run       # print everything, change nothing
python installer/install.py install --repos-file repos.txt              # many repos, one result row each
python installer/install.py install --repo . --profile strict --set max_rounds=4
python installer/install.py verify  --repo . --json                     # CI gate
python installer/install.py status|update|uninstall --repo .
```

Sources: `--source local` (default), `catalog` (with `--version`), `url` (`--url` and `--sha256`) or `bundle` (`--bundle file.zip`, offline). Install order is extension, then preset (default `--priority 5`). Registries are backed up to `.specify/.backup/<timestamp>/` and restored if a step fails. Project config is never overwritten, and `update` keeps this project's `vuln-flows.json` settings: its repo chains (`flows`), version hand-over rules (`handoff`), build settings and overrides, `workspace_root`, `branch_prefix`, `platform_repo`, `reference_paths`, `version_files` and `base_branch`. The shipped file only holds a generic example. Exit codes: 0 success, 1 failure, 2 preflight failure, 3 integrity failure. The log is `.specify/sdlc-skills-install.log`. Restart your agent if the new commands do not appear.
