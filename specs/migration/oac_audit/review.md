---
wire_schema: "1.0"
command: review
artifact: oac_audit
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
  - artifact: oac_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of OAC audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# OAC Audit — Review

## Purpose

Internal RA review of the OAC audit before it feeds into the migration inventory. The reviewer confirms physical/logical/presentation-layer coverage, agrees on decommission decisions for unused subject areas or physical tables, checks that warehouse dependency mapping and connection pools are complete, and flags any physical tables or raw SQL constructs needing deeper investigation before the migration strategy is drafted — particularly `rewrite_sql`/`rebuild` physical tables and any construct classified `redesign` or `manual-review-out-of-scope`.

## Prerequisites

- `audit/oac_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/oac_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about reporting, dashboards, OAC, semantic model ownership, or specific subject areas. Surface relevant extracts — particularly mentions of critical subject areas, model owners, or known query issues.

### Step 2: Present audit for review

Display a summary:
- Total databases, connection pools, physical tables, physical joins, logical tables, subject areas
- Migration approach distribution for physical tables (repoint / rewrite_sql / rebuild)
- Complexity breakdown for physical tables (Low / Medium / High)
- Raw SQL constructs by type and by `construct_action` (translate / redesign / manual-review-out-of-scope)
- Connection pools and the physical tables per connection
- Source-resolution coverage and the unresolved physical tables
- Logical and presentation layer summary, with any `migration_impact` exceptions called out
- Structural validation (`validate_smml.py`) result
- dbt model dependencies and their migration batch dependencies
- Subject areas/physical tables flagged for decommission with reasons

### Step 3: Gather reviewer feedback

1. Is the physical/logical/presentation catalog complete — any databases, schemas, or subject areas not captured here?
2. Do the decommission decisions for unused/archived subject areas and physical tables look right? Any that should be kept or cut differently?
3. Are there any High-complexity physical tables (`rewrite_sql` or `rebuild`) that need a spike before migration strategy is drafted?
4. Are the `redesign` and `manual-review-out-of-scope` constructs fully accounted for, and does the team agree on who owns reauthoring each one?
5. Are the warehouse object dependencies for physical tables correct — do the listed tables/views match what the team knows about these subject areas?
6. Does the structural validation result need action before this audit is treated as final?

### Step 4: Apply feedback and record decision

Incorporate corrections into `audit/oac_audit.md`. Record:

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
  oac_audit:
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

The OAC audit review is an internal RA gate. Approval confirms the physical, logical, and presentation layers are fully accounted for, warehouse dependency mapping for the physical layer is complete enough to drive cutover sequencing, connection pools are captured, raw SQL constructs are fully scoped and classified, and no blocking unknowns remain before migration strategy work begins. The output feeds the migration inventory's dependency graph — specifically which warehouse objects must exist on target before each physical table can be repointed.
