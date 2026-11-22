---
wire_schema: "1.0"
command: validate
artifact: governance_design
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
  - artifact: governance_design
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify governance design completeness and internal consistency
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Governance Design Validate

## Validation Checks

- [ ] Every domain from dataset_audit has a canonical table entry
- [ ] Every canonical table exists in the warehouse (not a proposed future table)
- [ ] Every deprecated table has a sunset date and a migration note
- [ ] Tiering policy explicitly covers all three tiers with routing order stated
- [ ] Ownership register has a contact for every domain
- [ ] No canonical table appears in the deprecation list
- [ ] Sunset dates are ≥30 days from today (no immediate deprecations without review)

## Status Update

```yaml
governance_design:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
