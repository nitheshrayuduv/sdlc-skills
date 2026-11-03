# org-sdlc (Spec Kit preset)

Wraps `speckit.clarify`, `speckit.plan`, `speckit.tasks` and `speckit.implement` so each calls the `speckit.sdlc-skills.run` command of the [sdlc-skills extension](../sdlc-skills/README.md). The wraps hold no skill logic.

| Command | Position |
| --- | --- |
| clarify | before the core steps |
| plan | after the core design step |
| tasks | after core task generation |
| implement | standing instruction before the core steps |

Install the extension first, then the preset at a priority that beats the core commands:

```bash
specify extension add /path/to/sdlc-skills/speckit-extensions/sdlc-skills --dev
specify preset add --dev /path/to/sdlc-skills/speckit-extensions/org-sdlc --priority 5
```

Or use the installer, which does both, backs up the registries and verifies the result: see [installer/README.md](../../installer/README.md).
