---
description: Generate visualization catalog from Lovable output
argument-hint: <project-folder>
---

# Generate visualization catalog from Lovable output

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
description: Generate visualization catalog from Lovable output
argument-hint: <project-folder>
---

# Visualization Catalog Generate Command

## Purpose

Parse the raw CSV and markdown files saved from the Lovable mock session into a structured visualization catalog. This catalog serves as the primary input for downstream data modeling, dbt generation, and LookML dashboard creation.

This is a **generate-only** artifact (no validate or review steps).

## Usage

```bash
/wire:viz_catalog-generate YYYYMMDD_project_name
```

## Prerequisites

- `mockups.generate` must be `complete` in status.md
- `mockups.review` must be `approved` in status.md
- Files must exist:
  - `.wire/<project-folder>/design/dashboard_visualization_catalog.csv`
  - `.wire/<project-folder>/design/dashboard_spec.md`

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `project_type` is `dashboard_first`
3. Verify `artifacts.mockups.review` is `approved`
4. Verify the required input files exist

If prerequisites not met, show error:
```
Error: Mockups must be reviewed and approved first.

Current status: [status]

Complete mockups review: /wire:mockups-review <project>
```

### Step 2: Parse Dashboard Visualization Catalog CSV

**Process**:
1. Read `.wire/<project-folder>/design/dashboard_visualization_catalog.csv`
2. Parse the CSV into structured records with these fields:
   - Dashboard page name
   - Visualization name
   - Chart/table type
   - Required measures
   - Required dimensions
3. Handle CSV variations (Lovable may produce slightly different column names):
   - Look for columns containing "page", "dashboard", "visualization", "chart", "type", "measure", "dimension"
   - Map to canonical field names

### Step 3: Parse Dashboard Specification

**Process**:
1. Read `.wire/<project-folder>/design/dashboard_spec.md`
2. Extract:
   - Dashboard pages and their purposes
   - Visualization descriptions and layout notes
   - Filter specifications
   - Any interaction/drill-down requirements

### Step 4: Cross-Reference with Requirements

**Process**:
1. Read `.wire/<project-folder>/requirements/requirements_specification.md`
2. For each requirement/question in the requirements:
   - Identify which dashboard visualizations address it
   - Flag any requirements not covered by the mock visualizations
3. For each visualization:
   - Link back to the requirement(s) it satisfies

### Step 5: Generate Structured Catalog

**Process**:
Create `.wire/<project-folder>/design/visualization_catalog.md` with this structure:

```markdown
# Visualization Catalog

## Summary

- **Total Dashboards:** [count]
- **Total Visualizations:** [count]
- **Unique Measures:** [count]
- **Unique Dimensions:** [count]
- **Requirements Coverage:** [covered]/[total] requirements addressed

## Dashboards

### [Dashboard Page Name]

**Purpose:** [from spec]

| # | Visualization | Type | Measures | Dimensions | Requirement(s) |
|---|--------------|------|----------|------------|-----------------|
| 1 | [name] | [bar/line/table/KPI/etc.] | [measure1, measure2] | [dim1, dim2] | [REQ-1, REQ-3] |
| 2 | ... | ... | ... | ... | ... |

[Repeat for each dashboard page]

## Measures Index

| Measure | Used In | Count |
|---------|---------|-------|
| [measure_name] | [Dashboard 1 #2, Dashboard 2 #1] | [n] |

## Dimensions Index

| Dimension | Used In | Count |
|-----------|---------|-------|
| [dimension_name] | [Dashboard 1 #1, Dashboard 1 #2] | [n] |

## Requirements Coverage

| Requirement | Addressed By | Status |
|-------------|-------------|--------|
| [REQ-1] [description] | Dashboard 1 #1, Dashboard 1 #3 | Covered |
| [REQ-5] [description] | - | Not Covered |

## Notes

- [Any observations about gaps, redundancies, or suggestions]
```

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.viz_catalog section:
   ```yaml
   viz_catalog:
     generate: complete
     generated_date: [today's date]
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `viz_catalog`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## Visualization Catalog Generated Successfully

**File:** `design/visualization_catalog.md`

### Summary
- [X] dashboards with [Y] total visualizations
- [Z] unique measures, [W] unique dimensions
- [covered]/[total] requirements covered

### Gaps Found
[List any uncovered requirements, if any]

### Next Steps

1. **Review the catalog** for completeness and accuracy
2. **Generate data model**: `/wire:data_model-generate <project>`
   The data model will use this catalog to determine required measures and dimensions
```

## Edge Cases

### CSV Missing or Malformed

If the CSV file doesn't exist or can't be parsed:
1. Check if the file exists at alternative paths
2. Ask the consultant to re-download from Lovable
3. If the file exists but has unexpected format, attempt best-effort parsing and note issues

### Dashboard Spec Missing

If only the CSV exists without the spec:
- Generate the catalog from CSV data alone
- Note that dashboard purposes and layout details are missing
- Suggest the consultant return to Lovable to generate the spec

### No Requirements Match

If some visualizations don't map to any requirement:
- Include them in the catalog with "N/A" in the Requirements column
- Note these in the summary as "Additional visualizations beyond stated requirements"

## Output

This command creates:
- `design/visualization_catalog.md` — structured catalog with dashboards, measures, dimensions, and requirements coverage
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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
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
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
