# Maintain and release

[Back to overview](../README.md)

## Where things live

| Change | Edit |
| --- | --- |
| Engineering guidance shared by every stage | `skills/engineering-build/` (repository root) |
| What Engineering Build does before or after a core command | `commands/speckit.<stage>.md` |
| Which companion skill runs when | `bindings.yml` |
| How a skill reads Spec Kit artifacts and where its output goes | `adapters/<skill>.md` |
| An applicability decision | `detectors/<name>.md` |
| Rules shared by every stage, and how bindings are applied | `guide/` |

## Add a companion skill

1. Put the skill in the repository's top-level `skills/<id>/`, unmodified, with its `LICENSE`.
2. Add an entry to `skills.lock.yml` (source URL, commit, license, version, `sha256: pending`).
3. Write `adapters/<id>.md`; add `detectors/<name>.md` if the trigger needs judgment.
4. Add a binding to the registry. Triggers: `always`, `detect`, `task_tag`, `path_glob`, `any`, `all`.
5. Refresh hashes and run the tests (below). If the skill belongs to a stage with no bindings yet, add a line to that wrapped command telling it to follow `guide/bindings.md` for the stage.

To upgrade an upstream skill, copy the new version in, update `commit` and `version` in the lock, refresh the hashes, review the diff and run the tests. Any edit to a shipped skill, including `skills/engineering-build/`, needs a hash refresh.

## Refresh hashes and test

From the repository root:

```bash
python speckit-extensions/engineering-build/scripts/verify_lock.py --preset speckit-extensions/engineering-build --skills skills --update
python -m unittest discover -s speckit-extensions/engineering-build/tests -v
```

Installs are exercised against real temporary Spec Kit projects when `specify` is on PATH.

## Release

Bump `preset.version` in `preset.yml` and `skills/engineering-build/VERSION`, then refresh the hashes. Then:

```bash
python speckit-extensions/install.py package --output dist
```

This writes `dist/engineering-build-<version>.zip` (the staged preset with its skills) and its `.sha256`. Publish both, and fill `download_url` and `sha256` in `speckit-extensions/catalog.json`. Consumers install a release with `install.py install --source url --url <zip> --sha256 <hash>` or `--source bundle --bundle <zip>`.
