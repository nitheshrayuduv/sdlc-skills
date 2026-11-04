# Maintain and release

[Back to overview](../README.md)

## Where things live

| Change | Edit |
| --- | --- |
| Engineering guidance shared by every stage | `skills/engineering-build/` (repository root) |
| What a hook does at one stage | `commands/` |
| Which companion skill runs when | `config/engineering-build-config.template.yml` |
| How a skill reads Spec Kit artifacts and where its output goes | `adapters/<skill>.md` |
| An applicability decision | `detectors/<name>.md` |
| A stage placement inside a core command | `preset/commands/` |

## Add a companion skill

1. Put the skill in the repository's top-level `skills/<id>/`, unmodified, with its `LICENSE`.
2. Add an entry to `skills.lock.yml` (source URL, commit, license, version, `sha256: pending`).
3. Write `adapters/<id>.md`; add `detectors/<name>.md` if the trigger needs judgment.
4. Add a binding to the registry. Triggers: `always`, `detect`, `task_tag`, `path_glob`, `any`, `all`.
5. Refresh hashes and run the tests (below). If the new stage is not a core command, add a hook that calls the runner for it.

To upgrade an upstream skill, copy the new version in, update `commit` and `version` in the lock, refresh the hashes, review the diff and run the tests. Any edit to a shipped skill, including `skills/engineering-build/`, needs a hash refresh.

## Refresh hashes and test

From the repository root:

```bash
python speckit-extensions/engineering-build/scripts/verify_lock.py --ext speckit-extensions/engineering-build --skills skills --update
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```

Installs are exercised against real temporary Spec Kit projects when `specify` is on PATH.

## Release

Bump `extension.version` in `extension.yml`, the preset version and its `requires.extensions` range, and `skills/engineering-build/VERSION`. Then:

```bash
python installer/install.py package --output dist
```

This writes `dist/engineering-build-<version>.zip` (the staged extension with its skills, plus the preset) and its `.sha256`. Publish both, and fill `download_url` and `sha256` in `catalog/engineering-build.json`. Consumers install a release with `install.py install --source url --url <zip> --sha256 <hash>` or `--source bundle --bundle <zip>`.
