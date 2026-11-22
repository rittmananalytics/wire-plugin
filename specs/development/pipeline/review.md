---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Present pipeline connections for stakeholder review and approval
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pipeline Review Command

## Purpose

Present the configured pipeline connections for stakeholder review and approval. Routes to the tool-specific review spec for a connection-level summary, then gathers sign-off using the standard review pattern.

## Usage

```bash
/wire:pipeline-review YYYYMMDD_project_name
```

## Prerequisites

- `pipeline.validate == pass` in status.md

## Workflow

### Step 1: Read Status and Route

1. Read `.wire/<project_id>/status.md`
2. Check `artifacts.pipeline.validate`. If not `pass`:
   ```
   Warning: Pipeline has not passed validation yet.
   Run: /wire:pipeline-validate <project_id>
   Proceed anyway? (y/n)
   ```
3. Read `artifacts.pipeline.pipeline_tool`.

### Step 2: Delegate Summary to Tool-Specific Spec

Based on `pipeline_tool`, load and execute the corresponding review spec to build the review summary:

| `pipeline_tool` | Spec |
|----------------|------|
| `fivetran` | `wire/specs/development/pipeline/fivetran/review.md` |
| `dlt` | `wire/specs/development/pipeline/dlt/review.md` |
| `airbyte` | `wire/specs/development/pipeline/airbyte/review.md` |
| `airflow` | `wire/specs/development/pipeline/airflow/review.md` |
| `custom` | Present the pipeline design document and connection configs directly |

### Step 3: Retrieve External Context (Optional)

1. Follow `specs/utils/meeting_context.md` — pass artifact name `pipeline`
2. Follow `specs/utils/atlassian_search.md` — pass artifact name `pipeline`
3. If a document store is configured, follow `specs/utils/docstore_fetch.md` — pass artifact `pipeline`

### Step 4: Gather Feedback

Use AskUserQuestion:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Pipeline Review",
    "options": [
      {"label": "Approved", "description": "Pipeline connections are correctly configured and approved"},
      {"label": "Changes requested", "description": "Pipeline needs adjustments"},
      {"label": "Needs discussion", "description": "Requires further clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 5a: If Approved

Ask: `Who approved the pipeline? (Name and role)`

Update status.md:
```yaml
pipeline:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer]"
  reviewed_date: <today>
```

Suggest next steps:
```
## Pipeline Approved

**Tool**: [pipeline_tool]
**Reviewed by**: [Reviewer]

### Next Steps

Generate the orchestration layer:
  /wire:orchestration-generate <project_id>
```

### Step 5b: If Changes Requested

Ask: `What changes are needed?`

Update status.md:
```yaml
pipeline:
  review: changes_requested
  feedback: "[Feedback]"
  reviewed_date: <today>
```

```
## Pipeline Changes Requested

### Change Requests:
[Feedback]

### Next Steps
1. Address feedback
2. Re-validate: /wire:pipeline-validate <project_id>
3. Re-submit: /wire:pipeline-review <project_id>
```

### Step 6: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md`:
- Artifact: `pipeline`
- Action: `review`
- Status: approved / changes_requested

### Step 7: Sync to Document Store (Optional)

If approved, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file.
