---
wire_schema: "1.0"
command: generate
artifact: seed_data
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: viz_catalog
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Generate seed data files from data model
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Seed Data Generate Command

Follow `specs/utils/mock_data_delegate.md` before executing the workflow below.

## Purpose

Generate internally consistent CSV seed data files that enable the dbt project to run immediately without client data access. The seed data must be realistic enough to produce meaningful dashboard visualizations and internally consistent (all foreign key values exist in dimension seeds, dates are coherent, distributions are sensible).

## Usage

```bash
/wire:seed_data-generate YYYYMMDD_project_name
```

## Prerequisites

- `data_model.review` must be `approved` in status.md
- The following design files must exist:
  - `.wire/<project-folder>/design/source_tables_ddl.sql`
  - `.wire/<project-folder>/design/target_warehouse_ddl.sql`
  - `.wire/<project-folder>/design/visualization_catalog.md` (if dashboard_first project)

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.data_model.review` is `approved`
3. Read the `project_type` and `client` from status.md frontmatter
4. Verify each required input file exists **by name**, and name the command that writes any
   that are missing:

| File | Written by | Required for |
|---|---|---|
| `design/source_tables_ddl.sql` | `data_model-generate` | every release type |
| `design/target_warehouse_ddl.sql` | `data_model-generate` | every release type |
| `design/visualization_catalog.md` | **`viz_catalog-generate`** | `dashboard_first` only |

If the data model is not approved:
```
Error: Data model must be reviewed and approved first.

Current status: [status]

Complete data model review: /wire:data_model-review <project>
```

If a required file is missing, stop and name both the file and its writer:
```
Error: seed data cannot be generated. Missing required input(s):

  [path]   written by  [command]

Run the command(s) above, then re-run: /wire:seed_data-generate <project>
```

**`design/visualization_catalog.md` is the one people miss.** On a `dashboard_first` release,
`mockups-generate` Step 4A already wrote `design/dashboard_visualization_catalog.csv`, so
`viz_catalog-generate` looks redundant and gets skipped. It is not redundant: it is the only
writer of `design/visualization_catalog.md`, and that file is what tells Step 3 below which
measures must return a non-zero value. Do not substitute the CSV. Do not proceed without the
file. Stop and name `viz_catalog-generate`.

In v4.0.0 the precondition gate blocks this case before Step 1 runs, because
`dashboard_first.yaml` declares `seed_data` as depending on `viz_catalog: generate: complete`.
This check is the backstop for a release whose gate was overridden, and for release types whose
YAML does not carry that edge.

### Step 2: Analyze Data Model

**Process**:
1. Read `.wire/<project-folder>/design/source_tables_ddl.sql`
2. Read `.wire/<project-folder>/design/target_warehouse_ddl.sql`
3. Parse both DDL files to extract:
   - Table names and their schemas
   - Column names, data types, and constraints
   - Primary key columns
   - Foreign key relationships between tables
   - NOT NULL constraints

4. If visualization catalog exists, read `.wire/<project-folder>/design/visualization_catalog.md`:
   - Identify which measures and dimensions are needed
   - Ensure seed data will produce non-zero values for key metrics

### Step 2.5: Choose the Seed Naming

New releases name seed files `seed__<table_name>.csv` and load them to the `seeds` schema. A release already under way keeps the names it has, so `data_refactor` still finds them. Never rename an existing seed.

Use the **legacy** naming (`<table_name>.csv`, existing schema) if any of these is true:
- `status.md` has `seed_data.seed_naming: legacy`.
- `status.md` shows `seed_data.generate: complete` with no `seed_naming` field (seeds generated before Wire 4.1.2).
- `dev/seed_data/`, or the dbt project's `seeds/` directory, already holds CSV files for this release that are not named `seed__*`.

Otherwise use the **seed_prefix** naming. Record the choice in Step 6 as `seed_naming: seed_prefix | legacy`.

Seed columns keep the CSV's column names (the source column names from the DDL). The model column prefix rules do not apply to seeds. Only a staging model reads a seed.

### Step 3: Design Seed Data Strategy

**Process**:
1. For each source table in `source_tables_ddl.sql`, plan a seed CSV file:
   - Determine appropriate row counts (enough for meaningful visualizations, typically 10-100 per dimension table, 100-1000 per fact table)
   - Plan realistic value distributions
   - Map foreign key dependencies to ensure referential integrity

2. Build a dependency graph:
   - Dimension/lookup tables must be generated before fact tables that reference them
   - Ensure all FK values used in fact tables exist in their referenced dimension tables

3. Plan domain-specific realistic data:
   - Use the client name and domain context to generate contextually appropriate names, dates, categories
   - Ensure date ranges are sensible (e.g., recent 1-2 years)
   - Create varied but realistic distributions (not all values the same)

### Step 4: Generate CSV Seed Files

**Process**:
For each source table, in dependency order:

1. Generate a CSV file with:
   - Header row matching the column names from the DDL
   - Data rows with realistic, domain-appropriate values
   - Proper data types (dates as YYYY-MM-DD, numbers as plain digits, strings quoted if they contain commas)

2. **Referential Integrity Rules**:
   - Every FK value in a child table MUST exist as a PK in the parent table
   - No duplicate primary key values
   - No NULL values in NOT NULL columns
   - Date columns use consistent format (YYYY-MM-DD)

3. **Distribution Rules**:
   - Fact tables should have varied measure values (not all zeros or same value)
   - Categorical dimensions should have realistic distributions (not uniform)
   - Date facts should span a reasonable date range
   - Some records should have NULL in nullable columns (for testing NULL handling)

4. Save each CSV to `.wire/<project-folder>/dev/seed_data/`:
   - File naming (seed_prefix): `seed__[table_name].csv` (the source table name, lowercase)
   - File naming (legacy, release already under way): `[table_name].csv`

### Step 5: Generate Seed Data Summary

**Process**:
Create `.wire/<project-folder>/dev/seed_data/README.md`:

```markdown
# Seed Data Summary

