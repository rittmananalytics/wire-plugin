---
wire_schema: "1.0"
command: review
artifact: training
domain: enablement
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: training
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Record stakeholder review feedback on training
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# training Review Command

## Purpose

Record stakeholder feedback on the training. Captures approval or change requests.

## Usage

```bash
/wire:training-review YYYYMMDD_project_name
```

## Prerequisites

- training must exist and pass validation
- `training.validate` should be `pass`

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `status.md`
2. Check that `training.validate == pass`

**If validation not pass**:
```
Warning: training has not passed validation yet.

Run `/wire:training-validate <project>` before review.

Proceed anyway? (y/n)
```

### Step 2: Present for Review

**Output**:
```
## training Review Session

**Project:** [PROJECT_NAME]
**Files:** [List files being reviewed]

Please review the training and provide feedback.
```

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `training`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `training`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "training is complete and approved"},
      {"label": "Changes requested", "description": "training needs revisions"},
      {"label": "Needs discussion", "description": "Requires clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

**Ask for reviewer**:
```
Who approved the training? (Name and role)
```

**Update status**:
```yaml
training:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer]"
  reviewed_date: 2026-02-13
```

**Suggest next steps**:
```

On Claude Code the same approval can be recorded with no model turn: `/wire-approve <artifact> --final [--as internal|client] [--evidence <url>]` (the Wire mod, wire#270) sets `review: approved`, `reviewed_by` and `reviewed_date` as this step does and appends the approval to the artifact's `review_events` list, which this command does not write. Without `--final` it records the event alone and leaves the review state to this command.

## training Approved ✅

**Reviewed by:** [Reviewer]

### Next Steps

[Next artifact or phase]
```

### Step 4b: If Changes Requested

**Ask for feedback**:
```
What changes are needed?
```

**Update status**:
```yaml
training:
  generate: complete
  validate: pass
  review: changes_requested
  feedback: "[Feedback]"
  reviewed_date: 2026-02-13
```

**Suggest iteration**:
```
## training Changes Requested 🔄

### Change Requests:
[Feedback]

### Next Steps

1. Address feedback
2. Re-validate: `/wire:training-validate <project>`
3. Re-submit for review
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `training`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

### Step 5.5: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `training`
- Action: `review`
- Status: the review state just written to status.md

### Step 5.6: Sync to Document Store (Optional)

If a document store is configured for this engagement and the review was approved, follow the workflow in `specs/utils/docstore_sync.md` to re-sync the final training materials to the configured store. This ensures reviewers see the approved, final version.

Fail gracefully if the document store is unavailable — this step is optional and additive.

## Output

This command:
- Records review feedback in `status.md`
- Updates review status
- Suggests next steps
