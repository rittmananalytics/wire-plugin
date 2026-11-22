---
wire_schema: "1.0"
command: review
artifact: dbt_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: dbt_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of dbt audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Audit — Review

## Purpose

Internal RA review of the dbt audit. The reviewer confirms the complexity ratings, agrees on batch sizing, and flags any models that need a spike before migration begins.

## Prerequisites

- `audit/dbt_audit.md` and `audit/dbt_audit.csv` with `validate: pass`

## Workflow

### Step 1: Present audit summary

Display:
- Model count by complexity tier
- Feature tag distribution (top 10 most-common tags)
- Batch plan overview (batch count, models per batch, complexity mix per batch)
- Macros requiring translation
- Models with no tests

### Step 2: Gather reviewer feedback

Ask the reviewer:

1. Do the complexity ratings look right? Any models that appear mis-classified?
2. Does the batch sizing work — too large/small for the planned sprint structure?
3. Any models flagged Simple that should be manually reviewed before automated translation?
4. Any macros or jinja patterns that need a bespoke translation approach?

### Step 3: Apply feedback and record decision

Append review block to `audit/dbt_audit.md`.

### Step 4: Update status

```yaml
artifacts:
  dbt_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```
