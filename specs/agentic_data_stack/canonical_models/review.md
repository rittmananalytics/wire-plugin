---
wire_schema: "1.0"
command: review
artifact: canonical_models
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
  - artifact: canonical_models
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Data team review of canonical model implementation and deprecation notices
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Canonical Models Review

## Purpose

Confirm the dbt implementation with the data engineering team before proceeding to semantic layer build. This is a technical review — the audience is the data team, not business stakeholders.

## Workflow

### Step 1: Present Implementation Summary

```
## Canonical Models Review

### What Was Built

| Domain | Canonical Model | Tests | Deprecated Tables |
|---|---|---|---|
| orders | wh_sales__order_fact | 12 passing | orders_raw, revenue_v2 (sunset YYYY-MM-DD) |
| customers | wh_core__customer_dim | 8 passing | customer_snapshot_2023 |

### dbt Test Results

All N canonical model tests: PASS
```

### Step 2: Walk Through Each Domain

For each domain, show:
1. The canonical model definition
2. The schema.yml documentation quality
3. The deprecation notices on removed tables

### Step 3: Confirm Sunset Dates

Confirm all sunset dates with the data engineering lead. These will be communicated to downstream consumers.

### Step 4: Record Sign-off

```yaml
canonical_models:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```
