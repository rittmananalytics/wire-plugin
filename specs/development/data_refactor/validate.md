---
wire_schema: "1.0"
command: validate
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
  - artifact: data_refactor
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate refactored dbt project against real data
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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
   - Missing source references (seeds that weren't properly replaced). Check `ref()` calls for seeds under either naming: `seed__<table_name>` and `<table_name>`.
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
