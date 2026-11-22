---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Record stakeholder review of data refactor
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Refactor Review Command

## Purpose

Record stakeholder feedback on the refactored dbt project. The reviewer verifies the transition from seed data to real client data is complete and correct.

## Usage

```bash
/wire:data_refactor-review YYYYMMDD_project_name
```

## Prerequisites

- `data_refactor.validate` must be `pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.data_refactor.validate` is `pass`

If not met:
```
Error: Data refactor must pass validation first.

Run: /wire:data_refactor-validate <project>
```

### Step 2: Present Review Summary

**Process**:
1. Read `.wire/<project-folder>/design/data_refactor_plan.md`
2. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside any other context
3. Present a summary:

```
## Data Refactor Review

### Refactoring Summary
- Tables refactored: [count]
- Staging models updated: [count]
- Source definitions changed from seed to real data
- Validation: PASSED

### Refactor Plan
[Key points from data_refactor_plan.md]

### Review Criteria
- Are all source definitions pointing to the correct real data sources?
- Do staging models correctly transform the real source data?
- Are all dbt tests passing against real data?
- Is the warehouse schema consistent with the design?
- Are seed files preserved as reference?
```

### Step 3: Collect Review Decision

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the review decision for the data refactor?",
    "header": "Review",
    "options": [
      {"label": "Approved", "description": "Refactored project correctly uses real client data"},
      {"label": "Changes requested", "description": "Additional refactoring needed before proceeding"}
    ],
    "multiSelect": false
  }]
}
```

If "Changes requested", ask in chat:
```
What changes are needed? Please describe the issues with the refactored project.
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.data_refactor section:

**If approved**:
```yaml
data_refactor:
  generate: complete
  validate: pass
  review: approved
  reviewed_date: [today's date]
  reviewer: [reviewer name if provided]
```

**If changes requested**:
```yaml
data_refactor:
  generate: complete
  validate: pass
  review: changes_requested
  reviewed_date: [today's date]
  reviewer: [reviewer name if provided]
  review_notes: [summary of requested changes]
```

3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_refactor`
- Action: `review`
- Status: the review state just written to status.md

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

### Step 7: Confirm and Suggest Next Steps

**If approved**:
```
## Data Refactor Review: Approved

The project has been successfully transitioned from seed data to real client data.

### Next Steps
1. **Data quality checks**: `/wire:data_quality-generate <project>`
2. **User acceptance testing**: `/wire:uat-generate <project>`
```

**If changes requested**:
```
## Data Refactor Review: Changes Requested

**Feedback:** [summary]

### Next Steps
1. **Regenerate refactor**: `/wire:data_refactor-generate <project>`
2. Then re-validate: `/wire:data_refactor-validate <project>`
3. Then re-review: `/wire:data_refactor-review <project>`
```

## Output

This command updates `status.md` with the review outcome. No files are created.
