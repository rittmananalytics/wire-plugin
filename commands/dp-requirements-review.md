---
description: Record stakeholder review of requirements
argument-hint: <project-folder>
---

# Record stakeholder review of requirements

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Record stakeholder review feedback on requirements specification
argument-hint: <project-folder>
---

# Requirements Review Command

## Purpose

Record stakeholder feedback on the requirements specification. Captures approval or change requests and updates tracking.

## Usage

```bash
/dp:requirements:review YYYYMMDD_project_name
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

Run `/dp:requirements:validate [folder]` before review.

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
1. Follow the meeting context retrieval workflow defined in `dp/utils/meeting_context.md`
   - Pass the project folder and artifact name `requirements`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `dp/utils/atlassian_search.md`
   - Pass the project folder and artifact name `requirements`
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

1. **Design data pipeline**: `/dp:pipeline_design:generate [folder]`
2. **Design data model**: `/dp:data_model:generate [folder]`
3. **Create mockups**: `/dp:mockups:generate [folder]`
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
2. Re-validate: `/dp:requirements:validate [folder]`
3. Re-submit for review: `/dp:requirements:review [folder]`
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

1. **Generate workshop materials**: `/dp:workshops:generate [folder]`
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

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

## Edge Cases

### Requirements Not Validated

If validation hasn't been run:
```
Warning: Requirements have not been validated.

You should run validation first to catch any issues:
/dp:requirements:validate [folder]

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
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
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
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
