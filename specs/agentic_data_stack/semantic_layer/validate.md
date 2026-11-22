---
wire_schema: "1.0"
command: validate
artifact: semantic_layer
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
  - artifact: semantic_layer
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify semantic layer implementation — metrics queryable, coverage target met
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Validate

## Validation Checks

**For dbt Semantic Layer:**
- [ ] `dbt parse` completes with 0 errors
- [ ] `dbt sl list metrics` returns all designed metrics
- [ ] Sample query succeeds for at least one metric per domain: `dbt sl query --metrics <metric> --group-by <time_dim> --limit 1`
- [ ] Every metric has a description

**For LookML:**
- [ ] LookML validator returns 0 errors
- [ ] Every canonical explore has at least one measure per designed metric
- [ ] All measures have descriptions
- [ ] No measure references a deprecated table

**Coverage check:**
- [ ] `sl_coverage_pct` in status.md is ≥ the target from query_audit (typically 80% of must-have patterns)

## Status Update

```yaml
semantic_layer:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  metrics_queryable: N
```
