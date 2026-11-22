---
wire_schema: "1.0"
command: review
artifact: requirements
domain: requirements
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
  - artifact: requirements
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Record stakeholder review feedback on requirements specification
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Requirements Review Command

## Purpose

Record stakeholder feedback on the requirements specification. Captures approval or change requests and updates tracking.

## Usage

```bash
/wire:requirements-review YYYYMMDD_project_name
```

## Prerequisites

- Requirements must exist and pass validation
- `requirements.validate` should be `pass`

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `status.md`
2. Check that `requirements.validate == pass`
3. If not pass, warn user

**If validation not pass**:
```
Warning: Requirements have not passed validation yet.

Run `/wire:requirements-validate [folder]` before review.

Proceed anyway? (y/n)
```

### Step 2: Present Requirements for Review

**Output**:
```
## Requirements Review Session

**Project:** [PROJECT_NAME]
**Requirements File:** .wire/[folder]/requirements/requirements_specification.md

### Review Checklist

Please review the requirements and provide feedback:

- [ ] Executive summary accurately describes the project
- [ ] All functional requirements are clear and testable
- [ ] Non-functional requirements are realistic
- [ ] Data sources and owners are correct
- [ ] All SOW deliverables are documented
- [ ] Acceptance criteria are clear and measurable
- [ ] Timeline is achievable
- [ ] Risks and assumptions are complete
- [ ] Nothing important is missing

Take your time to review the full document.
```

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `requirements`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `requirements`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context
4. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "Requirements are complete and approved"},
      {"label": "Changes requested", "description": "Requirements need revisions"},
      {"label": "Needs discussion", "description": "Schedule workshop to clarify"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

**Ask for reviewer details**:
```
Who approved the requirements? (Name and role, e.g., "Chris Loveday, Vice Principal")
```

**Output**:
```
## Requirements Approved ✅

**Reviewed by:** [Reviewer Name and Role]
**Date:** [Current Date]

Requirements are locked and ready for design phase.

### Next Steps

1. **Design data pipeline**: `/wire:pipeline_design-generate [folder]`
2. **Design data model**: `/wire:data_model-generate [folder]`
3. **Create mockups**: `/wire:mockups-generate [folder]`
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer Name]"
  reviewed_date: 2026-02-13
```

On Claude Code the same state can be written with no model turn: `/wire-approve <artifact> --final [--as internal|client] [--evidence <url>]` (the Wire mod, wire#270) sets `review: approved`, `reviewed_by` and `reviewed_date` as above and appends the approval to the artifact's `review_events` list, which this command does not write. Without `--final` it records the event alone and leaves the review state to this command.

### Step 4b: If Changes Requested

**Ask for specific feedback**:
```
What changes are needed? Please describe the specific revisions required:
```

**Record feedback**:
```
## Requirements Changes Requested 🔄

**Reviewed by:** [Reviewer Name]
**Date:** [Current Date]

### Change Requests:

[User's feedback text]

### Next Steps

1. Update requirements based on feedback
2. Re-validate: `/wire:requirements-validate [folder]`
3. Re-submit for review: `/wire:requirements-review [folder]`
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: changes_requested
  feedback: "[User's feedback]"
  reviewed_date: 2026-02-13
```

### Step 4c: If Needs Discussion

**Output**:
```
## Requirements Need Discussion 💬

A workshop is recommended to clarify requirements.

### Next Steps

1. **Generate workshop materials**: `/wire:workshops-generate [folder]`
2. Conduct workshop with stakeholders
3. Update requirements based on workshop outputs
4. Re-validate and re-review
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: pending
  notes: "Workshop scheduled to clarify requirements"
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Edge Cases

### Requirements Not Validated

If validation hasn't been run:
```
Warning: Requirements have not been validated.

You should run validation first to catch any issues:
/wire:requirements-validate [folder]

Continue with review anyway? (y/n)
```

### Requirements Already Approved

If requirements already have `review: approved`:
```
Requirements are already approved.

Do you want to:
1. View approval details
2. Re-review (will overwrite previous approval)
3. Cancel
```

## Output

This command:
- Records review feedback in `status.md`
- Updates review status (approved/changes_requested/pending)
- Suggests next steps based on outcome
