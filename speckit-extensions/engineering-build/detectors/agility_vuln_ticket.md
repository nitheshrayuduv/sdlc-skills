# Detector: agility_vuln_ticket

Decide whether this feature is a vulnerability upgrade driven by an Agility ticket.

**Yes:** `<feature_dir>/vuln/intake.json` exists, or `spec.md` names an Agility vulnerability ticket (for example `Vulnerability report of <FLOW>`, a `D-` or `S-` number with CVE rows, or the words vulnerable and fixed version for Gradle dependencies).

**No:** neither of the above.

**Unknown:** `spec.md` mentions vulnerabilities or dependency upgrades but names no ticket and `intake.json` is absent. The runner asks the user once whether to run `speckit.engineering-build.vuln-intake`.

Output exactly:

```
result: yes | no | unknown
evidence:
  - "intake.json exists" | "<quoted line from spec.md>"
```
