---
description: Generate seed data files from data model
argument-hint: <project-folder>
---

# Generate seed data files from data model

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Generate seed data files from data model
argument-hint: <project-folder>
---

# Seed Data Generate Command

## Purpose

Generate internally consistent CSV seed data files that enable the dbt project to run immediately without client data access. The seed data must be realistic enough to produce meaningful dashboard visualizations and internally consistent (all foreign key values exist in dimension seeds, dates are coherent, distributions are sensible).

## Usage

```bash
/dp:seed_data:generate YYYYMMDD_project_name
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
3. Verify the required DDL files exist
4. Read the `project_type` and `client` from status.md frontmatter

If prerequisites not met, show error:
```
Error: Data model must be reviewed and approved first.

Current status: [status]

Complete data model review: /dp:data_model:review <project>
```

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
   - File naming: `[table_name].csv` (matching the source table name, lowercase)

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

Add to `dbt_project.yml`:
```yaml
seeds:
  +schema: seed
  project_name:
    +enabled: true
```
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
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `seed_data`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Confirm and Suggest Next Steps

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

1. **Validate seed data**: `/dp:seed_data:validate <project>`
   Checks referential integrity, PK uniqueness, type consistency
2. After validation, review: `/dp:seed_data:review <project>`
3. Then generate dbt project: `/dp:dbt:generate <project>`
```

## Edge Cases

### Missing DDL Files

If source_tables_ddl.sql or target_warehouse_ddl.sql don't exist:
```
Error: DDL files not found. The data model must generate these files first.

Expected files:
- design/source_tables_ddl.sql
- design/target_warehouse_ddl.sql

Run: /dp:data_model:generate <project>
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
- `dev/seed_data/*.csv` — CSV seed files, one per source table
- `dev/seed_data/README.md` — seed data summary and documentation
- Updates `status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