## Overview

Generated seed data for [project_name] — [client_name]
Generated date: [today's date]

## Files

| File | Source Table | Rows | Description |
|------|-------------|------|-------------|
| [filename].csv | [table_name] | [count] | [brief description] |

## Dependency Order

Load seeds in this order to maintain referential integrity:
1. [dimension_table_1].csv
2. [dimension_table_2].csv
3. [fact_table_1].csv (references: dimension_table_1, dimension_table_2)

## Foreign Key Relationships

| Child Table | FK Column | Parent Table | PK Column |
|------------|-----------|--------------|-----------|
| [fact_orders] | [customer_id] | [dim_customers] | [customer_id] |

## Data Characteristics

- Date range: [start_date] to [end_date]
- [Key distribution notes]

## dbt Configuration

Add to `dbt_project.yml` (seed_prefix naming, new releases):
```yaml
seeds:
  <project_name>:
    +schema: seeds
    +enabled: true
```

For legacy naming, keep the seed schema the project already uses (earlier Wire releases wrote `+schema: seed`).
```

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.seed_data section:
   ```yaml
   seed_data:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: [today's date]
     seed_file_count: [number of CSV files]
     seed_naming: seed_prefix | legacy   # from Step 2.5
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `seed_data`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `seed_data`
- `artifact_name`: `Seed Data`
- `file_path`: `.wire/releases/[release_folder]/dev/seed_data.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

**Output**:
```
## Seed Data Generated Successfully

**Location:** `dev/seed_data/`
**Files:** [count] CSV files
**Total rows:** [total across all files]

### Files Generated
- [filename].csv — [rows] rows ([description])
- ...

### Next Steps

1. **Validate seed data**: `/wire:seed_data-validate <project>`
   Checks referential integrity, PK uniqueness, type consistency
2. After validation, review: `/wire:seed_data-review <project>`
3. Then generate dbt project: `/wire:dbt-generate <project>`
```

## Edge Cases

### Missing DDL Files

If source_tables_ddl.sql or target_warehouse_ddl.sql don't exist:
```
Error: DDL files not found. The data model must generate these files first.

Expected files:
- design/source_tables_ddl.sql
- design/target_warehouse_ddl.sql

Run: /wire:data_model-generate <project>
```

### Circular Foreign Keys

If the dependency graph has cycles:
- Break the cycle by generating one table with placeholder FK values
- Then update those values after the referenced table is generated
- Note this in the README

### Very Large Tables

If the DDL suggests a table would need many rows for realistic data:
- Cap at 1000 rows for fact tables
- Cap at 100 rows for dimension tables
- Note the caps in the README

## Output

This command creates:
- `dev/seed_data/*.csv`: CSV seed files, one per source table (`seed__<table_name>.csv` in new releases)
- `dev/seed_data/README.md` — seed data summary and documentation
- Updates `status.md`
