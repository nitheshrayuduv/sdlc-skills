# Feature design

## Describe the change clearly

Start with current behavior and the requested difference. Cite the current implementation and link existing onboarding pages rather than copying them. Give enough context to understand the proposal when no onboarding guide exists. Mark the proposal as not yet implemented.

Use a small change map: area, current code, planned change, reason. Identify shared libraries, existing clients and stored data affected by compatibility. State non-goals. Discuss alternatives only when the choice matters; do not force three designs for a small change.

## Design each affected area

| Area | Specify |
| --- | --- |
| Architecture and module design | Responsibilities, boundaries, dependency direction, public interfaces, internal collaboration, state/lifecycle, extension points |
| End-to-end flow | Trigger, validation, permissions, business work, transactions, external calls/events, result and failure paths |
| Database | Current schema evidence; added/changed tables, fields, types, constraints and indexes; query changes, data invariants, migration order and compatibility |
| API/events | Apply [API and integration planning](api.md) for affected contracts, behavior and consumers; skip for changes without interface impact |
| Frontend | User journey, routes, components, state ownership, form rules, loading/empty/error states, accessibility, API interaction and permission feedback |
| Operations | Configuration, jobs, resource/time limits, logs/metrics/traces, rollout and recovery behavior |

Mark inapplicable areas once. For database changes, inspect the active Liquibase/Flyway roots and the affected objects' full history, including later alterations, baselines, conditions and repeatables. Do not treat a model class as proof of the deployed schema. Preserve unresolved history. Use a new migration for applied history; use engine/version-correct behavior. Plan existing-data checks, staged expansion, restartable backfill/reconciliation and safe contraction when needed. Explain irreversible changes.

Do not expose internal persistence models by default. For UI work, specify observable behavior, including failed requests and stale responses, not only the component names. API/event contract examples and retry behavior belong to the linked API guide.

## Use diagrams to explain the proposal

Keep Mermaid in design.md, or in a directly linked design page for a large feature. Show a component view of affected modules and a sequence for a key new/changed journey. Add state/ER diagrams when state/data changes matter. Label Current and Proposed explicitly. Link unchanged diagrams rather than reproducing them.

Use short names, labeled arrows, boundaries and no more than five nodes across. Split large views. Explain the main point in one sentence; do not rewrite every arrow in prose. Cite existing nodes and label proposed files/interfaces. Use local rendering if available and say when rendering was not checked.

## Choose standards and patterns

List only standards relevant to the change, with their source and where they apply. Include naming/lint, module boundaries, errors, logging/redaction, validation, data access, contracts and tests as needed. Identify one repository example to follow. Separate required policy from a new proposal.

For a pattern, explain the concrete problem, the places it applies, a simpler alternative, and the maintenance cost. Do not default to microservices, CQRS, DDD, a new framework or a broad rewrite. If existing conventions are unsafe or incompatible with the feature, explain the exception and the rule proposed to replace them.

## Make security concrete

Use a small table: risk/scenario, required control, enforcement point, linked implementation task/check. Consider identity spoofing, cross-tenant or cross-object access, privilege changes, unsafe inputs, sensitive data/logs, secrets, untrusted integrations and resource abuse. Tailor the list to actual feature entry points.

Inspect global middleware and downstream policies before assuming enforcement is missing. Client-side visibility is not server authorization. Permission checks should also cover background jobs and alternate entry points. Never use real tokens or personal data in examples.
