---
wire_schema: "1.0"
command: review
artifact: migration_strategy
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
  - artifact: migration_strategy
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Client sign-off on migration strategy

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Strategy — Review

## Purpose

Client sign-off on the migration strategy. This is the gate that authorises the migration team to begin writing to the target platform. Once approved, the target_setup generate command becomes available.

## Prerequisites

- `migration/migration_strategy.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` for any Fathom recordings discussing migration approach, timeline, or risk tolerance.

### Step 2: Present strategy summary

Display:
- Platform pair and overall approach
- Phase plan with timelines
- Top 5 risks and mitigations
- Equivalency success criteria
- Go/no-go checklist

### Step 3: Gather client sign-off

Present for client review:

1. Does the translation approach for [most complex feature type] make sense given your data?
2. Is the phasing plan compatible with your business calendar (freeze periods, reporting deadlines)?
3. Are the equivalency thresholds appropriate — is ±0.1% row count tolerance acceptable for your most critical tables?
4. Is the rollback procedure understood and agreed?

### Step 4: Record decision

Append:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Sign-off notes
[Client comments and any agreed changes to approach]
```

### Step 5: Update status

```yaml
artifacts:
  migration_strategy:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:target-setup-generate $ARGUMENTS
```

## Review Gate

Client approval of the migration strategy is required before any writes to the target platform. The target_setup generate command will not proceed without `migration_strategy review: approved` in status.md.
