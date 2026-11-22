---
wire_schema: "1.0"
command: review
artifact: migration_report
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
  - artifact: migration_report
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Final review and archive of migration report

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Report — Review

## Purpose

Final client-facing review of the migration report. Confirms the project is complete and initiates the release archive.

## Prerequisites

- `migration/migration_report.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` for any post-cutover recordings.

### Step 2: Present report summary

Display: executive summary, object counts, equivalency outcome, effort comparison, source decommission timeline.

### Step 3: Gather client confirmation

1. Does this accurately reflect what was delivered?
2. Are the accepted differences documented correctly?
3. Is the decommission timeline agreed?
4. Any follow-up actions required?

### Step 4: Record decision

Append review block to `migration/migration_report.md`.

### Step 5: Update status

```yaml
artifacts:
  migration_report:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Archive the release

If approved, offer to archive the release:
```
Migration release complete. Archive? (yes/no)
/wire:archive releases/$ARGUMENTS
```
