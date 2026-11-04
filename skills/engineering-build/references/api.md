# API and integration planning

Read this guide when a feature changes an API contract, its observable behavior, access rules, or an external integration. Include affected APIs even when their endpoint signatures stay unchanged. For a local change with no interface impact, skip this guide and do not create API documents. This is part of Engineering Build, not a full API audit. When the api-designer companion skill runs at plan, it owns the contract itself (`contracts/openapi.yaml`, error catalog, pagination, versioning); use this guide for consumer compatibility, permissions, failure handling and verification around that contract.

## Establish the contract and consumers

Trace the changed operation through routing, middleware, validation, service logic and storage or downstream calls. Find consumers, SDKs, frontend calls, jobs and existing contract tests. Record inspected paths and unknown consumers. Identify the authoritative contract and how it is produced: design-first schema, code-generated schema, protocol definition, or an existing written interface. Do not treat a generated file as the editable source without checking its build process.

Use the repository's protocol, conventions and supported schema version. For HTTP APIs, use an existing OpenAPI definition when available. Do not upgrade its version or introduce a generator just to complete a plan. For GraphQL use its schema and resolver behavior; for RPC use the service/message definitions; for events use the message contract. A library interface does not need an HTTP facade or OpenAPI file.

Keep one authoritative definition. In Spec Kit, place a proposed contract under the feature's contracts/ when needed, or link the existing authoritative repository contract and describe the planned delta. State which source will change during implementation and how generated outputs are refreshed. Do not maintain an independent copy of an existing specification. In a standalone plan, use the existing design document or a linked contract file. Never generate a separate api-plan.md that repeats plan.md.

## Define the observable behavior

Cover only the rows that apply to the affected operation. Put the details in its owning contract rather than copying this checklist into every plan.

| Topic | Decisions the implementation needs |
| --- | --- |
| Operation | Consumer, purpose, protocol operation or HTTP method/path, stable identifier, and side effects |
| Input | Field location and type; required, omitted and null behavior; defaults; allowed values, length/range limits; unknown-field handling; units, timezone and precision where relevant |
| Output | Fields and visibility, media type, status/outcome, relevant headers, and examples that match the schema |
| Errors | Invalid input, unauthenticated/forbidden access, missing resources, conflicts, rate limits and downstream failures as applicable; stable machine-readable codes and safe messages |
| Collections | Bounded page size, cursor/offset behavior, stable ordering and tie-breaker, filter/sort allowlists, and behavior as data changes between pages |
| Updates | Partial versus replacement semantics, omitted/null fields, concurrent updates, conflict detection and the caller's recovery action |
| Resource use | Payload/upload/query/batch limits, timeout and cancellation, admission/rate limits, and how clients recognize retryable outcomes |
| Caching | Cacheability, invalidation, validators and correct user/tenant variation when caching is used |

For HTTP, follow the chosen methods' and status codes' semantics. A successful acceptance response for background work is not proof of completion. Specify how clients check completion and failure. Retain established error formats unless a change is justified; RFC 9457 Problem Details is an option for HTTP errors, not a mandatory migration. Do not return stack traces, secret values or another tenant's data in errors.

Provide a small synthetic success example and a relevant failure or boundary example. Include headers only when they affect behavior. For non-HTTP interfaces, express equivalent outcomes in their native error/result model instead of inventing HTTP codes.

## Specify access at each boundary

Identify the authenticated actor and how the server derives trusted identity and tenant context. For each changed operation, cover operation-level permission, access to the requested object, and which input/output fields that actor may write or read. Apply this to nested objects, list/search results, bulk actions, status endpoints and callbacks where present. Do not rely on hidden UI controls or an unverified tenant ID supplied by the client.

Separate writable fields from server-owned fields to prevent unauthorized property changes. Trace existing middleware and shared checks before proposing new enforcement. Link API-specific controls to the feature's security section; do not write the same risk twice.

For browser callers, assess cookie-based CSRF protection and the existing CORS policy where applicable. CORS does not replace authorization. For third-party APIs, validate responses as untrusted data, restrict destination URLs/redirects when callers can influence them, bound response size/time, and redact sensitive values. For signed callbacks, define signature verification, replay handling and secret rotation when those mechanisms are used. Do not invent credentials or call live providers during planning.

## Design retries and asynchronous work

For a retried write, state what can be repeated and how duplicate effects are prevented. If using an idempotency key, define its scope, request comparison, retention, same-key/different-request outcome, concurrent claim behavior, and replay result after success or failure. Explain how recording the key and performing the effect remain consistent, including a crash or a lost response. A unique key alone does not prove end-to-end exactly-once execution across external systems.

For downstream calls, define deadlines, retryable errors, retry limits/backoff and overload behavior using existing client conventions. Do not blindly retry non-idempotent writes or assume a timeout means nothing happened. Resolve an uncertain outcome before repeating a side effect when required.

For jobs, events or webhooks, distinguish submission, delivery, acknowledgement and completed business work. Define correlation, ownership checks, ordering, deduplication, partial failure, redelivery, cancellation and recovery only where relevant. Keep schema details in the message contract and put the important success/failure sequence beside the design explanation.

## Preserve compatibility

Compare old and proposed contracts and behavior for the consumers found. Consider added required inputs, removed/renamed fields, narrowed ranges, nullability/default changes, new enum values, changed errors and permissions, paging changes and SDK serialization. Even an additive field can affect a strict consumer. Record unknown consumer behavior as an evidence gap; do not promise compatibility from the word “additive.”

Follow the repository's versioning and deprecation policy. For a breaking change, define the transition, old/new coexistence, consumer update order, completion check and rollback limits. Do not automatically create a new API version for every feature. Include published documentation and client generation work when those are part of the contract release process.

## Turn the contract into checks

Select checks that address this change's actual risks. Reuse repository tooling; propose missing tooling explicitly rather than installing it during planning. A schema linter alone does not prove runtime behavior or authorization.

- Validate the changed schema and its examples; compare the proposed contract with the accepted baseline using supported tooling when available.
- Exercise input boundaries, omitted/null values, relevant error outcomes and prohibited writable fields.
- Check unauthorized operation/object/tenant access and response-field visibility, including lists or bulk operations if affected.
- Check old-consumer compatibility, generated-client behavior and contract/runtime agreement at the relevant integration boundary.
- For changed writes or jobs, test concurrent requests, duplicate requests, failure after a side effect, lost responses, retries and recovery.
- For changed reads or integrations, test paging stability, resource limits, caching boundaries and malformed/slow downstream responses where relevant.

During specify/clarify, surface consumer expectations and unresolved behavior without forcing implementation choices. During plan, settle the contract and its proposed checks. During tasks, link those checks to the single task list and requirement coverage table. During implement, verify the implemented handler/schema/client agree and record checks actually run in the normal validation artifact. If a missing decision affects permissions, compatibility or side effects, state that blocker before calling the design ready.

Sources and their scope are recorded once in [Sources](sources.md). Use technology/version-specific primary documentation when applying this guide to a real repository.
