---
description: Raise one PR per changed repo when every build passed
---

# Raise PRs

Resolve the feature folder (`FEATURE`). If `FEATURE/vuln/intake.json` does not exist, this feature is not a vulnerability upgrade: say `no vulnerability upgrade in this feature, skipping` and stop. Otherwise read `.specify/extensions/engineering-build/skills/engineering-vulnerability-upgrade/SKILL.md`. Scripts are in `.specify/extensions/engineering-build/scripts/vuln/`.

1. Run `raise_prs.py --feature-dir FEATURE` without `--yes`. If it exits 6, builds did not all pass: report the failed repo and stop. No branch is pushed and no PR is created after a failed build, whatever `required` says.
2. Show the PR plan: each repo, branch, target branch and files. Pushing a branch and opening a PR is outward-facing, so ask the user to confirm. When the `impl-vuln-upgrade` binding sets `confirm_before_pr: false`, skip the question.
3. Only after a clear yes, run it again with `--yes`. Add `--base BRANCH` only if the user names a target for branches that already existed.
4. Report each PR URL and the ticket ID. Do not merge anything.
5. Record the PR URLs in `FEATURE/skill-runs.md` on the row for `impl-vuln-upgrade`.
