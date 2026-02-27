---
description: Validate seed data files
argument-hint: <project-folder>
---

# Validate seed data files

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
description: Validate seed data files
argument-hint: <project-folder>
---

# Seed Data Validation Command

## Purpose

Validate the generated CSV seed data files for structural correctness, referential integrity, and data quality. Ensures the seed data will load successfully into dbt and produce meaningful dashboard results.

## Usage

```bash
/wire:dp-seed_data-validate YYYYMMDD_project_name
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

For each CSV file in `dev/seed_data/`:

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

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `seed_data`
- Action: `validate`
- Status: the validate state just written to status.md

### Step 7: Confirm and Suggest Next Steps

**If all checks pass**:
```
## Seed Data Validation: PASS

All [count] checks passed across [count] files.

### Next Steps
1. **Review seed data**: `/wire:dp-seed_data-review <project>`
2. After approval, generate dbt: `/wire:dp-dbt-generate <project>`
```

**If checks fail**:
```
## Seed Data Validation: FAIL

[passed]/[total] checks passed. [failed] failures found.

### Failures
[list failures with details]

### Recommended Action
Regenerate seed data: `/wire:dp-seed_data-generate <project>`
Or fix the specific issues listed above manually.
```

## Edge Cases

### No Seed Files Found

If `dev/seed_data/` is empty or missing:
```
Error: No seed data files found.

Generate seed data first: /wire:dp-seed_data-generate <project>
```

### DDL File Missing

If DDL files are missing, validate what we can (CSV structure, basic type checks) and note that FK validation was skipped.

## Output

This command outputs a validation report to the conversation and updates `status.md`. No files are created.

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
| YYYY-MM-DD HH:MM | /wire:dp-<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:dp-*` command that was invoked (e.g., `/wire:dp-requirements-generate`, `/wire:dp-new`, `/wire:dp-dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:dp-new` created a new project
  - `archived` — `/wire:dp-archive` archived a project
  - `removed` — `/wire:dp-remove` deleted a project
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
| 2026-02-22 14:35 | /wire:dp-new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:dp-requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:dp-requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:dp-requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:dp-conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:dp-conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:dp-conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:dp-conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:dp-conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:dp-conceptual_model-review | approved | Reviewed by John Doe |
```
