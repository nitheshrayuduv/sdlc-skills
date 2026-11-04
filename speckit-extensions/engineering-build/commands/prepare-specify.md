---
description: Prepare Engineering Build guidance before specify
---

# Prepare specify

Read `.specify/extensions/engineering-build/hooks.md` and follow its shared rules.

Read the feature request and relevant repository boundaries. Carry forward user goals, compatibility, sensitive data, constraints and observable acceptance criteria. Do not select an older feature, create a branch/folder, write technical design, or decide product questions for the user. Let the core specify command create and identify the new feature.

Tell the calling stage that this hook only prepared context: it did not create a branch or emit BRANCH_NAME/FEATURE_NUM. Spec Kit 1.2.0's branch-creation paragraph assumes a Git hook; use branch metadata only if another hook actually supplied it. Do not invent metadata or treat this hook's success as evidence of branch creation.

Apply the **Specify** guidance in the stage map. Return a concise context/check result to the calling stage. Do not invoke another Spec Kit command.
