---
wire_schema: "1.0"
command: validate
artifact: pipeline
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
  - artifact: pipeline
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate pipeline connections and configuration against the pipeline design
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pipeline Validate Command

## Purpose

Validate that pipeline connections are correctly configured, healthy, and match the approved pipeline architecture. Routes to the appropriate tool-specific validation spec based on `pipeline_tool` in `status.md`.

## Usage

```bash
/wire:pipeline-validate YYYYMMDD_project_name
```

## Prerequisites

- `pipeline.generate == complete` in status.md

## Workflow

### Step 1: Read Status and Route

1. Read `.wire/<project_id>/status.md`
2. Verify `artifacts.pipeline.generate == complete`. If not:
   ```
   Error: Pipeline not generated yet.
   Run: /wire:pipeline-generate <project_id>
   ```
3. Read `artifacts.pipeline.pipeline_tool`.

### Step 2: Delegate to Tool-Specific Spec

Based on `pipeline_tool`, load and execute the corresponding validation spec in full:

| `pipeline_tool` | Spec |
|----------------|------|
| `fivetran` | `wire/specs/development/pipeline/fivetran/validate.md` |
| `dlt` | `wire/specs/development/pipeline/dlt/validate.md` |
| `airbyte` | `wire/specs/development/pipeline/airbyte/validate.md` |
| `airflow` | `wire/specs/development/pipeline/airflow/validate.md` |
| `custom` | Apply the validation checklist from the pipeline design document |

### Step 3: Verify Status Updated

After the tool-specific spec completes, confirm `artifacts.pipeline.validate` is set to `pass` or `fail` in status.md.

### Step 4: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `pipeline`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)
