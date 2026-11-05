# engineering-build-preset (Spec Kit preset)

Wraps `speckit.clarify`, `speckit.plan`, `speckit.tasks` and `speckit.implement` so each calls `speckit.engineering-build.run <stage>` from the [engineering-build extension](../README.md) at the right point. The wraps hold no skill logic; the extension's binding registry decides what runs.

| Command | Position | Companion skills it triggers |
| --- | --- | --- |
| clarify | before the core steps | grill-me |
| plan | after the core design step | database-schema-designer, api-designer, engineering-vulnerability-upgrade |
| tasks | after core task generation | playwright-expert, engineering-vulnerability-upgrade |
| implement | standing instruction before the core steps | ponytail, playwright-expert, engineering-vulnerability-upgrade |

The preset requires the extension. Install both with the installer, which adds the extension (with its skills) first and this preset at priority 5: see [speckit-extensions/README.md](../../README.md).
