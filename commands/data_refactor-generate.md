---
description: Generate refactoring plan from seed-based to real client data
argument-hint: <project-folder>
---

# Generate refactoring plan from seed-based to real client data

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.15\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"data_refactor-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.15\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate refactoring plan from seed-based to real client data
argument-hint: <project-folder>
---

# Data Refactor Generate Command

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
- Update `models/staging/_sources.yml`:
  - Change from seed references to real source database/schema
  - Update table and column names as needed

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
   - Change `ref('seed_name')` to `source('source_name', 'table_name')`
   - Update column references where names differ
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
