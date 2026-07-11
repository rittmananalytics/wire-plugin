---
description: Generate visualization catalog from mockup output
argument-hint: <project-folder>
---

# Generate visualization catalog from mockup output

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
description: Generate visualization catalog from mockup output
argument-hint: <project-folder>
---

# Visualization Catalog Generate Command

Follow `specs/utils/data_designer_delegate.md` before executing the workflow below.

## Purpose

Parse the visualization catalog CSV and dashboard specification markdown files produced by `/wire:mockups-generate` into a structured visualization catalog. This catalog serves as the primary input for downstream data modeling, dbt generation, and LookML dashboard creation.

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
3. Handle CSV variations (column names may differ slightly):
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

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `viz_catalog`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `viz_catalog`
- `artifact_name`: `Visualization Catalog`
- `file_path`: `.wire/releases/[release_folder]/design/viz_catalog.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

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
2. If the file is missing entirely, ask the consultant to re-run `/wire:mockups-generate <project>` — it generates this file automatically
3. If the file exists but has unexpected format, attempt best-effort parsing and note issues

### Dashboard Spec Missing

If only the CSV exists without the spec:
- Generate the catalog from CSV data alone
- Note that dashboard purposes and layout details are missing
- Suggest re-running `/wire:mockups-generate <project>` to regenerate both files

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

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

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
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
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
