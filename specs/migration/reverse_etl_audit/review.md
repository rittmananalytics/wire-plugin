---
wire_schema: "1.0"
command: review
artifact: reverse_etl_audit
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
  - artifact: reverse_etl_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of reverse ETL audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Reverse ETL Audit — Review

## Purpose

Internal RA review of the reverse ETL audit before it feeds into the migration inventory. The reviewer confirms sync coverage, agrees on decommission decisions, validates that warehouse dependency mapping is complete, and flags any syncs that need deeper investigation before the migration strategy is drafted — particularly any Customer Studio audiences or Journeys that require rebuild.


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Prerequisites

- `audit/reverse_etl_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about data activation, downstream destinations, Hightouch syncs, or reverse ETL. Surface relevant extracts — particularly any mentions of specific destination tools, sync frequency requirements, or known sync failures.

### Step 2: Present audit for review

Display a summary of the reverse ETL audit:
- Total syncs, broken down by destination type
- Migration approach distribution (repoint / rewrite_model / rebuild / decommission)
- Complexity breakdown (Low / Medium / High)
- Lightning engine syncs requiring schema recreation
- dbt model syncs and their migration batch dependencies
- Syncs flagged for decommission with reasons
- Any syncs with `status: interrupted` or `status: pending`

### Step 3: Gather reviewer feedback

Ask the reviewer:

1. Is the sync list complete — are there any syncs or workspace environments not captured here?
2. Do the decommission decisions look right? Any syncs that should be kept or cut differently?
3. Are there any High-complexity syncs (Customer Studio audiences, Journeys, or rewrite_model cases) that need a spike before migration strategy is drafted?
4. Are the warehouse object dependencies correct — do the listed tables/views match what the team knows about these syncs?
5. Any concerns about sync volume, schedule frequency, or destination credentials that will affect cutover timing?

### Step 4: Apply feedback and record decision

Incorporate any corrections into `audit/reverse_etl_audit.md`. Record the review outcome:

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
  reverse_etl_audit:
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

The reverse ETL audit review is an internal RA gate — not a client deliverable at this stage. Approval confirms:
- All syncs are accounted for and decisions are defensible
- Warehouse dependency mapping is complete enough to drive cutover sequencing
- No blocking unknowns remain before migration strategy work begins

The output feeds directly into the migration inventory — specifically the dependency graph that determines which warehouse objects must be migrated before each sync can be re-pointed.
