---
description: Ask for flow, ticket, report, branch and base branch, then read the vulnerability report
---

# Vulnerability intake

Read `.specify/extensions/engineering-build/skills/engineering-vulnerability-upgrade/SKILL.md` and follow it. Scripts are in `.specify/extensions/engineering-build/scripts/vuln/`; run them with `python`. Pass `--config` only if the project has its own copy of the flow config. The default is `.specify/extensions/engineering-build/config/vuln-flows.json`.

## Feature folder

Resolve the feature folder (`FEATURE`) the way Spec Kit does, so later stages use the same one:

1. If `.specify/feature.json` exists, use its `feature_directory`.
2. Otherwise create `specs/NNN-vuln-upgrade-<ticket in lower case>`, where `NNN` is the next free three-digit number under `specs/` (`001` when there is none), and write `{"feature_directory": "<that path>"}` to `.specify/feature.json`.

Do not invent another name such as `specs/vuln`.

## Ask these, in order

Wait for each answer. Skip a question only if the user already gave the answer in this request.

1. **Flow:** one of the flow names in the flow config (list them from `flows` in `vuln-flows.json`).
2. **Ticket ID:** the work item in your tracker (for example `PROJ-123`). It names the branch, the feature folder and the PRs.
3. **Vulnerability report:** a file path (a scanner export, or the ticket's text saved as text, HTML or JSON), or the report pasted in chat. Save a pasted report to `FEATURE/vuln/report.txt` as given.
4. **Branch** to work on (default `vuln/<ticket>`).
5. **Base branch** (parent branch): the branch the working branch is created from in every repo where it does not exist yet, and the branch the PRs target. Ask it in those words: "Which base branch should the working branch be created from?" Always ask, even if the branch already exists in some repos. Suggest a default from the branch name when it carries a version line, using the team's branch for that line when one exists (for example `PROJ-123-1.4.x` suggests `1.4.x-maintenance`); otherwise suggest nothing. Also ask whether any repo needs a different base branch (for example a repo with no branch for that line).

## Then

1. Run `intake.py --flow F --ticket T --branch B --base PARENT --feature-dir FEATURE`, adding `--base-for REPO=BRANCH` for each repo with a different parent.
2. Run `prepare_branches.py --check-only --feature-dir FEATURE`. It prints which repos already have the branch and `MISSING: ...` for the rest. For each missing repo, check that the base branch exists there (`git -C <repo> branch -r --list origin/PARENT`); if it does not, tell the user which repos lack it and ask for a base branch for those, then run `intake.py` again with `--base-for`. Do not create branches here.
3. Run `read_report.py --report REPORT --ticket T --out FEATURE/vuln/findings.json`. It reads the file only and never calls a tracker or the network. If it exits 4, the report holds no vulnerable and fixed versions: show the user what was read and ask for the right report.
4. Show the findings table (dependency, vulnerable, fixed, severity, images, status). Say which rows are out of scope (OS packages) and which fix version was chosen where a package had several. If the report header names a different flow from the one chosen, say so.
5. Ask the user to confirm the table. For each `needs-confirmation` row, fix it in `findings.json` with the user's answer or remove it.
6. Seed `FEATURE/spec.md` with a short problem statement, the ticket ID, where the report came from, the branch and base branch, and the confirmed table, so the normal specify, clarify, plan and tasks stages have a real spec.

Make no file changes in any repo. Stop after step 6 and tell the user the next step is the normal plan stage. The `plan-vuln-upgrade` binding then runs because `FEATURE/vuln/intake.json` exists.
