# Adapter: grill-me (stage `clarify`)

Skill: `skills/grill-me/grilling.md` is the interview loop; `skills/grill-me/grill-me.md` explains intent and pitfalls. Both are vendored unmodified.

## Mismatches this adapter handles

The skill expects a fresh conversation, plan mode off, and writes no files. Clarify runs inside an existing session and must write to `spec.md`. So:

- Tell the user once to run clarify outside plan mode.
- Run the interview with no file writes. After the interview ends, perform all file writes yourself.

## Inputs

- Starting idea: the active `spec.md` and `.specify/memory/constitution.md`. Do not ask anything they already answer.
- Settings from the binding: `interaction`, `max_rounds`, `split_threshold`, `edge_case_lenses`.

## Procedure

1. Follow the skill's rounds: each round asks the whole frontier (every question whose prerequisites are answered). If `interaction: one-at-a-time`, ask a single question per turn.
2. Treat each edge-case lens as an extra branch. Every lens ends either answered or explicitly N/A.
3. Accept "I don't know". Record it as an open assumption, never a silent default.
4. When a question needs something to react to (layout, feel), stop grilling it and record `Deferred: needs prototype`.
5. Facts the repo can settle are looked up, not asked. Decisions belong to the user; never answer them yourself.
6. Stop when the frontier is empty, the user says stop, or `max_rounds` is reached.
7. If the question count passes `split_threshold`, advise splitting the feature into smaller specs.

## Outputs

- `spec.md`: add `### Session <YYYY-MM-DD>` under `## Clarifications` (create the heading if absent) listing every question and answer. A second session on the same date gets `(2)`. Update affected requirement, edge-case and assumption sections in place. Never duplicate an existing bullet.
- Open assumptions and deferred items go under `## Assumptions` as `- [open] ...` and `- [deferred: needs prototype] ...`.

## Quality gate

Every lens is answered, N/A with a reason, or listed as an open assumption.
