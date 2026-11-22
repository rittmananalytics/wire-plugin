---
wire_schema: "1.0"
command: generate
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
  - artifact: pipeline_design
    action: review
    outcome: approved
auto_validate: false          # validate makes live Fivetran MCP calls per connection (connection tests, schema/column config); the airflow route makes none
delegates_to:
  - utils/precondition_gate
description: Create and configure data pipeline connections based on approved pipeline design
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pipeline Generate Command

Follow `specs/utils/pipeline_engineer_delegate.md` before executing the workflow below.

## Purpose

Create and configure data pipeline connections based on the approved pipeline architecture. Routes to the appropriate tool-specific spec based on `pipeline_tool` recorded in `status.md` during pipeline design.

## Usage

```bash
/wire:pipeline-generate YYYYMMDD_project_name
```

## Prerequisites

- `pipeline_design`: `review: approved`
- `artifacts.pipeline.pipeline_tool` must be set in `status.md` (written by `/wire:pipeline_design-generate`)

## Workflow

### Step 1: Read Status and Route

1. Read `.wire/<project_id>/status.md`
2. Verify `pipeline_design.review == approved`. If not:
   ```
   Error: Pipeline design must be approved before creating pipeline connections.
   Run: /wire:pipeline_design-review <project_id>
   ```
3. Read `artifacts.pipeline.pipeline_tool`. If null or absent:
   ```
   Error: No pipeline tool selected. Re-run pipeline design to choose a tool.
   Run: /wire:pipeline_design-generate <project_id>
   ```

### Step 2: Delegate to Tool-Specific Spec

Based on `pipeline_tool`, load and execute the corresponding spec in full:

| `pipeline_tool` | Spec |
|----------------|------|
| `fivetran` | `wire/specs/development/pipeline/fivetran/generate.md` |
| `dlt` | `wire/specs/development/pipeline/dlt/generate.md` |
| `airbyte` | `wire/specs/development/pipeline/airbyte/generate.md` |
| `airflow` | `wire/specs/development/pipeline/airflow/generate.md` |
| `custom` | Follow the bespoke approach documented in `.wire/<project_id>/design/pipeline_architecture.md` |

Pass `project_id` as context to the delegated spec.

### Step 3: Verify Output

After the tool-specific spec completes, confirm:
- A pipeline connections/config artifact exists under `.wire/<project_id>/development/pipeline/`
- `artifacts.pipeline.generate == complete` in status.md

If the tool-specific spec did not update status.md, update it now:
```yaml
pipeline:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: <today>
```

### Step 4: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `pipeline`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 5: Sync to Document Store (Optional)

If a document store is configured, follow `specs/utils/docstore_sync.md`:
- `artifact_id`: `pipeline`
- `artifact_name`: `Data Pipeline`
- `file_path`: `.wire/<project_id>/development/pipeline/pipeline_connections.md`
- `project_id`: the project folder

### Step 6: Suggest Next Steps

```
## Pipeline Generated

**Tool**: [pipeline_tool]
**Artifact**: .wire/<project_id>/development/pipeline/pipeline_connections.md

### Next Steps

1. Validate the pipeline:
   /wire:pipeline-validate <project_id>
```
