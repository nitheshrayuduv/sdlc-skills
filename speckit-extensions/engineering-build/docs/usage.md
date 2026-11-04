# Workflow and outputs

[Back to overview](../README.md)

Keep using the standard Spec Kit commands. For Copilot/Claude with the default skills layout:

```text
/speckit-specify <feature description>
/speckit-clarify
/speckit-plan
/speckit-tasks
/speckit-implement
```

For Codex, use the corresponding $speckit- names. Clarify runs when you choose that stage; the extension does not automatically launch every stage. Implementation requires an explicit implementation request.

Companion skills run inside those same commands; you do not call them. grill-me interviews you at clarify; database-schema-designer and api-designer review the plan when the data model or an API changes; playwright-expert shapes `[E2E]` tasks and tests; ponytail keeps every implement task to the smallest complete change (set `settings.level` on `impl-minimal` to `lite`, `full` or `ultra`). For a vulnerability ticket, start with `/speckit-engineering-build-vuln-intake`. To turn a skill off for one repository, set `enabled: false` on its binding in `.specify/extensions/engineering-build/engineering-build-config.yml`.

Before hooks prepare context and return to the current stage. After hooks complete or check the stage's documents. They never invoke core commands recursively. A direct extension command performs only its named action.

## One home for each topic

Use the feature folder selected by Spec Kit, never the folder with the newest modification time.

| File | Purpose |
| --- | --- |
| spec.md | Requirements, user behavior and acceptance criteria |
| plan.md | Technical approach, standards, patterns, rollout and links |
| tasks.md | The single task checklist and requirement-to-task-to-check mapping |
| research.md | Technical decisions and unresolved choices, when needed |
| data-model.md and contracts/ | Canonical data and API/event definitions |
| engineering/design.md | Design diagrams and detail when plan.md becomes too large |
| engineering/security.md | Risks and controls when a separate page helps |
| engineering/validation.md | Checks actually run and remaining implementation gaps |
| skill-runs.md | Which companion skills ran or were skipped, with evidence and pinned version |

Small designs and security sections stay in plan.md. Link spec.md to the plan; link the plan to tasks and supporting documents. Create links after their targets exist. Do not create a second plan under docs/plans or copy API definitions between documents. Use plain English in every output, including chat responses.

## Project-specific standards

The extension reads each target repository's instructions, constitution, code and accepted specifications. Put team-specific standards in those project files. Shared rules can evolve in this extension repository. Keep project names, architecture assumptions and feature documents out of shared extension commands.

## What checks mean

Hook registration is deterministic, but following a hook and producing a sound design depends on the coding agent. Missing context must be reported. Do not claim tests ran without execution evidence. This extension does not enforce a GitHub PR gate, run migrations, deploy an application, or approve a PR.

After a Spec Kit or extension update, verify a representative feature, generated command dispatch and output links. If hooks are missing, check [Installation](install.md); do not keep two Engineering Build integrations active to compensate.
