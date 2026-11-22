---
wire_schema: "1.0"
command: review
artifact: orchestration_audit
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
  - artifact: orchestration_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of orchestration audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Audit — Review

## Purpose

Confirms the job catalog is complete, migration approaches are sensible, and no critical jobs have been accidentally excluded before migration strategy is drafted.

## Prerequisites

- `audit/orchestration_audit.md` with `validate: pass`

## Workflow

### Step 1: Present audit summary

Display: total jobs, breakdown by type and criticality, count requiring evaluate/translate, connection list.

### Step 2: Gather reviewer feedback

1. Are any critical jobs missing from this audit?
2. Do the exclude decisions make sense?
3. Any jobs with unusual trigger mechanisms that need special handling?

### Step 3: Record decision

Append review block to `audit/orchestration_audit.md`.

### Step 4: Update status

```yaml
artifacts:
  orchestration_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```
