---
wire_schema: "1.0"
command: review
artifact: metabase_audit
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
  - artifact: metabase_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of Metabase audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Audit — Review

## Purpose

Internal RA review of the Metabase audit before it feeds into the migration inventory. The reviewer confirms card/dashboard coverage, agrees on decommission decisions, checks that warehouse dependency mapping and permission groups are complete, and flags any cards needing deeper investigation before the migration strategy is drafted — particularly `rewrite_sql` cards and any `rebuild` cases.

## Prerequisites

- `audit/metabase_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about reporting, dashboards, Metabase, BI access, or specific reports. Surface relevant extracts — particularly mentions of critical dashboards, report owners, or known query issues.

### Step 2: Present audit for review

Display a summary:
- Total cards, dashboards, collections
- Migration approach distribution (repoint / rewrite_sql / rebuild / decommission)
- Complexity breakdown (Low / Medium / High)
- Database connections and the cards per connection
- Permission groups and their access
- Source-resolution coverage and the unresolved cards
- dbt model cards and their migration batch dependencies
- Cards flagged for decommission with reasons

### Step 3: Gather reviewer feedback

1. Is the card/dashboard list complete — any collections, personal collections, or reports not captured here?
2. Do the decommission decisions look right? Any cards that should be kept or cut differently?
3. Are there any High-complexity cards (`rewrite_sql` or `rebuild`) that need a spike before migration strategy is drafted?
4. Are the warehouse object dependencies correct — do the listed tables/views match what the team knows about these reports?
5. Are the permission groups complete, and do they reflect the access the client expects after migration?

### Step 4: Apply feedback and record decision

Incorporate corrections into `audit/metabase_audit.md`. Record:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Capture comments, corrections, or follow-up actions]
```

### Step 5: Update status

```yaml
artifacts:
  metabase_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved and all other audits are also approved:
```
/wire:migration-inventory-generate $ARGUMENTS
```

If other audits are still pending:
```
Continue with remaining audits. When all audits are approved:
/wire:migration-inventory-generate $ARGUMENTS
```

## Review Gate

The Metabase audit review is an internal RA gate. Approval confirms all reporting content is accounted for, warehouse dependency mapping is complete enough to drive cutover sequencing, permission groups are captured, and no blocking unknowns remain before migration strategy work begins. The output feeds the migration inventory's dependency graph — specifically which warehouse objects must exist on target before each card can be repointed.
