# sdlc-skills (Spec Kit extension)

Runs vendored, version-pinned skills at Spec Kit stages through a binding registry. Spec: [docs/specs/spec-kit-extension-spec.md](../../docs/specs/spec-kit-extension-spec.md). It works with the [org-sdlc preset](../org-sdlc/README.md), which wraps the core commands to call it.

| Stage | Skill | Runs when |
| --- | --- | --- |
| `clarify` | grill-me | Always |
| `plan` | database-schema-designer | Detector `db_change` says yes |
| `plan` | api-designer | Detector `api_change` says yes |
| `tasks`, `implement` | playwright-expert | `[E2E]` task, or a matching test path |

## Layout

- `extension.yml`: commands `speckit.sdlc-skills.run` and `speckit.sdlc-skills.edge-case-audit`, optional `after_clarify` hook.
- `config/sdlc-skills-config.template.yml`: the binding registry. Overrides go in `.specify/extensions/sdlc-skills/sdlc-skills-config.yml` or `.local.yml`.
- `adapters/`, `detectors/`: glue between Spec Kit artifacts and each skill, and the yes/no/unknown applicability checks.
- `skills/` and `skills.lock.yml`: unmodified vendored skills, pinned by upstream commit and SHA-256. Each keeps its MIT `LICENSE`.
- `scripts/verify_lock.py`, `scripts/check_playwright_rules.py`.

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
python -m unittest speckit-extensions/sdlc-skills/tests/test_extension.py -v
```
