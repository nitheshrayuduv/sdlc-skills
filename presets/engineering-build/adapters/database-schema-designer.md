# Adapter: database-schema-designer (stage `plan`, binding `plan-db`)

Skill: `skills/database-schema-designer/SKILL.md` and its `references/`.

Runs only when detector `db_change` returns `yes` (or the user answers yes to the one `unknown` question).

## Inputs, derived before asking

Fill each from existing artifacts and ask only for gaps.

| Skill input | Derived from |
| --- | --- |
| Database engine and version | `plan.md` Technical Context (Storage), then repo files. The constitution wins over the skill's PostgreSQL default |
| Entities and relationships | Key Entities and requirements in `spec.md` |
| 5-10 key queries | User stories and functional requirements, written out with filters and sort order |
| Volume, growth, read/write mix | Non-functional requirements, else asked |
| Tenancy, retention, audit, PII | Constitution and `spec.md`, else asked |
| ORM or migration tool | Detected from the repo (Alembic, Flyway, Prisma, EF Core, Liquibase and so on) |

## Outputs

- `data-model.md`: entities, ERD, constraints, and an index table mapping each index to the query it serves. Edit in place when the file exists.
- `<feature_dir>/db/`: draft DDL and reversible migrations. Never write into the application tree; `tasks` turns them into implementation tasks.
- `plan.md` under `## Quality Gates`, a `### Database` checklist copied from the skill's pre-delivery checklist, each item `pass`, `fail` or `n/a`. Examples: every foreign key has an `ON DELETE` rule and an index, timestamps are timezone-aware, destructive rollbacks are flagged.

## Verification

If a database is reachable, run the DDL and `EXPLAIN` the key queries. Otherwise walk each query against the schema by hand and say so in `plan.md`. A failed or skipped check is a warning, not a stop, unless the binding sets `required: true`.

## Ordering

Runs before `plan-api`, so API resources are modeled on the agreed data model.
