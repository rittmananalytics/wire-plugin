---
wire_schema: "1.0"
command: review
artifact: seed_data
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
  - artifact: seed_data
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Record stakeholder review of seed data
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Seed Data Review Command

## Purpose

Record stakeholder feedback on the generated seed data. Captures approval or change requests and updates tracking. The reviewer should verify the seed data is realistic, domain-appropriate, and sufficient for initial dashboard visualization.

## Usage

```bash
/wire:seed_data-review YYYYMMDD_project_name
```

## Prerequisites

- `seed_data.validate` must be `pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.seed_data.validate` is `pass`

If not met:
```
Error: Seed data must pass validation first.

Run: /wire:seed_data-validate <project>
```

### Step 2: Present Review Summary

**Process**:
1. Read `.wire/<project-folder>/dev/seed_data/README.md`
2. Read a sample of the seed CSV files (first 5-10 rows of each)
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside any other context
4. Present a summary:

```
## Seed Data Review

**Files:** [count] CSV seed files
**Total rows:** [count]

### Overview
[Summary from README.md]

### Sample Data Preview
[First few rows from key tables]

### Review Criteria
- Is the data realistic for the [client/domain] context?
- Are the value distributions reasonable?
- Is there enough data variety for meaningful dashboard visualizations?
- Are the entity names and categories domain-appropriate?
```

### Step 3: Collect Review Decision

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the review decision for the seed data?",
    "header": "Review",
    "options": [
      {"label": "Approved", "description": "Seed data is realistic and sufficient for initial development"},
      {"label": "Changes requested", "description": "Seed data needs modifications before proceeding"}
    ],
    "multiSelect": false
  }]
}
```

If "Changes requested", ask in chat:
```
What changes are needed? Please describe the issues with the seed data.
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.seed_data section:

**If approved**:
```yaml
seed_data:
  generate: complete
  validate: pass
  review: approved
  reviewed_date: [today's date]
  reviewer: [reviewer name if provided]
```

**If changes requested**:
```yaml
seed_data:
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
- Artifact: `seed_data`
- Action: `review`
- Status: the review state just written to status.md

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

### Step 7: Confirm and Suggest Next Steps

**If approved**:
```
## Seed Data Review: Approved

### Next Steps
1. **Generate dbt project**: `/wire:dbt-generate <project>`
   The dbt project will use these seed files as its data source
```

**If changes requested**:
```
## Seed Data Review: Changes Requested

**Feedback:** [summary]

### Next Steps
1. **Regenerate seed data**: `/wire:seed_data-generate <project>`
2. Then re-validate: `/wire:seed_data-validate <project>`
3. Then re-review: `/wire:seed_data-review <project>`
```

## Output

This command updates `status.md` with the review outcome. No files are created.
