---
wire_schema: "1.0"
command: review
artifact: omni_audit
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: omni_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of Omni audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Audit — Review

## Purpose

Internal RA review of the Omni audit before it feeds into the migration inventory. The reviewer confirms model and content coverage, agrees on decommission decisions for unused workbooks/tiles, checks that warehouse dependency mapping and connections are complete, and flags any views or raw-SQL tiles needing deeper investigation before the migration strategy is drafted — particularly `rewrite_sql` views/tiles and any `rebuild` cases.

## Prerequisites

- `audit/omni_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/omni_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about reporting, dashboards, Omni, BI access, or specific workbooks. Surface relevant extracts — particularly mentions of critical dashboards, model owners, or known query issues.

### Step 2: Present audit for review

Display a summary:
- Total connections, topics, views, folders, workbooks, tiles
- Migration approach distribution for views (repoint / rewrite_sql / rebuild)
- Complexity breakdown for views (Low / Medium / High)
- Tiles by query surface (topic vs raw_sql), and raw-SQL tiles by approach
- Connections and the views per connection
- Source-resolution coverage and the unresolved views / raw-SQL tiles
- dbt model views and their migration batch dependencies
- Workbooks/tiles flagged for decommission with reasons

### Step 3: Gather reviewer feedback

1. Is the model and content catalog complete — any workbooks, personal folders, or topics not captured here?
2. Do the decommission decisions for unused/archived workbooks and tiles look right? Any that should be kept or cut differently?
3. Are there any High-complexity views (`rewrite_sql` or `rebuild`) that need a spike before migration strategy is drafted?
4. Are the warehouse object dependencies for views correct — do the listed tables/views match what the team knows about these reports?
5. Are the raw-SQL tile overrides fully accounted for, and does their scope match what the client expects to keep after migration?

### Step 4: Apply feedback and record decision

Incorporate corrections into `audit/omni_audit.md`. Record:

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
  omni_audit:
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

The Omni audit review is an internal RA gate. Approval confirms all reporting content is accounted for, warehouse dependency mapping for the model's views is complete enough to drive cutover sequencing, connections are captured, raw-SQL tile overrides are fully scoped, and no blocking unknowns remain before migration strategy work begins. The output feeds the migration inventory's dependency graph — specifically which warehouse objects must exist on target before each view can be repointed.
