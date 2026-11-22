---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Data team and business stakeholder review of semantic layer implementation
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Review

## Purpose

Confirm the semantic layer implementation covers the agreed metrics and answers the priority questions from the query audit. Include a business stakeholder who can verify the numbers — not just the data team who built them.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for prior discussions about specific metrics or questions stakeholders have flagged as unreliable. Verify those cases are now passing in the semantic layer.

### Step 2: Run the Priority Questions

Before the review meeting, run every must-have question from the query audit through the semantic layer and confirm the output is correct:

```bash
# Example: confirm total_revenue for last month
dbt sl query --metrics total_revenue \
  --group-by order__order_date__month \
  --where "{{ TimeDimension('order__order_date', 'MONTH') }} = '2025-04-01'" \
  --limit 1
```

Compare each result against a known-correct source (prior dashboard, finance report, or direct SQL).

### Step 2: Present Coverage Summary

```
## Semantic Layer Review

Implemented N metrics across N domains.

### Coverage Against Priority Questions

| Question | Before | After |
|---|---|---|
| Revenue by channel | Raw SQL | ✅ Semantic layer |
| Active customers 30d | Raw SQL | ✅ Semantic layer |
| Marketing spend by campaign | Raw SQL | ✅ Semantic layer |

Overall must-have coverage: X% (target: 80%)
```

### Step 3: Spot-Check Numbers

Walk the reviewer through 3–5 representative queries. Confirm numbers match expectations. Any discrepancies must be resolved before the review passes.

### Step 4: Record Sign-off

```yaml
semantic_layer:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
  numbers_verified: true
```
