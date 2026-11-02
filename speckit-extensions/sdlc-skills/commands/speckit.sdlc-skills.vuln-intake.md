---
description: Ask for flow, Agility ticket and branch, then read the vulnerability report
---

# Vulnerability intake

Read `.specify/extensions/sdlc-skills/skills/engineering-vulnerability-upgrade/SKILL.md` and follow it. Resolve the current feature folder (`FEATURE`). Scripts are in `.specify/extensions/sdlc-skills/scripts/vuln/`; run them with `python`. Pass `--config` only if the project has its own copy of the flow config. The default is `.specify/extensions/sdlc-skills/config/vuln-flows.json`.

Ask these in order and wait for each answer. Skip a question only if the user already gave the answer in this request.

1. **Flow:** deploy or release.
2. **Agility ticket number.**
3. **Branch** to work on (default `vuln/<ticket>`).

Then:

1. Run `intake.py --flow F --ticket T --branch B --feature-dir FEATURE`.
2. Run `prepare_branches.py --check-only --feature-dir FEATURE`. It prints `MISSING: ...` for repos without the branch. If any are missing, ask for the **parent branch**, and ask whether any repo needs a different one. Run `intake.py` again with `--base PARENT` so the answer is recorded. Do not create branches here.
3. Run `agility_fetch.py --ticket T --out FEATURE/vuln/findings.json`. It needs `AGILITY_TOKEN` and `AGILITY_URL` in the environment. If they are missing, tell the user to set them and stop; never ask for the token in chat.
4. Show the findings table (dependency, vulnerable, fixed, severity, images, status). Say which rows are out of scope (OS packages) and which fix version was chosen where a package had several. If the ticket header names a different flow from the one chosen, say so.
5. Ask the user to confirm the table. For each `needs-confirmation` row, fix it in `findings.json` with the user's answer or remove it.
6. Seed `spec.md` with a short problem statement, the ticket number and the confirmed table, so the normal specify, clarify, plan and tasks stages have a real spec.

Make no file changes in any repo. Stop after step 6 and tell the user the next step is the normal plan stage. The `plan-vuln-upgrade` binding then runs because `FEATURE/vuln/intake.json` exists.
