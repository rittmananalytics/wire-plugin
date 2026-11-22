---
wire_schema: "1.0"
command: generate
artifact: viz_catalog
domain: design
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
  - artifact: mockups
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate visualization catalog from mockup output
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Visualization Catalog Generate Command

Follow `specs/utils/data_designer_delegate.md` before executing the workflow below.

## Purpose

Parse the visualization catalog CSV and dashboard specification markdown files produced by `/wire:mockups-generate` into a structured visualization catalog. This catalog serves as the primary input for downstream data modeling, dbt generation, and LookML dashboard creation.

This is a **generate-only** artifact (no validate or review steps).

**Normally you do not run this by hand.** `mockups-review` Step 4a.1 runs it automatically on
approval for `dashboard_first` and `dashboard_extension` releases, because every input it needs
is already on disk at that point and there is no decision for a person to make in between.
Running it directly is still valid and idempotent: use it to regenerate the catalog after
editing the CSV or the dashboard spec by hand, or if the automatic run reported a failure.

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
