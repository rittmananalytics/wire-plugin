---
wire_schema: "1.0"
command: validate
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
  - artifact: seed_data
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate seed data files
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Seed Data Validation Command

## Purpose

Validate the generated CSV seed data files for structural correctness, referential integrity, and data quality. Ensures the seed data will load successfully into dbt and produce meaningful dashboard results.

## Usage

```bash
/wire:seed_data-validate YYYYMMDD_project_name
```

## Prerequisites

- `seed_data.generate` must be `complete` in status.md
- Seed files must exist in `.wire/<project-folder>/dev/seed_data/`

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.seed_data.generate` is `complete`
3. Verify seed CSV files exist in `dev/seed_data/`

### Step 2: Load Reference Data

**Process**:
1. Read `.wire/<project-folder>/design/source_tables_ddl.sql`
2. Parse DDL to get expected table schemas (columns, types, constraints, FK relationships)
3. Read `.wire/<project-folder>/dev/seed_data/README.md` for documented relationships

### Step 3: Run Validation Checks

For each CSV file in `dev/seed_data/`. Match each file to its DDL table by name: `seed__<table_name>.csv` (new releases) and `<table_name>.csv` (releases under way before Wire 4.1.2) both map to `<table_name>`.

**Naming Check**:
0. All files in the release use one naming, and it matches `seed_data.seed_naming` in status.md where that field is set: `seed_prefix` means `seed__<table_name>.csv`; `legacy` (or no field, on a release generated before 4.1.2) means the existing names. Both are accepted. A mix of the two in one release is a warning, not a failure. Never ask for an existing seed to be renamed.

**Structural Checks**:
1. CSV parses without errors (proper quoting, consistent column count)
2. Header row matches expected columns from DDL
3. No empty files (at least 1 data row)
4. Column count matches DDL column count

**Primary Key Checks**:
5. No duplicate values in PK columns
6. No NULL values in PK columns

**Foreign Key Checks**:
7. Every FK value exists in the referenced parent table's PK column
8. No orphaned records (fact rows referencing non-existent dimension rows)

**Data Type Checks**:
9. Date columns contain valid dates (YYYY-MM-DD format)
10. Numeric columns contain valid numbers
11. No NULL values in NOT NULL columns (per DDL constraints)

**Data Quality Checks**:
12. Fact tables have variation in measure columns (not all same value)
13. Date ranges are reasonable (within last 2-3 years)
14. Categorical values are consistent within each column

### Step 4: Generate Validation Report

**Process**:
Create validation report with results:

```
## Seed Data Validation Report

**Project:** [project_name]
**Date:** [today's date]
**Result:** [PASS/FAIL]

### Summary

- **Files checked:** [count]
- **Total checks:** [count]
- **Passed:** [count]
- **Failed:** [count]
- **Warnings:** [count]

### Results by File

#### [filename].csv
- [count] rows, [count] columns
- Checks: [passed]/[total]
- Issues: [list any failures]

### Failed Checks

| # | File | Check | Details |
|---|------|-------|---------|
| 1 | [file] | [check name] | [specific failure details] |

### Warnings

| # | File | Warning | Details |
|---|------|---------|---------|
| 1 | [file] | [warning] | [details] |
```

### Step 5: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.seed_data section:
   ```yaml
   seed_data:
     generate: complete
     validate: pass  # or fail
     review: not_started
     validated_date: [today's date]
     validation_checks: [passed]/[total]
   ```
3. Write updated status.md

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `seed_data`
- Action: `validate`
- Status: the validate state just written to status.md

### Step 7: Confirm and Suggest Next Steps

**If all checks pass**:
```
## Seed Data Validation: PASS

All [count] checks passed across [count] files.

### Next Steps
1. **Review seed data**: `/wire:seed_data-review <project>`
2. After approval, generate dbt: `/wire:dbt-generate <project>`
```

**If checks fail**:
```
## Seed Data Validation: FAIL

[passed]/[total] checks passed. [failed] failures found.

### Failures
[list failures with details]

### Recommended Action
Regenerate seed data: `/wire:seed_data-generate <project>`
Or fix the specific issues listed above manually.
```

## Edge Cases

### No Seed Files Found

If `dev/seed_data/` is empty or missing:
```
Error: No seed data files found.

Generate seed data first: /wire:seed_data-generate <project>
```

### DDL File Missing

If DDL files are missing, validate what we can (CSV structure, basic type checks) and note that FK validation was skipped.

## Output

This command outputs a validation report to the conversation and updates `status.md`. No files are created.
