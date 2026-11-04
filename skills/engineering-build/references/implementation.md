# Implementation plan

## Make tasks actionable

Use short task IDs such as T1. Each task needs: purpose, existing/planned files, implementation steps, prerequisites, linked requirements/security controls, and a test or observable done condition. Keep these details together in tasks.md for Spec Kit, or implementation.md for a standalone plan. A title such as “Implement backend” is not enough.

Sequence contract/data preparation, core behavior, adapters/UI, testing and release by actual dependencies. Keep tasks small enough to review. Include cleanup only when needed for this feature. Do not generate tickets or assign people unless asked. If a review finding is a prerequisite, link its existing finding rather than restating it.

Keep one compact requirement coverage table: requirement, task(s), validation. Write the requirement itself only in spec.md for Spec Kit, or README.md for a standalone plan. For Spec Kit, keep contracts in its contracts/ files when present; otherwise use the design document. Put detailed security risks/controls only in their chosen section or security.md. Tasks reference them by readable links.

## Plan useful tests

Choose checks based on risk, not a fixed quota. Cover changed business rules, negative/permission cases, contract compatibility, integration boundaries, database upgrades, UI interactions, concurrency/retries and recovery where applicable. Explain setup, action and expected outcome. Use synthetic fixtures, not production personal data.

For API or integration changes, use the relevant checks in [API and integration planning](api.md). Link them to tasks here; keep contract details in their existing owning file.

Distinguish existing tests to extend from planned tests. Include both fresh install and upgrade paths for relevant schema changes, old/new application coexistence, existing invalid data, partial failure and retry recovery. Do not claim any test passed unless run and recorded. Static inspection is not performance measurement; say what measurement would settle a performance assumption.

## Plan release and recovery

Explain preparation, data prechecks, configuration, deployment sequence, backfill/reconciliation, verification, monitoring and cleanup. Decide whether a feature flag helps and who/what activates it without inventing a named owner. Tie release gates to observable outcomes.

State compatibility during rollout. Identify lock/rewrite and resource risks using the actual database/version and known data size. Avoid an unconditional zero-downtime claim. A rollback script cannot restore deleted data by itself; specify restore requirements or forward recovery and any point after which rollback is unsafe.

## Check readiness

Every accepted requirement has a task and a way to verify it. Every important security risk has a control and a test. Every breaking change has a transition plan. Every unknown that changes the design is marked with the decision needed. Every diagram/contract agrees with the task list. Remove repeated explanations and keep the plan readable.
