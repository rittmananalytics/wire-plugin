---
wire_schema: "1.0"
command: utility
artifact: equivalency
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Apply agreed fix and re-run equivalency checks for affected objects

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Equivalency — Fix

## Purpose

Applies a specific fix to a failing equivalency object and re-runs the equivalency checks for that object (and any objects that depend on it). Updates the loop history in status.md. This is a targeted repair command — it does not re-run checks for the entire scope.

## Arguments

Required:
- `--object <name>` — the table or dbt model to fix
- `--approach <description>` — brief description of the fix being applied

Example:
```
/wire:equivalency-fix 01-migration --object wh_sales__order_fact --approach "Add COALESCE for NULL handling in subtotal column"
```

## Workflow

### Step 1: Load context

Read the investigation notes for this object from the latest equivalency report. Confirm the `--approach` matches or builds on the proposed fix.

### Step 2: Apply the fix

Based on the `--approach`:

**If SQL translation fix**:
- Open the translated model at `migration/dbt/{model_name}.sql`
- Apply the correction
- Update the diff file
- Re-run `dbt compile` for the model if target profile available

**If DDL fix**:
- Open the relevant target_setup_scripts SQL file
- Apply the correction
- Note that the DDL change may need to be applied to the target platform manually

**If configuration fix** (Fivetran mapping, type handling):
- Document the configuration change required
- If Fivetran MCP available: apply the mapping change via MCP
- Otherwise: write detailed manual steps for the engineer to apply

**If accepted difference**:
- Document the business justification
- Update the equivalency tolerance for this table in migration_strategy.md
- Mark the object as `accepted_difference` in status.md

### Step 3: Re-run checks for affected objects

Identify all objects that depend on the fixed object (using the dependency graph from migration_inventory.md).

Re-run all per-object check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum) for:
- The fixed object
- All direct dependents of the fixed object

If the fix touches a column feeding a business invariant, re-run that invariant too.

If `migration.scope == tenant_carveout`, apply `migration.tenant_predicate` as a `WHERE` clause on both source and target when re-running these checks, exactly as `equivalency-validate` does. When `scope` is `full_migration` or absent, re-run unscoped.

If the fixed object or any re-checked dependent is a relative-date-flagged model (`equivalency-validate` Step 1.5), resolve a fresh pinned as-of for this re-run, apply the same literal substitution over the compiled SQL on both sides, and record the pinned value in the fix entry (Step 4). Never re-run a flagged model's checks unpinned.

### Step 4: Update status

Add a `fix` entry to the loop history:

```yaml
migration:
  equivalency_validation:
    loop_history:
      - run: N
        date: "{{PREVIOUS_DATE}}"
        passing: X
        failing: Y
      - fix:
          date: "{{TODAY}}"
          object: "{{OBJECT_NAME}}"
          approach: "{{APPROACH}}"
          pinned_as_of: "{{PINNED_AS_OF_TS}}"   # UTC; only when re-checked objects include relative-date-flagged models
          result: "passing" | "still_failing"
```

Update `checks_failing` with the new total after re-checking affected objects.

### Step 5: Output

If the object now passes:
```
Fix applied successfully. {{OBJECT_NAME}} now passes all equivalency checks.
Checks failing: N (was N+1)

/wire:equivalency-validate $ARGUMENTS   ← run full check when all fixes applied
```

If the object still fails:
```
Fix applied but {{OBJECT_NAME}} still failing.
Check type still failing: [type]

Re-investigate:
/wire:equivalency-investigate $ARGUMENTS --object {{OBJECT_NAME}}
```
