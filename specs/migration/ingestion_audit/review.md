---
wire_schema: "1.0"
command: review
artifact: ingestion_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
mcp_contextual:
  - fathom
  - jira
  - confluence
produces:
  - type: status_update
    description: "Records reviewer name and decision in status.md"
preconditions:
  - artifact: ingestion_audit
    action: validate
    outcome: PASS
valid_next:
  - migration_inventory/generate
delegates_to:
  - utils/precondition_gate
description: Internal RA review of ingestion audit
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Ingestion Audit — Review

## Purpose

Internal RA review of the ingestion audit before it feeds into the migration inventory. The reviewer confirms connector coverage, agrees on exclusions, and flags any connectors that need additional investigation before strategy is drafted.

## Prerequisites

- `audit/ingestion_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about data sources, connector coverage, or ingestion scope. Surface relevant extracts for the reviewer.

### Step 2: Present audit for review

Display a summary of the ingestion audit:
- Total connectors in scope
- Breakdown by complexity (Low / Medium / High)
- Connectors excluded from migration with reasons
- Any broken or high-complexity connectors requiring attention
- Recommended migration order

### Step 3: Gather reviewer feedback

Ask the reviewer:

1. Is the connector list complete — are there any sources not captured here?
2. Do the exclusion decisions look right? Any connectors that should be included or excluded differently?
3. Are there any High-complexity connectors that need a spike before migration strategy is drafted?
4. Any concerns about row volumes or sync frequency assumptions?

### Step 4: Apply feedback and record decision

Incorporate any corrections into `audit/ingestion_audit.md`. Record the review outcome:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Capture any comments, corrections, or follow-up actions]
```

### Step 5: Update status

```yaml
artifacts:
  ingestion_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:db-object-audit-generate $ARGUMENTS
```

Or run all remaining audits in parallel:
```
/wire:migration-audit-all $ARGUMENTS
```

## Review Gate

The ingestion audit review is an internal RA gate — not a client deliverable at this stage. Approval confirms:
- All connectors are accounted for
- Exclusion decisions are defensible
- No blocking unknowns remain before strategy work begins

The output feeds directly into the migration inventory synthesis.
