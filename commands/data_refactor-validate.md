---
description: Validate refactored dbt project against real data
argument-hint: <project-folder>
---

# Validate refactored dbt project against real data

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.4\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"data_refactor-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.4\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate refactored dbt project against real data
argument-hint: <project-folder>
---

# Data Refactor Validation Command

## Purpose

Validate that the refactored dbt project (transitioned from seed data to real client data) compiles correctly and runs successfully against the actual data sources.

## Usage

```bash
/wire:data_refactor-validate YYYYMMDD_project_name
```

## Prerequisites

- `data_refactor.generate` must be `complete` in status.md

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.data_refactor.generate` is `complete`

### Step 2: Compile Check

**Process**:
1. Navigate to the dbt project directory
2. Run `dbt compile` to verify all models parse correctly
3. Check for:
   - Missing source references (seeds that weren't properly replaced)
   - Undefined column references
   - SQL syntax errors from schema changes
   - Broken ref() chains

### Step 3: Run Models

**Process**:
1. Run `dbt run` to execute all models against real data
2. Track results per model:
   - Staging models: do they run without SQL errors?
   - Integration models: do joins work with real data?
   - Mart models: do aggregations produce results?
3. Note any failures with specific error messages

### Step 4: Run Tests

**Process**:
1. Run `dbt test` to execute all configured tests
2. Track results:
   - Schema tests (unique, not_null, accepted_values, relationships)
   - Custom data tests
3. Note test failures — some may be expected if real data has quality issues

### Step 5: Compare Outputs

**Process**:
1. Compare the refactored output against expected warehouse schema:
   - Read `design/target_warehouse_ddl.sql`
   - Verify all target tables were created
   - Verify column counts and types match expectations
2. Check row counts in mart tables (should be non-zero if data exists)

### Step 6: Generate Validation Report

**Process**:
Present validation results:

```
## Data Refactor Validation Report

**Project:** [project_name]
**Date:** [today's date]
**Result:** [PASS/FAIL]

### Compile Check
- Status: [PASS/FAIL]
- Models compiled: [count]
- Errors: [list if any]

### Model Execution
- Status: [PASS/FAIL]
- Models run: [count]
- Successful: [count]
- Failed: [count]
- Failures: [list with error details]

### Test Results
- Status: [PASS/FAIL]
- Tests run: [count]
- Passed: [count]
- Failed: [count]
- Failures: [list with details]

### Schema Comparison
- Target tables expected: [count]
- Target tables created: [count]
- Missing tables: [list if any]

### Summary
[Overall assessment — is the refactored project production-ready?]
```

### Step 7: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.data_refactor section:
   ```yaml
   data_refactor:
     generate: complete
     validate: pass  # or fail
     review: not_started
     validated_date: [today's date]
   ```
3. Write updated status.md

### Step 8: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_refactor`
- Action: `validate`
- Status: the validate state just written to status.md

### Step 9: Confirm and Suggest Next Steps

**If all checks pass**:
```
## Data Refactor Validation: PASS

The refactored project compiles and runs successfully against real data.

### Next Steps
1. **Review refactored project**: `/wire:data_refactor-review <project>`
```

**If checks fail**:
```
## Data Refactor Validation: FAIL

### Failures
[list failures]

### Recommended Action
Fix the issues identified above and re-run: `/wire:data_refactor-validate <project>`
If schema changes are needed, regenerate: `/wire:data_refactor-generate <project>`
```

## Edge Cases

### No Database Access

If real database is unavailable for testing:
- Run compile check only
- Note that runtime validation was skipped
- Set validate to `pass` with a note about compile-only validation

### Partial Failures

If some models succeed but others fail:
- Report which layers are working (staging OK, integration fails, etc.)
- Set validate to `fail` — all layers must pass for validation

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
