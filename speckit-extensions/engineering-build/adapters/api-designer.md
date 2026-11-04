# Adapter: api-designer (stage `plan`, binding `plan-api`)

Skill: `skills/api-designer/SKILL.md` and its `references/`.

Runs only when detector `api_change` returns `yes` (or the user answers yes to the one `unknown` question). The skill covers REST and GraphQL. For gRPC or event contracts, record `unsupported style` and skip with a warning.

## Inputs

Domain requirements from `spec.md`; the data model from `data-model.md` (so resources follow the agreed entities); the auth approach from the constitution or `plan.md`; and any existing OpenAPI file in the repo.

## Outputs

| Skill deliverable | Lands in |
| --- | --- |
| Resource model and relationships | `plan.md`, `## API Design` |
| Endpoint specifications | `contracts/` summary table |
| OpenAPI 3.1 YAML | `contracts/openapi.yaml` (edited in place when one exists) |
| Auth and authorization flows | `plan.md`, `## API Design` |
| Error catalog (RFC 7807 `type` URIs), pagination and filtering, versioning and deprecation | `contracts/openapi.yaml` plus a short summary in `plan.md` |
| Lint result | `plan.md`, `## Quality Gates`, `### API` |

## Verification

Run `npx --yes @redocly/cli@1 lint contracts/openapi.yaml` and a Prism mock check (`npx --yes @stoplight/prism-cli@5 mock contracts/openapi.yaml`, then request one endpoint) when `npx` and network are available. Pinned tool versions keep results reproducible. Otherwise record the check as skipped with the reason, as a warning. With `required: true`, a failing lint blocks the plan.

## Breaking changes

When an OpenAPI file already existed, add a `### Breaking changes` note to `plan.md` listing each breaking change and its migration path, or the words `none`. This enforces the skill's rule against breaking changes without a note.

## Hand-off to tasks

State in `plan.md` that `contracts/openapi.yaml` is the source of truth so `speckit.tasks` can generate contract-test and mock-server tasks from it.
