---
wire_schema: "1.0"
command: review
artifact: migration_inventory
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
  - artifact: migration_inventory
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA and client scope confirmation

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Inventory — Review

## Purpose

Joint internal RA and client review of the migration inventory. This is the first client-facing gate in the migration workflow. The client confirms the scope is complete and agrees to the effort estimate before strategy and execution work begins.

## Prerequisites

- `migration/migration_inventory.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to surface any Fathom recordings touching migration scope, budget, or timeline.

### Step 2: Present inventory summary

Display:
- Total objects by type
- Effort estimate with phase breakdown
- Migration duration estimate
- Key risks: evaluate objects, High-complexity connectors/models
- Proposed phasing

### Step 3: Gather reviewer feedback

**Internal RA questions**:
1. Is the effort estimate realistic given the team's experience with this platform pair?
2. Any objects or phases where the estimate feels low?

**Client confirmation questions**:
1. Does this inventory match your understanding of what's in scope?
2. Are there any objects you want to exclude that are currently in scope?
3. Does the phasing approach work with your cutover timeline?
4. Any non-production environments (staging, dev) that also need migrating?

### Step 4: Apply feedback and record decision

Update the inventory if scope changes are agreed. Append:

```markdown
## Review

**Internal reviewer**: {{RA_REVIEWER}}
**Client attendees**: {{CLIENT_NAMES}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Agreed scope changes
[List any objects added or removed after review]

### Open items
[List any items requiring follow-up before strategy begins]
```

### Step 5: Update status

```yaml
artifacts:
  migration_inventory:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:migration-batching-generate $ARGUMENTS
```

Batching partitions the approved inventory into graph-checked domain batches before strategy is drafted. For engagements that skip domain batching, go straight to:
```
/wire:migration-strategy-generate $ARGUMENTS
```

## Review Gate

This review is the scope sign-off point. Once approved, the migration strategy will be drafted against this inventory. Changes to scope after this point require a formal change request.
