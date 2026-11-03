# Detector: vuln_report

Decide whether this feature is a dependency vulnerability upgrade driven by a scanner report.

**Yes:** `<feature_dir>/vuln/intake.json` exists, or `spec.md` describes vulnerable dependency versions to upgrade from a scanner report (advisory IDs such as CVE or GHSA, with vulnerable and fixed versions).

**No:** neither of the above.

**Unknown:** `spec.md` mentions vulnerabilities or dependency upgrades but names no report and `intake.json` is absent. The runner asks the user once whether to run `speckit.sdlc-skills.vuln-intake`.

Output exactly:

```
result: yes | no | unknown
evidence:
  - "intake.json exists" | "<quoted line from spec.md>"
```
