---
wire_schema: "1.0"
command: generate
artifact: droughty_introspect
domain: droughty
release_types:
  - droughty
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Generate a schema inventory report — tables, columns, row counts, and PK/FK coverage across all schemas in scope
argument-hint: <release-folder>

---

# Droughty Introspect Command

## Purpose

Produce a schema inventory report for all tables and columns in the Droughty-configured schemas. Reports table counts, column counts, estimated row counts, PK/FK coverage, null-rate signals, and data type distributions. Output lands in the Wire artifact directory as `schema_inventory.md` and is available to subsequent Wire commands as evidence for the problem definition, requirements, and data model phases.

This command uses the warehouse's `INFORMATION_SCHEMA` directly via the configured MCP or SQL connection — not the Droughty CLI itself — so it runs regardless of whether dbt models have been deployed.

## Usage

```bash
/wire:droughty-introspect <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete for this release
- Warehouse accessible (BigQuery MCP or Snowflake connection active)

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Extract `warehouse`, `schemas`, and `profile_name`

If setup is not complete:
```
Error: Droughty setup not complete.

Run /wire:droughty-setup [release] first.
```

### Step 2: Query INFORMATION_SCHEMA

For each schema in `droughty.setup.schemas`, query the warehouse:

**BigQuery** (via BigQuery MCP or `bq` CLI):
```sql
SELECT
  table_schema,
  table_name,
  COUNT(*) AS column_count,
  SUM(CASE WHEN is_nullable = 'YES' THEN 1 ELSE 0 END) AS nullable_columns
FROM [project].[schema].INFORMATION_SCHEMA.COLUMNS
GROUP BY 1, 2
ORDER BY 1, 2
```

For row counts (approximate is fine):
```sql
SELECT
  table_schema,
  table_name,
  row_count
FROM [project].[schema].__TABLES__
ORDER BY 1, 2
```

**Snowflake** (via SQL):
```sql
SELECT
  table_schema,
  table_name,
  column_count,
  row_count
FROM information_schema.tables
WHERE table_schema IN ('[schema1]', '[schema2]')
ORDER BY 1, 2
```

### Step 3: Identify PK/FK Coverage

Scan column names for naming convention signals:
- Columns ending in `_pk` or `_id` (with no other `_pk` column on the table) → likely primary keys
- Columns ending in `_fk` or referencing another table by `[table]_id` pattern → likely foreign keys

Compute:
- `pk_coverage` — proportion of tables with at least one likely PK column
- `fk_coverage` — proportion of tables with at least one likely FK column

These are heuristics, not enforced constraints. Flag them clearly as inferred.

### Step 4: Generate Schema Inventory Report

Write to `.wire/releases/[release]/artifacts/droughty/schema_inventory.md`:

```markdown
# Schema Inventory — [client_name]

**Generated**: [today]
**Warehouse**: [warehouse_type]
**Schemas scanned**: [comma-separated list]
**Total tables**: [n]
**Total columns**: [n]

---

## Summary

| Metric | Value |
|---|---|
| Schemas in scope | [n] |
| Total tables | [n] |
| Tables with row counts | [n] |
| Estimated total rows | [n] |
| Tables with likely PK column | [n] ([pct]%) |
| Tables with at least one FK column | [n] ([pct]%) |

---

## Tables by Schema

### [schema_name]

| Table | Columns | Rows (approx) | PK col | FK cols |
|---|---|---|---|---|
| [table_name] | [n] | [n or —] | [col or —] | [cols or —] |
...

---

## Columns by Table

[For each table, list columns with type and nullable flag — truncated if >50 columns per table]

---

## Coverage Signals

**PK coverage** ([pct]% of tables have a likely primary key column):
Tables without a likely PK: [list]

**FK coverage** ([pct]% of tables have at least one FK reference column):
Tables with FK columns: [list with the FK column names]

---

## Notes

- Row counts are approximations from warehouse metadata, not COUNT(*) queries.
- PK/FK detection is based on column naming conventions (`_pk`, `_fk`, `_id` suffixes). Confirm against actual constraints or dbt schema.yml tests.
- This inventory was generated on [today] and reflects the current warehouse state.
```

### Step 5: Update status.md

```yaml
droughty:
  introspect:
    status: complete
    tables_found: [n]
    columns_found: [n]
    schemas_scanned: [[list]]
    pk_coverage_pct: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/schema_inventory.md
    completed_date: [today]
```

### Step 6: Confirm Output

```
## Schema Inventory Complete ✅

[n] tables across [n] schemas — [n] columns total
PK coverage: [pct]% | FK coverage: [pct]%

Artifact: .wire/releases/[release]/artifacts/droughty/schema_inventory.md

This inventory is now available to:
  /wire:problem-definition-generate    — embeds the schema summary as evidence
  /wire:requirements-generate          — seeds the data landscape section
  /wire:droughty-dbml [release]        — generates the entity-relationship diagram
```

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/schema_inventory.md`
- Updated `droughty.introspect` block in `status.md`
