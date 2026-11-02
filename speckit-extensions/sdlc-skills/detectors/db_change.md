# Detector: db_change

Decide whether the feature changes the data model. Read `spec.md` and the `plan.md` Technical Context.

**Yes signals:** new or changed entities in Key Entities, persistent state, new fields or relationships, retention or audit needs, search or reporting over stored data, an existing migrations folder that the feature touches.

**No signals:** the feature only changes UI, copy, configuration, dependency versions, build or CI files, or calls existing endpoints that read existing data without storing anything new.

**Unknown:** the evidence points both ways or the spec is silent about persistence.

Output exactly:

```
result: yes | no | unknown
evidence:
  - "<quoted line from spec.md or plan.md>"
```

Quote at least one line for `yes` and `no`. For `no`, quote the line that shows the feature does not persist new data, or state `no persistence mentioned` if there is none.
