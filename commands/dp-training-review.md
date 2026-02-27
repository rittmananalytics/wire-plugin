---
description: Rehearse training
argument-hint: <project-folder>
---

# Rehearse training

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
description: Record stakeholder review feedback on training
argument-hint: <project-folder>
---

# training Review Command

## Purpose

Record stakeholder feedback on the training. Captures approval or change requests.

## Usage

```bash
/wire:dp-training-review YYYYMMDD_project_name
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

Run `/wire:dp-training-validate <project>` before review.

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
1. Follow the meeting context retrieval workflow defined in `dp/utils/meeting_context.md`
   - Pass the project folder and artifact name `training`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `dp/utils/atlassian_search.md`
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
2. Re-validate: `/wire:dp-training-validate <project>`
3. Re-submit for review
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `training`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

## Output

This command:
- Records review feedback in `status.md`
- Updates review status
- Suggests next steps

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
| YYYY-MM-DD HH:MM | /wire:dp-<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:dp-*` command that was invoked (e.g., `/wire:dp-requirements-generate`, `/wire:dp-new`, `/wire:dp-dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:dp-new` created a new project
  - `archived` — `/wire:dp-archive` archived a project
  - `removed` — `/wire:dp-remove` deleted a project
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
| 2026-02-22 14:35 | /wire:dp-new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:dp-requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:dp-requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:dp-requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:dp-conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:dp-conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:dp-conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:dp-conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:dp-conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:dp-conceptual_model-review | approved | Reviewed by John Doe |
```
