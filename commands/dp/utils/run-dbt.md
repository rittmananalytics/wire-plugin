---
description: Run dbt models
argument-hint: <project-folder>
---

# Run dbt models

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.agent_v2` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.agent_v2/` in specs refers to the `.agent_v2/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Run dbt models for the project in dbt Cloud or locally
---

# Run dbt Utility Command

## Purpose

Execute dbt models for a project, either in dbt Cloud (recommended) or locally. Provides options for full refresh, selective runs, and test execution.

## Prerequisites

- dbt project with models generated (`/dp:dbt:generate` completed)
- dbt Cloud account OR dbt Core installed locally
- BigQuery/warehouse credentials configured

## Workflow

### Step 1: Determine dbt Execution Environment

**Ask user:**

```
How would you like to run dbt?

1. dbt Cloud (recommended)
2. dbt Core (local)
3. Show me the commands to run manually
```

### Step 2a: If dbt Cloud

**Process**:
1. Check if `.agent_v2/config.md` has dbt Cloud project ID and API key
2. If not configured, prompt user to add credentials
3. Use dbt Cloud API to trigger job

**API Call**:
```bash
curl -X POST \
  https://cloud.getdbt.com/api/v2/accounts/{account_id}/jobs/{job_id}/run/ \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  -d '{"cause": "Triggered by agent_v2"}'
```

**Monitor Run**:
```
dbt Cloud job triggered: Run #{run_id}

Status: Running...
View in dbt Cloud: https://cloud.getdbt.com/...

Checking status every 30 seconds...
```

**When complete**:
```
✓ dbt run completed successfully

Models run: [count]
Tests passed: [count]
Execution time: [time]

View full results: [dbt Cloud URL]
```

### Step 2b: If dbt Core (local)

**Process**:
1. Verify dbt is installed: `dbt --version`
2. Verify profiles.yml is configured
3. Run dbt commands via Bash tool

**Commands to run**:

```bash
# Navigate to dbt project
cd dbt/

# Install dependencies
dbt deps

# Run models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
```

**Output results**:
```
✓ dbt deps completed
✓ dbt run completed: [count] models built
✓ dbt test completed: [count] tests passed

Models materialized:
- staging: [count] views
- integration: [count] views
- warehouse: [count] tables

Tests:
- Passed: [count]
- Failed: [count]

[If failures, show details]
```

### Step 2c: If show manual commands

**Output**:
```
## Manual dbt Execution

### Using dbt Cloud:
1. Go to https://cloud.getdbt.com
2. Navigate to your project
3. Click "Run" or trigger a job
4. Select environment and models to run

### Using dbt Core (command line):

```bash
# Navigate to dbt project
cd dbt/

# Install dependencies (first time only)
dbt deps

# Run all models
dbt run

# Run specific models
dbt run --select staging.<source_name>.*
dbt run --select +enrolment_fct  # model and all upstream
dbt run --select enrolment_fct+  # model and all downstream

# Run models in specific folders
dbt run --select warehouse.core.*

# Full refresh (rebuild incremental models)
dbt run --full-refresh

# Run tests
dbt test

# Run tests for specific models
dbt test --select enrolment_fct

# Generate documentation
dbt docs generate

# Serve documentation locally
dbt docs serve
```

### Useful Options:

```bash
# Run in target environment
dbt run --target prod

# Run with specific vars
dbt run --vars '{"current_academic_year": "24/25"}'

# Parallel threads
dbt run --threads 4

# Debug
dbt run --debug
```

### After Running:

Check the results and update project status:
/dp:dbt:validate <project_id>
```

### Step 3: Handle Errors

**If dbt run fails:**

1. Parse error messages
2. Identify failing models
3. Suggest fixes:

```
dbt run failed with [count] errors:

❌ Model staging.<source_name>.stg_<source_name>__<entity> failed
   Error: Syntax error at line 23

   Suggested fix:
   - Check SQL syntax in dbt/models/staging/<source_name>/stg_<source_name>__<entity>.sql
   - Verify column names match source schema

❌ Model warehouse.core.enrolment_fct failed
   Error: Dependency int__student not found

   Suggested fix:
   - Ensure upstream model runs first
   - Check ref() syntax: {{ ref('int__student') }}

To debug:
1. Review error details: [show full error]
2. Fix the model SQL
3. Re-run: /dp:utils:run-dbt <project_id>
```

### Step 4: Update Status

**If run successful:**

**Process**:
1. Read current status file
2. Update dbt artifact:
   ```yaml
   dbt:
     generate: complete
     validate: pass  # if tests also passed
     last_run: 2026-02-13T10:30:00Z
     models_run: [count]
     tests_passed: [count]
   ```
3. Write updated status.md

**Output**:
```
Status updated: dbt models validated successfully

Next steps:
- Review results in BigQuery/warehouse
- Update semantic layer if needed: /dp:semantic_layer:generate <project_id>
- Generate dashboards: /dp:dashboards:generate <project_id>
```

## Advanced Options

### Selective Runs

**Run only specific layers:**
```bash
# Only staging models
dbt run --select staging.*

# Only warehouse models
dbt run --select warehouse.*

# Specific model and dependencies
dbt run --select +enrolment_fct
```

### Full Refresh

**For incremental models:**
```bash
dbt run --full-refresh
```

### Test Specific Models

**Run tests for specific models:**
```bash
dbt test --select enrolment_fct
dbt test --select warehouse.core.*
```

## Edge Cases

### dbt Not Installed (local)

```
Error: dbt not found

dbt Core is not installed. Please:
1. Install dbt: pip install dbt-bigquery (or dbt-snowflake, etc.)
2. Configure profiles.yml
3. Try again

Or use dbt Cloud instead (recommended).
```

### profiles.yml Not Configured

```
Error: dbt profile not configured

Please configure ~/.dbt/profiles.yml with your warehouse credentials.

See: https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml
```

### dbt Cloud API Not Configured

```
Error: dbt Cloud credentials not found

Please add to .agent_v2/config.md:

```yaml
dbt_cloud:
  account_id: "your_account_id"
  project_id: "your_project_id"
  api_token: "your_api_token"
```

Get your API token from: https://cloud.getdbt.com/settings/profile
```

### Models Already Built

If target tables already exist:

```
Warning: Some models already exist in the warehouse.

Options:
1. Run normally (will refresh existing models)
2. Full refresh (rebuild everything from scratch)
3. Cancel

Which would you prefer?
```

## Output

This command:
- Executes dbt run (and optionally dbt test)
- Updates project status with run results
- Provides links to view results
- Suggests next steps

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
