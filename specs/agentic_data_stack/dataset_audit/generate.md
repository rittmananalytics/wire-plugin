---
wire_schema: "1.0"
command: generate
artifact: dataset_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Inventory all warehouse tables, identify duplicates, and grade governance maturity per domain
argument-hint: <release-folder>

---

# Agentic Data Stack — Dataset Audit Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce a complete inventory of tables in the client's warehouse, identify near-duplicate and redundant definitions, classify each table by governance tier, and grade the overall governance maturity per domain. This is the foundation for every downstream decision in the release — if the audit is shallow, the canonical model will be wrong.

## Usage

```bash
/wire:ads_dataset-audit-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` exists with `project_type: agentic_data_stack`
- Warehouse access configured (BigQuery, Snowflake, Databricks, or Redshift)
- dbt project path recorded in status.md (optional — enriches the audit with lineage)

## Workflow

### Step 1: Read Context

1. Read `.wire/<release-folder>/status.md`
2. Note: `warehouse`, `bi_tool`, `semantic_layer`, `dbt_project_path`, `primary_domain`
3. Read `.wire/engagement/context.md` for business context and domain definitions
4. Read `.wire/engagement/sow.md` if present — SOW may name specific tables or subject areas

### Step 2: Discover Tables

Connect to the warehouse and enumerate all tables in the analytics schema(s). For each table, collect:

- Full table reference (project.dataset.table for BigQuery; database.schema.table for Snowflake)
- Row count and approximate size
- Last modified date
- Owner / creator (from information_schema where available)
- Column count and column names
- Description (from table metadata / dbt docs if available)

**BigQuery:**
```sql
SELECT
  table_catalog, table_schema, table_name,
  row_count, size_bytes, last_modified_time,
  ARRAY_AGG(column_name ORDER BY ordinal_position) AS columns
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
JOIN `region-us`.INFORMATION_SCHEMA.COLUMNS USING (table_catalog, table_schema, table_name)
GROUP BY 1,2,3,4,5,6
ORDER BY table_schema, table_name
```

**Snowflake:**
```sql
SELECT
  table_catalog, table_schema, table_name, table_type,
  row_count, bytes, last_altered, table_owner, comment
FROM information_schema.tables
WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
ORDER BY table_schema, table_name
```

If direct warehouse access is unavailable, ask the consultant to run the query and paste results, or provide a CSV export from their warehouse console.

### Step 3: Identify Near-Duplicates

Group tables by semantic similarity. Flag as near-duplicate when two or more tables share:

- Overlapping column sets (>70% column name overlap)
- Similar naming (same root word with different suffixes: `_v2`, `_new`, `_old`, `_copy`, `_bak`, `_legacy`, year suffixes)
- Same grain but different sources or transformation levels

For each duplicate group, identify the canonical candidate — typically the one with:
- Most recent modification date
- Highest row count
- Clearest naming (follows dbt three-layer convention or agreed naming standard)
- dbt-managed (prefer managed over ad-hoc)

### Step 4: Classify by Governance Tier

Assign each table to one of three tiers:

| Tier | Criteria | Agent routing |
|---|---|---|
| **Semantic** | Defined metric in semantic layer (MetricFlow, LookML, dbt SL) | Route here first — always |
| **Curated** | dbt-managed mart or staging model, documented, tested | Route here if no semantic metric |
| **Raw** | Unmanaged, undocumented, or staging-only tables | Last resort fallback |

### Step 5: Grade Governance Maturity Per Domain

Group tables by business domain (orders, customers, marketing, finance, logistics, product, etc.) and assign a maturity grade:

| Grade | Criteria |
|---|---|
| **A** | One canonical table per entity; semantic layer coverage >80%; documented; tested |
| **B** | Clear canonical table; partial semantic layer; documented; some tests |
| **C** | Multiple candidates for canonical; sparse documentation; few tests |
| **D** | Widespread duplication; no documentation; no semantic layer; raw tables primary |

### Step 6: Write Dataset Audit Document

Write `.wire/<release-folder>/artifacts/dataset_audit.md`:

```markdown
---
artifact: dataset_audit
generated: YYYY-MM-DD
status: draft
---

# Dataset Audit

## Summary

| Metric | Value |
|---|---|
| Total tables discovered | N |
| Near-duplicate groups identified | N |
| Tables recommended for deprecation | N |
| Domains assessed | N |
| Overall governance grade | A/B/C/D |

## Domain Governance Grades

| Domain | Grade | Tables | Canonical Candidates | Issues |
|---|---|---|---|---|
| orders | B | 12 | fct_orders | 3 near-duplicates |
| ... | | | | |

## Near-Duplicate Groups

### [Group 1: Revenue Tables]

| Table | Rows | Last Modified | Assessment |
|---|---|---|---|
| orders_raw | 2.1M | 2024-11-01 | Raw — deprecate |
| revenue_v2 | 2.1M | 2024-09-15 | Stale copy — deprecate |
| fct_orders | 2.1M | 2025-03-01 | **Canonical — retain** |
| fct_orders_v3 | 1.8M | 2025-01-10 | Partial migration — deprecate |

**Recommendation:** Retain `fct_orders`. Deprecate `orders_raw`, `revenue_v2`, `fct_orders_v3` with 90-day sunset.

## Full Table Inventory

[Complete table listing with tier classification]

## Recommended Deprecations

[Ordered list of tables recommended for sunset with justification]
```

### Step 7: Update Status

```yaml
dataset_audit:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  tables_discovered: N
  duplicate_groups: N
  domains_assessed: N
  overall_grade: B
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dataset_audit`
- `artifact_name`: `Dataset Audit`
- `file_path`: `.wire/[release_folder]/artifacts/dataset_audit.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

```
## Dataset Audit Generated ✓

Discovered N tables across N domains. Identified N near-duplicate groups 
affecting N tables. Overall governance grade: B.

**Highest-priority issues:**
- [Domain]: N competing definitions for [entity]
- [Domain]: Primary table undocumented, no dbt management

**Next steps:**
- /wire:ads_metric-audit-generate — inventory semantic layer coverage
- /wire:ads_query-audit-generate — analyse query history patterns
- /wire:ads_dataset-audit-validate — run automated checks on audit completeness
```

## Edge Cases

### No Direct Warehouse Access

If the consultant cannot provide direct SQL access, request a schema export:
- BigQuery: `bq ls --format=prettyjson project:dataset > schema.json`
- Snowflake: Information Schema CSV export from Snowflake console
- dbt: `dbt ls --output json` provides model inventory with metadata

Work from the export rather than blocking on access.

### Very Large Schemas (>500 tables)

Focus the audit on tables with >10,000 rows and tables modified in the last 12 months. Flag the tail of small/stale tables as "low-priority — likely safe to archive" rather than auditing individually.

### No dbt Project

If no dbt project exists, the governance grade ceiling is C — curated tier tables can only be identified by naming convention and metadata, not by lineage or test coverage. Note this explicitly and factor into the governance_design recommendations.

## Output

- `.wire/<release-folder>/artifacts/dataset_audit.md`
- Updated `status.md`
