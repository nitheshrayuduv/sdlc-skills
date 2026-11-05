# Native Spec Kit extension

Use Spec Kit 1.2.0 or later within major version 1, installed separately in the target repository (`specify init`). Engineering Build then ships as two Spec Kit packages from the sdlc-skills repository, installed together by `speckit-extensions/install.py`:

| Package | Source | What it does |
| --- | --- | --- |
| Extension `engineering-build` | `speckit-extensions/engineering-build/` | Twelve mandatory before/after hooks on constitution, specify, clarify, plan, tasks and implement; the binding runner `speckit.engineering-build.run`; adapters, detectors and the binding registry for the companion skills |
| Preset `engineering-build-preset` | `speckit-extensions/engineering-build/preset/` | Wraps clarify, plan, tasks and implement so the runner is called at the exact point inside each stage |

The skills themselves live once, in the repository's top-level `skills/` folder. The installer copies the ones listed in the extension's `skills.lock.yml` (this skill and its companions) into `.specify/extensions/engineering-build/skills/`, checking each SHA-256 before and after. Commands read them from there, so every agent Spec Kit supports can use them as plain instruction files.

Keep the source checkout separate from applications. Each target owns its constitution, hook configuration, binding overrides and feature outputs. Updates to the shared source do not automatically update target installations; run the installer's `update` command. Keep using the core constitution, specify, clarify, plan, tasks and implement commands.

Before hooks prepare stage-specific guidance without changing the feature. After hooks reconcile constitution, specification, design, tasks or implementation evidence, and make sure the companion-skill bindings for the stage ran (the preset normally runs them; the hooks run them when it did not). Hooks never call core commands recursively. Feature artifacts remain in the resolved Spec Kit feature directory: spec.md, plan.md and tasks.md remain the entry points, with `skill-runs.md` as the record of which companion skills ran or were skipped and why.

This extension does not require an API key, launch a background agent, or run a CI gate. It uses the active coding agent session. Mandatory means optional: false in Spec Kit's hook configuration; actual execution still depends on the coding agent and the current generated core commands. Verify the transcript and artifacts on a sample feature.

When migrating from the older `engineering-plan` extension or the `sdlc-skills` extension with the `org-sdlc` preset, remove them with the supported remove commands first, then install. Run the extension's configure command to update its managed constitution/agent guidance without replacing unrelated text. Do not delete existing feature documents or other extensions.
