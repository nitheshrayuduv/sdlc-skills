# sdlc-skills (Spec Kit extension)

Runs vendored, version-pinned skills at Spec Kit stages through a binding registry. Spec: [docs/specs/spec-kit-extension-spec.md](../../docs/specs/spec-kit-extension-spec.md). It works with the [org-sdlc preset](../org-sdlc/README.md), which wraps the core commands to call it.

| Stage | Skill | Runs when |
| --- | --- | --- |
| `clarify` | grill-me | Always |
| `plan` | database-schema-designer | Detector `db_change` says yes |
| `plan` | api-designer | Detector `api_change` says yes |
| `tasks`, `implement` | playwright-expert | `[E2E]` task, or a matching test path |
| `plan`, `tasks`, `implement.vuln-upgrade` | engineering-vulnerability-upgrade | Detector `vuln_report` says yes, or a `[VULN]` task |

## Layout

- `extension.yml`: commands `speckit.sdlc-skills.run` and `speckit.sdlc-skills.edge-case-audit`, optional `after_clarify` hook.
- `config/sdlc-skills-config.template.yml`: the binding registry. Overrides go in `.specify/extensions/sdlc-skills/sdlc-skills-config.yml` or `.local.yml`.
- `adapters/`, `detectors/`: glue between Spec Kit artifacts and each skill, and the yes/no/unknown applicability checks.
- `skills/` and `skills.lock.yml`: unmodified vendored skills, pinned by upstream commit and SHA-256. Each keeps its MIT `LICENSE`.
- `scripts/verify_lock.py`, `scripts/check_playwright_rules.py`.

## Vulnerability upgrade from a scanner report

Spec: [engineering-vulnerability-upgrade-spec.md](../../docs/specs/engineering-vulnerability-upgrade-spec.md). Run `speckit.sdlc-skills.vuln-intake` (asks flow, ticket reference, branch, base branch and report file; reads the report; seeds `spec.md`). Then plan, tasks and implement run the `engineering-vulnerability-upgrade` bindings: locate and decide at plan, `[VULN]` tasks per repo, apply and build at implement. The `after_implement` hook `speckit.sdlc-skills.vuln-pr` raises one PR per changed repo, only after every build passed and you confirm.

Describe your chain in `config/vuln-flows.json`: `flows` (repos in build order), `handoff` (which file and key in a later repo pins an earlier repo's version) and the build tool (`gradle` or `maven` preset, or explicit commands; per repo via `repo_overrides`). The shipped file is a generic example; `installer/install.py update` keeps your project's values. Scripts are in `scripts/vuln/` (Python 3.10+, standard library only) and are tested by `tests/test_vuln_scripts.py`.

## Audit trail

Every run or skip is written to `specs/<feature>/skill-runs.md`, and `plan.md` gets a `## Skill Applicability` table. Open those files to see which skills were applied and why.

## Add a stage-to-skill pairing

1. Vendor the skill into `skills/<id>/` (keep its license) and run `python scripts/verify_lock.py --ext . --update` after adding its entry to `skills.lock.yml`.
2. Write `adapters/<id>.md`.
3. If the trigger needs judgment, add `detectors/<name>.md`.
4. Add a binding to the registry.
5. Run the tests.

## Update a vendored skill

Copy the new upstream version in, update `commit` and `version` in the lock, run `--update`, review the diff and run the tests.

## Tests

```bash
python -m unittest discover -s speckit-extensions/sdlc-skills/tests -v
```
