---
wire_schema: "1.0"
command: generate
artifact: data_refactor
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
  - artifact: dashboards
    action: review
    outcome: approved
auto_validate: false          # validate runs dbt run/dbt test against real client data
delegates_to:
  - utils/precondition_gate
description: Generate refactoring plan from seed-based to real client data
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Refactor Generate Command

Follow `specs/utils/mock_data_delegate.md` before executing the workflow below.

## Purpose

Refactor the seed-based dbt project to use real client data sources. This command generates a refactoring plan, compares the seed-based source schema against the actual client data sources, and executes the necessary changes to staging models, source definitions, and dbt configuration.

This is the transition point from the rapid prototype (built on seed data) to the production implementation (built on real data).

## Usage

```bash
/wire:data_refactor-generate YYYYMMDD_project_name
```

## Prerequisites

- `dbt.review` must be `approved` in status.md
- Real client data access must be confirmed (the consultant should have DDLs or database access)

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.dbt.review` is `approved`
3. Verify `project_type` is `dashboard_first`

If prerequisites not met:
```
Error: dbt project must be reviewed and approved first.

Current status: [status]

Complete dbt review: /wire:dbt-review <project>
```

### Step 2: Confirm Real Data Access

**Process**:
Ask the consultant:

```
## Data Refactor: Confirm Real Data Access

Before refactoring from seed data to real data, I need to understand the client's actual data sources.

Please provide one of the following:
1. **DDL files** — SQL CREATE TABLE statements for the client's actual source tables
   (save as `design/revised_source_tables_ddl.sql`)
2. **Database access** — connection details so I can inspect the schema directly
3. **Standard SaaS schemas** — if using Fivetran/Stitch connectors, tell me which
   sources (e.g., "Fivetran Salesforce", "Fivetran HubSpot") and I'll use known schemas

Which option applies?
```

Wait for the consultant to respond and provide the data.

### Step 3: Analyze Schema Differences

**Process**:
1. Read the original seed-based source schema:
   - `.wire/<project-folder>/design/source_tables_ddl.sql`
   - Find the seeds under either naming: `seed__<table_name>.csv` (releases from Wire 4.1.2) or `<table_name>.csv` (releases started earlier). Look in `dev/seed_data/` and the dbt project's `seeds/` directory, and in the staging models' `ref()` calls. `seed_data.seed_naming` in status.md, where set, says which naming the release uses. Match each seed to its source table by stripping a leading `seed__`.
2. Read the real client source schema:
   - `.wire/<project-folder>/design/revised_source_tables_ddl.sql`
   (or inspect database directly if access provided)

3. Compare schemas and document:
   - Tables present in both (may need column mapping changes)
   - Tables only in seed schema (may need removal or replacement)
   - Tables only in real schema (may need new staging models)
   - Column differences: renamed, type changes, added, removed
   - Key/constraint differences

### Step 4: Generate Refactoring Plan

**Process**:
Create `.wire/<project-folder>/design/data_refactor_plan.md`:

```markdown
# Data Refactor Plan

## Overview

Refactoring from seed-based prototype to real client data for [project_name].
Date: [today's date]

## Schema Comparison Summary

| Metric | Seed Schema | Real Schema |
|--------|-------------|-------------|
| Total tables | [count] | [count] |
| Matched tables | [count] | [count] |
| Seed-only tables | [count] | [count] |
| New real tables | [count] | [count] |

## Table-by-Table Analysis

### [table_name] — [MATCHED/SEED-ONLY/NEW]

**Seed schema:**
- Columns: [list]
- Used by staging model: [model name]

**Real schema:**
- Columns: [list]
- Changes needed: [list of changes]

**Action required:**
- [ ] Update source definition
- [ ] Update staging model SQL
- [ ] Update column mappings
- [ ] Add/remove columns

[Repeat for each table]

## dbt Configuration Changes

### Source Definitions
- Write or update the `_sources.yml` in each `models/staging/stg_<source>/` directory (an existing project keeps its existing source file names):
  - Change from seed references to real source database/schema
  - Update table and column names as needed
  - Follow the source declaration content rules in `data_model-generate` Step 2 for new declarations. These files are written by hand.

### Staging Models
- Models to update: [list with specific changes]
- Models to add: [list]
- Models to remove: [list]

### dbt_project.yml
- Remove seed configuration for source tables
- Update schema references
- Keep seed files as reference (do not delete)

### Integration/Mart Models
- Models impacted by staging changes: [list]

## Estimated Impact

- Files to modify: [count]
- Files to create: [count]
- Files to archive: [count]
- Risk level: [Low/Medium/High] — [rationale]
```

### Step 5: Execute Refactoring

**Process**:
After presenting the plan and getting consultant confirmation:

1. **Update source definitions**:
   - Modify `_sources.yml` to point to real data sources instead of seeds
   - Update database, schema, and table references

2. **Update staging models**:
   - Change `ref('seed__table_name')` or `ref('table_name')` (whichever naming the release's seeds use) to `source('source_name', 'table_name')`
   - Update column references where names differ. Keep the staging models' output column names, so downstream models and dashboards do not change.
   - Add/remove column transformations as needed

3. **Update dbt_project.yml**:
   - Remove or comment out seed configuration for source tables
   - Update any schema/database overrides

4. **Update integration and mart models** if impacted by staging changes

5. **Update target warehouse DDL**:
   - Regenerate `design/target_warehouse_ddl.sql` if the warehouse schema changed

6. **Keep seed files**:
   - Do NOT delete seed CSV files — keep them as reference
   - Add a note to `dev/seed_data/README.md` indicating they are now superseded by real data

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.data_refactor section:
   ```yaml
   data_refactor:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: [today's date]
     tables_refactored: [count]
     staging_models_updated: [count]
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_refactor`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `data_refactor`
- `artifact_name`: `Data Refactor Plan`
- `file_path`: `.wire/releases/[release_folder]/dev/data_refactor.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

**Output**:
```
## Data Refactor Generated Successfully

**Refactor Plan:** `design/data_refactor_plan.md`
**Tables refactored:** [count]
**Staging models updated:** [count]
**New models created:** [count]

### Changes Made
- Updated source definitions from seed to real data
- Modified [count] staging models
- Updated dbt_project.yml configuration
- Seed files preserved in dev/seed_data/ for reference

### Next Steps

1. **Validate refactored project**: `/wire:data_refactor-validate <project>`
   Verify the refactored project compiles and runs against real data
2. After validation, review: `/wire:data_refactor-review <project>`
```

## Edge Cases

### No Real Data DDL Provided

If the consultant hasn't saved the revised DDL:
- Guide them to export DDLs from their database
- For Fivetran/Stitch sources, offer to generate expected schemas from known connector docs
- If using standard SaaS connectors, reference our knowledge of typical schemas

### Major Schema Differences

If the real schema is drastically different from the seed schema:
- Flag this as high-risk refactoring
- Suggest reviewing the data model before proceeding
- Consider whether the data model itself needs regeneration

### Partial Data Access

If only some real data sources are available:
- Refactor what we can
- Keep seed-based sources for tables not yet available
- Document which tables are still using seeds

## Output

This command creates:
- `design/data_refactor_plan.md` — detailed refactoring plan
- Modified dbt source definitions, staging models, and configuration
- Updates `status.md`
