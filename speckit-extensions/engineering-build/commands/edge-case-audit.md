---
description: Check every edge-case lens is answered or marked N/A
---

# Edge-case coverage audit

Read the `clarify-grill` binding's `edge_case_lenses` from the merged registry (see `.specify/extensions/engineering-build/commands/run.md`, section 1) and open the active feature's `spec.md`.

For each lens, find an answer under `## Clarifications` or a requirement, edge case or assumption that covers it. Mark each lens exactly one of:

- **answered**: quote the spec line;
- **N/A**: the spec says why the lens does not apply;
- **open**: no answer and no reason.

Print a short table of lens, status and evidence. Add the table to `<feature_dir>/skill-runs.md` under `## Edge-case audit`, replacing any earlier audit table. Do not edit `spec.md`. If any lens is open, list the open lenses and suggest re-running `/speckit.clarify`. This audit is advisory and never blocks.
