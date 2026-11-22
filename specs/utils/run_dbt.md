---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Run dbt models for the project in dbt Cloud or locally

---

# Run dbt Utility Command

## Purpose

Execute dbt models for a project, either in dbt Cloud (recommended) or locally. Provides options for full refresh, selective runs, and test execution.

## Prerequisites

- dbt project with models generated (`/wire:dbt-generate` completed)
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
1. Check if `.wire/config.md` has dbt Cloud project ID and API key
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
dbt run --select +wh_core__enrolment_fact  # model and all upstream
dbt run --select wh_core__enrolment_fact+  # model and all downstream

# Run models in specific folders
dbt run --select warehouse.core.*

# Full refresh (rebuild incremental models)
dbt run --full-refresh

# Run tests
dbt test

# Run tests for specific models
dbt test --select wh_core__enrolment_fact

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
/wire:dbt-validate <project_id>
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

❌ Model warehouse.core.wh_core__enrolment_fact failed
   Error: Dependency int_core__student not found

   Suggested fix:
   - Ensure upstream model runs first
   - Check ref() syntax: {{ ref('int_core__student') }}

To debug:
1. Review error details: [show full error]
2. Fix the model SQL
3. Re-run: /wire:utils-run-dbt <project_id>
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
- Update semantic layer if needed: /wire:semantic_layer-generate <project_id>
- Generate dashboards: /wire:dashboards-generate <project_id>
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
dbt run --select +wh_core__enrolment_fact
```

### Full Refresh

**For incremental models:**
```bash
dbt run --full-refresh
```

### Test Specific Models

**Run tests for specific models:**
```bash
dbt test --select wh_core__enrolment_fact
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

Please add to .wire/config.md:

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

### MCP Tool Integration

When a dbt MCP server is configured in the project, prefer MCP tools over CLI commands for:
- Running models and tests (MCP handles authentication and error reporting)
- Querying the semantic layer
- Listing available models and metrics

Fall back to CLI commands when MCP tools are unavailable or when you need features not exposed by the MCP server (e.g., `dbt compile --select`, advanced selectors).

### Post-Run Analysis

After `dbt build` or `dbt run` completes, check `target/run_results.json` for detailed execution data:

```json
{
  "results": [
    {
      "unique_id": "model.project.stg_events",
      "status": "success",
      "execution_time": 3.42,
      "adapter_response": { "rows_affected": 150000 }
    }
  ]
}
```

Key fields to check:
- `status`: "success", "error", or "skipped"
- `execution_time`: seconds — flag models > 60s for optimization
- `adapter_response.rows_affected`: row count — useful for data validation
- `failures`: number of test failures (for test results)

## Output

This command:
- Executes dbt run (and optionally dbt test)
- Updates project status with run results
- Provides links to view results
- Suggests next steps
