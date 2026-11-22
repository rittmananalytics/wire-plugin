---
wire_schema: "1.0"
command: validate
artifact: query_audit
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
  - artifact: query_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify query audit pattern extraction and classification quality
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Query Audit Validate

## Validation Checks

- [ ] Query source is documented (query_history, sow_derived, or stakeholder_input)
- [ ] At least 10 question patterns identified (or a note explaining why fewer exist)
- [ ] Every pattern has a SL classification (SL-covered / SL-extendable / SL-gap / Raw-only)
- [ ] Every SL-gap pattern has a priority (High / Medium / Low)
- [ ] Raw-only patterns are genuinely complex — not misclassified SL-gap patterns
- [ ] Domain distribution sums to ~100%
- [ ] Top patterns align with domains identified in dataset_audit (no unexplained new domains)

## Status Update

```yaml
query_audit:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
