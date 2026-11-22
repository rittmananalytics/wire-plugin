---
wire_schema: "1.0"
command: validate
artifact: semantic_layer_design
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
  - artifact: semantic_layer_design
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Check semantic layer design completeness and metric definition quality
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Design Validate

## Validation Checks

- [ ] Every must-have gap from query_audit_decisions is covered by a designed metric
- [ ] Every metric has: name, description, aggregation type, source field, and at least one time dimension
- [ ] No metric references a deprecated table from governance_design
- [ ] All metric names are unique (no collisions with existing metric_audit inventory)
- [ ] Derived metrics have dependency paths documented
- [ ] Metric naming follows agreed conventions (snake_case, no abbreviations unless documented)
- [ ] Out-of-scope metrics are explicitly listed with deferral justification

## Status Update

```yaml
semantic_layer_design:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
