# Detector: ui_flows

Decide whether the feature has user flows that need browser (Playwright) tests. Read the acceptance scenarios in `spec.md`.

**Yes signals:** acceptance scenarios that a user performs in a browser (pages, forms, navigation, clicks), the repo already has a Playwright config, or the plan names a web UI.

**No signals:** the feature is a library, CLI, batch job, dependency upgrade or API-only change with no browser surface.

**Unknown:** the surface is not stated. Treat `unknown` as `no` for this detector and record a warning.

Output exactly:

```
result: yes | no | unknown
flows:
  - "<scenario id>: <one-line flow>"
evidence:
  - "<quoted line>"
```
