---
wire_schema: "1.0"
command: validate
artifact: metric_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: metric_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Check metric audit completeness and conflict detection quality
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Metric Audit Validate

## Validation Checks

- [ ] At least one metric source enumerated (dbt SL, LookML, BI tool, or schema.yml)
- [ ] Every domain from dataset_audit is assessed for metric coverage (or explicitly noted as having none)
- [ ] Every conflict has both definitions documented, not just flagged
- [ ] Coverage gap analysis covers at least 10 questions (or all SOW KPIs if fewer than 10)
- [ ] Every recommended new metric has a draft definition (not just a name)
- [ ] Coverage percentage is calculable from the gap analysis table

## Status Update

```yaml
metric_audit:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
