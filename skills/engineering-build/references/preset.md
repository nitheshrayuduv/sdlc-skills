# Native Spec Kit preset

Use Spec Kit 1.2.0 or later within major version 1, installed separately in the target repository (`specify init`). Engineering Build ships as one Spec Kit preset, `engineering-build`, from `presets/engineering-build/` in the sdlc-skills repository. `presets/install.py` installs it.

The preset wraps the six core commands: constitution, specify, clarify, plan, tasks and implement. Each wrapped command has an **Engineering Build: before** section that prepares the stage and an **Engineering Build: after** section that completes and checks the stage's artifacts, around the unchanged core steps. The companion skills run at a fixed point inside the stage: grill-me before the core clarify steps, database-schema-designer and api-designer after the core design draft, playwright-expert after task generation, and ponytail and playwright-expert for each implement task. The preset also holds the binding registry (`bindings.yml`), adapters, detectors and shared rules (`guide/`).

The skills themselves live once, in the repository's top-level `skills/` folder. The installer copies the ones listed in the preset's `skills.lock.yml` (this skill and its companions) into the staged preset, checks each SHA-256, and runs `specify preset add`. They end up in `.specify/presets/engineering-build/skills/`, where every agent Spec Kit supports can read them as plain instruction files.

Keep the source checkout separate from applications. Each target owns its constitution, binding overrides (`.specify/engineering-build.yml`) and feature outputs. Updates to the shared source do not automatically update target installations; run the installer's `update` command. Keep using the core commands.

Feature artifacts remain in the resolved Spec Kit feature directory: spec.md, plan.md and tasks.md remain the entry points, with `skill-runs.md` as the record of which companion skills ran or were skipped and why.

This preset does not require an API key, launch a background agent, or run a CI gate. It uses the active coding agent session. The wrapped commands are agent instructions; actual execution still depends on the coding agent. Verify the transcript and artifacts on a sample feature.

Earlier releases shipped an `engineering-build` extension plus an `engineering-build-preset` preset. The installer removes both and moves the old binding config to `.specify/engineering-build.yml`. When migrating from the older `engineering-plan` extension or the `sdlc-skills` extension with the `org-sdlc` preset, remove them with the supported remove commands first. Then run `/speckit-constitution` once so the Engineering Build principle and its links point at the preset. Do not delete existing feature documents or other extensions.
