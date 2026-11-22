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
description: Deep diagnostics for a specific failing equivalency object

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Equivalency — Investigate

## Purpose

Deep diagnostics for a specific table or dbt model that is failing equivalency checks. Goes beyond the summary-level reporting of `equivalency-validate` to identify the root cause of the failure — whether it is a translation error, a data loading issue, a timing problem, or an expected difference.

## Arguments

`$ARGUMENTS` must include `--object <table_or_model_name>`. Example:
```
/wire:equivalency-investigate 01-migration --object wh_sales__order_fact
```

## Workflow

### Step 1: Locate the failing object

Read the most recent equivalency report from `migration/equivalency_report_*.md`. Find the entry for the specified object. Load its per-check-type failure details.

### Step 2: Diagnose by failure type

If `migration.scope == tenant_carveout`, apply `migration.tenant_predicate` as a `WHERE` clause on both source and target in every diagnostic query below — including the partition-level, sample, and freshness queries — so the diagnosis matches the scoped row set `equivalency-validate` checked. When `scope` is `full_migration` or absent, run the queries unscoped as written.

Rule out timing before treating any failure as a real data divergence. If the object's SQL references `CURRENT_DATE()`, `NOW()`, or another relative-date function (a relative-date-flagged model per `equivalency-validate` Step 1.5), read the pinned as-of value recorded for it in the failing run's report. If no pinned value was recorded, the checks ran unpinned and the failure may be a live-edge timing artefact — re-run `/wire:equivalency-validate` (which pins the as-of instant for flagged models) before investigating further. If a pinned value was recorded, use that same literal in every diagnostic query below so the diagnosis reproduces the failing run exactly.

**If failing on Row count**:
- Run the row count query for both source and target
- Compare counts at the partition/date level (if partitioned): identify which date ranges have discrepancies
- Check Fivetran sync logs for the connector that loads this table — was the last sync complete?
- Check for soft-deleted rows that might differ between platforms
- For relative-date-flagged models: confirm the failing run used a pinned as-of (see preamble above) — an unpinned run over a "last N days" window can show a false count divergence at the live edge

**If failing on Schema**:
- Show the exact column diff: columns present in source but missing from target, columns present in target but not source, type mismatches
- Cross-reference against the target_setup DDL scripts — was the column included?
- Check for case sensitivity differences in column names

**If failing on Value sampling**:
- Identify which specific columns have statistical deviations
- Run a sample comparison: pull 20 rows from source and target on the same primary key values
- Check for NULL handling differences (COALESCE behaviour, empty string vs NULL)
- Check for timezone differences in TIMESTAMP columns

**If failing on Freshness**:
- Compare `max(loaded_at)` or `max(updated_at)` on source vs target
- Check Fivetran connector status on target — is it running on schedule?
- Check if the target connector completed its initial load

**If failing on dbt tests**:
- Show the full test output for the failing tests
- Identify whether the failure is a not_null, unique, accepted_values, or relationship test
- Check if the test failure exists on source as well (if so, it may be a pre-existing issue, not a migration regression)

### Step 3: Propose fix approach

Based on the diagnosis, propose one or more fix approaches with their trade-offs:

- **Translation fix**: update the dbt model SQL translation or DDL script
- **Configuration fix**: update Fivetran connector mapping or type handling
- **Data reload**: trigger a full historical sync for the connector
- **Accept as expected difference**: document the known difference with business justification (e.g., deprecated column no longer populated)
- **Adjust tolerance**: if the difference is within acceptable business bounds, update the tolerance for this table in migration_strategy.md

### Step 4: Write investigation notes

Append to the latest equivalency report:

```markdown
## Investigation: {{OBJECT_NAME}}

**Investigated**: {{TODAY}}
**Failure types**: [list]
**Root cause**: [description]
**Proposed fix**: [description]
**Fix command**: /wire:equivalency-fix $ARGUMENTS --object {{OBJECT_NAME}} --approach "[brief description]"
```

### Step 5: Output

Print: root cause summary, proposed fix, and the fix command to run.
