# Detector: vuln_report

Decide whether this feature is a vulnerability upgrade driven by a vulnerability report.

**Yes:** `<feature_dir>/vuln/intake.json` exists, or `spec.md` carries a vulnerability report (for example `Vulnerability report of <FLOW>`, CVE or GHSA rows with fixed versions, or the words vulnerable and fixed version for Gradle dependencies).

**No:** neither of the above.

**Unknown:** `spec.md` mentions vulnerabilities or dependency upgrades but holds no report and `intake.json` is absent. The runner asks the user once whether to run `speckit.engineering-build.vuln-intake`.

Output exactly:

```
result: yes | no | unknown
evidence:
  - "intake.json exists" | "<quoted line from spec.md>"
```
