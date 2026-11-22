---
wire_schema: "1.0"
command: review
artifact: db_object_audit
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
  - artifact: db_object_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of db object audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# DB Object Audit — Review

## Purpose

Internal RA review confirming the object catalog is complete, classification decisions are sound, and there are no surprises (large undiscovered tables, unanticipated external dependencies) before strategy work begins.

## Prerequisites

- `audit/db_object_audit.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to surface any Fathom recordings touching data model scope, warehouse structure, or object ownership.

### Step 2: Present audit summary

Display:
- Total objects by type and volume tier
- Schemas/datasets in scope
- Objects flagged `evaluate` with their notes
- Objects flagged `exclude` — confirm these are genuinely out of scope
- Platform-specific features detected in views (preview of translation complexity)

### Step 3: Gather reviewer feedback

Ask the reviewer:

1. Are there any schemas or databases missing from this audit?
2. Do the `exclude` decisions look right — any objects that should be in scope?
3. Any `evaluate` objects where the assessment approach is already clear?
4. Anything in the feature detection results that looks unexpectedly complex?

### Step 4: Apply feedback and record decision

Update the audit with any corrections. Append:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Capture any corrections, follow-up actions, or scope clarifications]
```

### Step 5: Update status

```yaml
artifacts:
  db_object_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved and all 5 audits are complete:
```
/wire:migration-inventory-generate $ARGUMENTS
```

Otherwise, continue with remaining audits.

## Review Gate

Approval confirms: the object catalog is complete, all schemas are accounted for, and the migration team has a shared understanding of scope before strategy begins.
